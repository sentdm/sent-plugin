#!/usr/bin/env python3
"""Compare the checked-in critical contract manifest with Sent's live v3 OpenAPI."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "schemas" / "sent" / "v3-contract-manifest.json"


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


def schema(document: dict[str, Any], name: str) -> dict[str, Any]:
    return resolve(document, document["components"]["schemas"][name])


def compare(document: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for path, methods in manifest["critical_paths"].items():
        if path not in document.get("paths", {}):
            errors.append(f"missing live path: {path}")
            continue
        live_methods = {method.upper() for method in document["paths"][path] if method.lower() in {"get", "post", "put", "patch", "delete"}}
        if live_methods != set(methods):
            errors.append(f"method drift at {path}: manifest={methods}, live={sorted(live_methods)}")
    for retired in manifest["retired_guidance_paths"]:
        if retired in document.get("paths", {}):
            errors.append(f"retired guidance path is live again and needs review: {retired}")

    template = schema(document, "SentDmServicesEndpointsCustomerAPIv3RequestsCreateTemplateRequest")
    if set(template.get("properties", {})) != set(manifest["template_create"]["allowed_fields"]):
        errors.append("template create field drift")
    body_content = schema(document, "SentDmServicesCommonEntitiesTemplateBodyContent")
    if body_content.get("properties", {}).get("template", {}).get("maxLength") != manifest["template_create"]["body_max_length"]:
        errors.append("template body maximum drift")
    button_description = schema(document, "SentDmServicesCommonEntitiesTemplateButton")["properties"]["type"].get("description", "")
    for button_type in manifest["template_create"]["button_types"]:
        if button_type not in button_description:
            errors.append(f"template button type absent from live description: {button_type}")

    create_profile = schema(document, "SentDmServicesEndpointsCustomerAPIv3RequestsCreateProfileRequest")
    if set(manifest["profile"]["create_required_fields"]) - set(create_profile.get("required", [])):
        errors.append("profile create required-field drift")
    waba = schema(document, "SentDmServicesEndpointsCustomerAPIv3RequestsWhatsappBusinessAccountCredentials")
    if set(waba.get("required", [])) != set(manifest["profile"]["waba_required_fields"]):
        errors.append("WABA credential required-field drift")
    complete = schema(document, "SentDmServicesEndpointsCustomerAPIv3RequestsProfilesCompleteProfileRequest")
    if set(complete.get("required", [])) != set(manifest["profile"]["complete_required_fields"]):
        errors.append("profile completion request drift")

    campaign = schema(document, "SentDmServicesEndpointsCustomerAPIv3RequestsCampaignsCampaignData")
    if set(campaign.get("required", [])) != set(manifest["campaign"]["required_fields"]):
        errors.append("campaign required-field drift")
    use_cases = schema(document, "SentDmServicesCommonEnumsMessagingUseCaseUS").get("enum", [])
    if use_cases != manifest["campaign"]["use_case_values"]:
        errors.append("campaign use-case enum drift")
    samples = schema(document, "SentDmServicesEndpointsCustomerAPIv3RequestsCampaignsCampaignUseCaseData")["properties"]["sampleMessages"]
    if (samples.get("minItems"), samples.get("maxItems")) != (
        manifest["campaign"]["sample_min"],
        manifest["campaign"]["sample_max"],
    ):
        errors.append("campaign sample-count drift")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openapi", type=Path, help="read a local OpenAPI document instead of the live URL")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if args.openapi:
        document = json.loads(args.openapi.read_text(encoding="utf-8"))
    else:
        request = urllib.request.Request(manifest["source"], headers={"User-Agent": "sent-plugin-contract-check/1"})
        with urllib.request.urlopen(request, timeout=30) as response:
            document = json.load(response)
    errors = compare(document, manifest)
    if errors:
        print("Live Sent contract drift detected:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Live Sent v3 critical contract matches the checked-in manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
