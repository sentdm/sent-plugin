#!/usr/bin/env python3
"""Monitor Sent OpenAPI and documentation sources at normalized fact level.

Exit codes:
    0 - every observed fact matches
    1 - semantic drift or a conflict between authoritative sources
    2 - source unavailability, malformed content, or monitor configuration error
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "schemas" / "sent" / "v3-contract-manifest.json"
CATALOG_PATH = ROOT / "schemas" / "sent" / "documentation-sources.json"
Fetcher = Callable[[str, float], str | bytes]


def resolve(document: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in value:
        target: Any = document
        for part in value["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        return resolve(document, target)
    merged: dict[str, Any] = {key: item for key, item in value.items() if key != "allOf"}
    for member in value.get("allOf", []):
        child = resolve(document, member)
        merged.setdefault("properties", {}).update(child.get("properties", {}))
        merged["required"] = sorted(set(merged.get("required", [])) | set(child.get("required", [])))
    return merged


def schema(document: dict[str, Any], name: str) -> dict[str, Any] | None:
    try:
        value = document["components"]["schemas"][name]
        return resolve(document, value)
    except (KeyError, TypeError, ValueError):
        return None


def _fact(
    source: dict[str, Any],
    name: str,
    expected: Any,
    observed: Any,
    status: str | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    if status is None:
        status = "match" if observed == expected else "drift"
    result = {
        "fact": name,
        "status": status,
        "expected": expected,
        "observed": observed,
        "source_url": source["url"],
        "affected_skills": source.get("affected_skills", []),
    }
    if detail:
        result["detail"] = detail
    return result


def _source_status(facts: list[dict[str, Any]]) -> str:
    statuses = {fact["status"] for fact in facts}
    for candidate in ("unavailable", "malformed", "conflict", "drift"):
        if candidate in statuses:
            return candidate
    return "ok"


def _source_result(source: dict[str, Any], facts: list[dict[str, Any]], attempts: int = 1) -> dict[str, Any]:
    return {
        "id": source["id"],
        "url": source["url"],
        "kind": source["kind"],
        "affected_skills": source.get("affected_skills", []),
        "last_verified": source.get("last_verified"),
        "status": _source_status(facts),
        "attempts": attempts,
        "facts": facts,
    }


def evaluate_openapi(
    document: dict[str, Any], manifest: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(document, dict) or not isinstance(document.get("paths"), dict):
        fact = _fact(source, "openapi.document", "valid OpenAPI object", None, "malformed")
        return _source_result(source, [fact])

    facts: list[dict[str, Any]] = []
    live_paths = document.get("paths", {})
    for path, methods in manifest["critical_paths"].items():
        value = live_paths.get(path)
        observed = (
            sorted(
                method.upper()
                for method in value
                if method.lower() in {"get", "post", "put", "patch", "delete"}
            )
            if isinstance(value, dict)
            else None
        )
        facts.append(_fact(source, f"openapi.path.{path}.methods", sorted(methods), observed))
    for retired in manifest["retired_guidance_paths"]:
        facts.append(_fact(source, f"openapi.retired_path.{retired}.present", False, retired in live_paths))

    template = schema(document, "SentDmServicesEndpointsCustomerAPIv3RequestsCreateTemplateRequest")
    facts.append(
        _fact(
            source,
            "template.allowed_fields",
            sorted(manifest["template_create"]["allowed_fields"]),
            sorted(template.get("properties", {})) if template else None,
        )
    )
    facts.append(
        _fact(
            source,
            "template.required_fields",
            sorted(manifest["template_create"]["required_fields"]),
            sorted(template.get("required", [])) if template else None,
        )
    )
    body_content = schema(document, "SentDmServicesCommonEntitiesTemplateBodyContent")
    body_maximum = (
        body_content.get("properties", {}).get("template", {}).get("maxLength")
        if body_content
        else None
    )
    facts.append(
        _fact(
            source,
            "template.body_max_length",
            manifest["template_create"]["body_max_length"],
            body_maximum,
        )
    )
    button = schema(document, "SentDmServicesCommonEntitiesTemplateButton")
    description = button.get("properties", {}).get("type", {}).get("description", "") if button else ""
    observed_buttons = sorted(
        button_type
        for button_type in manifest["template_create"]["button_types"]
        if button_type in description
    )
    facts.append(
        _fact(
            source,
            "template.button_types",
            sorted(manifest["template_create"]["button_types"]),
            observed_buttons if button else None,
        )
    )

    schema_facts = (
        (
            "profile.create_required_fields",
            "SentDmServicesEndpointsCustomerAPIv3RequestsCreateProfileRequest",
            manifest["profile"]["create_required_fields"],
        ),
        (
            "profile.waba_required_fields",
            "SentDmServicesEndpointsCustomerAPIv3RequestsWhatsappBusinessAccountCredentials",
            manifest["profile"]["waba_required_fields"],
        ),
        (
            "profile.complete_required_fields",
            "SentDmServicesEndpointsCustomerAPIv3RequestsProfilesCompleteProfileRequest",
            manifest["profile"]["complete_required_fields"],
        ),
        (
            "campaign.required_fields",
            "SentDmServicesEndpointsCustomerAPIv3RequestsCampaignsCampaignData",
            manifest["campaign"]["required_fields"],
        ),
    )
    for fact_name, schema_name, expected in schema_facts:
        value = schema(document, schema_name)
        facts.append(
            _fact(source, fact_name, sorted(expected), sorted(value.get("required", [])) if value else None)
        )

    use_cases = schema(document, "SentDmServicesCommonEnumsMessagingUseCaseUS")
    facts.append(
        _fact(
            source,
            "campaign.use_case_values",
            manifest["campaign"]["use_case_values"],
            use_cases.get("enum") if use_cases else None,
        )
    )
    campaign_use_case = schema(
        document, "SentDmServicesEndpointsCustomerAPIv3RequestsCampaignsCampaignUseCaseData"
    )
    samples = campaign_use_case.get("properties", {}).get("sampleMessages", {}) if campaign_use_case else {}
    facts.append(
        _fact(
            source,
            "campaign.sample_count_range",
            [manifest["campaign"]["sample_min"], manifest["campaign"]["sample_max"]],
            [samples.get("minItems"), samples.get("maxItems")] if campaign_use_case else None,
        )
    )
    return _source_result(source, facts)


def evaluate_document(text: str, source: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return _source_result(
            source,
            [_fact(source, "source.content", "non-empty text", None, "malformed")],
        )
    facts: list[dict[str, Any]] = []
    for check in source.get("checks", []):
        fact_name = check.get("fact", "unnamed")
        expected = check.get("expected")
        extractor = check.get("extractor")
        pattern = check.get("pattern")
        if extractor == "contains" and isinstance(pattern, str):
            facts.append(_fact(source, fact_name, expected, pattern in text))
            continue
        if extractor in {"regex_int", "regex_string"} and isinstance(pattern, str):
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match is None:
                facts.append(
                    _fact(
                        source,
                        fact_name,
                        expected,
                        None,
                        "malformed",
                        f"required pattern did not match: {pattern}",
                    )
                )
                continue
            observed: Any = match.group(1)
            if extractor == "regex_int":
                try:
                    observed = int(observed)
                except ValueError:
                    facts.append(_fact(source, fact_name, expected, observed, "malformed", "capture is not an integer"))
                    continue
            facts.append(_fact(source, fact_name, expected, observed))
            continue
        facts.append(_fact(source, fact_name, expected, None, "malformed", f"unsupported extractor {extractor!r}"))
    return _source_result(source, facts)


def default_fetcher(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "sent-plugin-freshness-check/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _unavailable(source: dict[str, Any], error: Exception, attempts: int) -> dict[str, Any]:
    fact = _fact(
        source,
        "source.availability",
        "available",
        f"{type(error).__name__}: {error}",
        "unavailable",
    )
    return _source_result(source, [fact], attempts)


def _malformed(source: dict[str, Any], detail: str, attempts: int) -> dict[str, Any]:
    fact = _fact(source, "source.parse", "parseable content", None, "malformed", detail)
    return _source_result(source, [fact], attempts)


def _apply_conflicts(results: list[dict[str, Any]]) -> None:
    observations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        if result["status"] in {"unavailable", "malformed"}:
            continue
        for fact in result["facts"]:
            if fact["status"] in {"match", "drift"} and fact["observed"] is not None:
                observations[fact["fact"]].append(fact)
    for fact_name, facts in observations.items():
        values = {json.dumps(fact["observed"], sort_keys=True) for fact in facts}
        if len(values) <= 1:
            continue
        rendered = sorted(json.loads(value) for value in values)
        for fact in facts:
            fact["status"] = "conflict"
            fact["detail"] = f"authoritative sources disagree: {rendered}"
    for result in results:
        result["status"] = _source_status(result["facts"])


def run_monitor(
    catalog: dict[str, Any],
    manifest: dict[str, Any],
    fetcher: Fetcher = default_fetcher,
    *,
    timeout: float = 10,
    retries: int = 2,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for source in catalog.get("sources", []):
        payload: str | bytes | None = None
        last_error: Exception | None = None
        attempts = 0
        for attempts in range(1, retries + 2):
            try:
                payload = fetcher(source["url"], timeout)
                last_error = None
                break
            except Exception as exc:  # network adapters expose several timeout/error types
                last_error = exc
        if last_error is not None:
            results.append(_unavailable(source, last_error, attempts))
            continue
        if isinstance(payload, bytes):
            try:
                payload = payload.decode("utf-8")
            except UnicodeDecodeError as exc:
                results.append(_malformed(source, str(exc), attempts))
                continue
        if not isinstance(payload, str):
            results.append(_malformed(source, "fetcher did not return text or bytes", attempts))
            continue
        if source.get("kind") == "openapi":
            try:
                document = json.loads(payload)
            except json.JSONDecodeError as exc:
                results.append(_malformed(source, f"invalid JSON: {exc}", attempts))
                continue
            result = evaluate_openapi(document, manifest, source)
            result["attempts"] = attempts
            results.append(result)
        else:
            result = evaluate_document(payload, source)
            result["attempts"] = attempts
            results.append(result)

    _apply_conflicts(results)
    counts = Counter(result["status"] for result in results)
    diagnostics = [
        fact
        for result in results
        for fact in result["facts"]
        if fact["status"] != "match"
    ]
    return {
        "schema_version": 1,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "summary": {
            "sources": len(results),
            **{status: counts[status] for status in ("ok", "drift", "conflict", "malformed", "unavailable")},
        },
        "sources": results,
        "diagnostics": diagnostics,
    }


def exit_code(report: dict[str, Any]) -> int:
    statuses = {source["status"] for source in report.get("sources", [])}
    if statuses & {"malformed", "unavailable"}:
        return 2
    if statuses & {"drift", "conflict"}:
        return 1
    return 0


def compare(document: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    """Compatibility wrapper returning human-readable OpenAPI drift messages."""
    source = {
        "id": "openapi",
        "url": manifest["source"],
        "kind": "openapi",
        "affected_skills": [],
        "last_verified": manifest.get("verified_at"),
    }
    result = evaluate_openapi(document, manifest, source)
    return [
        f"{fact['fact']}: expected={fact['expected']!r}, observed={fact['observed']!r}"
        for fact in result["facts"]
        if fact["status"] != "match"
    ]


def _configuration_report(detail: str) -> dict[str, Any]:
    source = {
        "id": "monitor-configuration",
        "url": "local",
        "kind": "configuration",
        "affected_skills": [],
        "last_verified": None,
    }
    result = _malformed(source, detail, 0)
    return {
        "schema_version": 1,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "summary": {"sources": 1, "ok": 0, "drift": 0, "conflict": 0, "malformed": 1, "unavailable": 0},
        "sources": [result],
        "diagnostics": result["facts"],
    }


def _write_report(path: Path | None, report: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--openapi", type=Path, help="compatibility mode: check one local OpenAPI document")
    parser.add_argument("--source-dir", type=Path, help="read <source-id>.json/.txt files instead of the network")
    parser.add_argument("--only", action="append", default=[], help="check only a named catalog source")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--output", type=Path, help="write the JSON diagnostic artifact")
    args = parser.parse_args(argv)

    try:
        catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report = _configuration_report(str(exc))
        _write_report(args.output, report)
        print(f"Freshness monitor configuration error: {exc}", file=sys.stderr)
        return 2
    if args.timeout <= 0 or args.retries < 0:
        report = _configuration_report("timeout must be positive and retries must be non-negative")
        _write_report(args.output, report)
        print("Freshness monitor configuration error: invalid timeout/retries", file=sys.stderr)
        return 2

    sources = catalog.get("sources", [])
    if args.openapi:
        sources = [source for source in sources if source.get("id") == "openapi"]
    elif args.only:
        requested = set(args.only)
        sources = [source for source in sources if source.get("id") in requested]
    filtered_catalog = {**catalog, "sources": sources}
    if not sources:
        report = _configuration_report("no catalog sources selected")
        _write_report(args.output, report)
        print("Freshness monitor configuration error: no catalog sources selected", file=sys.stderr)
        return 2

    if args.openapi:
        local_openapi = args.openapi

        def fetcher(url: str, timeout: float) -> bytes:
            return local_openapi.read_bytes()

    elif args.source_dir:
        source_dir = args.source_dir
        kinds = {source["url"]: source.get("kind") for source in sources}
        identifiers = {source["url"]: source["id"] for source in sources}

        def fetcher(url: str, timeout: float) -> bytes:
            suffix = ".json" if kinds[url] == "openapi" else ".txt"
            return (source_dir / f"{identifiers[url]}{suffix}").read_bytes()

    else:
        fetcher = default_fetcher

    report = run_monitor(
        filtered_catalog,
        manifest,
        fetcher,
        timeout=args.timeout,
        retries=args.retries,
    )
    _write_report(args.output, report)
    code = exit_code(report)
    summary = report["summary"]
    print(
        "Freshness results: "
        + ", ".join(f"{status}={summary[status]}" for status in ("ok", "drift", "conflict", "malformed", "unavailable"))
    )
    for diagnostic in report["diagnostics"]:
        print(
            f"- {diagnostic['status']} {diagnostic['fact']}: "
            f"expected={diagnostic['expected']!r}, observed={diagnostic['observed']!r} "
            f"({diagnostic['source_url']})",
            file=sys.stderr,
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
