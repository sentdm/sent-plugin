#!/usr/bin/env python3
"""Offline simulations for Sent contract and documentation freshness monitoring."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import check_live_contract as CHECKER


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "schemas" / "sent" / "v3-contract-manifest.json").read_text(encoding="utf-8"))


def minimal_openapi() -> dict:
    schemas = {
        "SentDmServicesEndpointsCustomerAPIv3RequestsCreateTemplateRequest": {
            "type": "object",
            "required": MANIFEST["template_create"]["required_fields"],
            "properties": {name: {} for name in MANIFEST["template_create"]["allowed_fields"]},
        },
        "SentDmServicesCommonEntitiesTemplateBodyContent": {
            "type": "object",
            "properties": {"template": {"type": "string", "maxLength": MANIFEST["template_create"]["body_max_length"]}},
        },
        "SentDmServicesCommonEntitiesTemplateButton": {
            "type": "object",
            "properties": {"type": {"description": " ".join(MANIFEST["template_create"]["button_types"])}},
        },
        "SentDmServicesEndpointsCustomerAPIv3RequestsCreateProfileRequest": {
            "type": "object",
            "required": MANIFEST["profile"]["create_required_fields"],
        },
        "SentDmServicesEndpointsCustomerAPIv3RequestsWhatsappBusinessAccountCredentials": {
            "type": "object",
            "required": MANIFEST["profile"]["waba_required_fields"],
        },
        "SentDmServicesEndpointsCustomerAPIv3RequestsProfilesCompleteProfileRequest": {
            "type": "object",
            "required": MANIFEST["profile"]["complete_required_fields"],
        },
        "SentDmServicesEndpointsCustomerAPIv3RequestsCampaignsCampaignData": {
            "type": "object",
            "required": MANIFEST["campaign"]["required_fields"],
        },
        "SentDmServicesCommonEnumsMessagingUseCaseUS": {
            "type": "string",
            "enum": MANIFEST["campaign"]["use_case_values"],
        },
        "SentDmServicesEndpointsCustomerAPIv3RequestsCampaignsCampaignUseCaseData": {
            "type": "object",
            "properties": {
                "sampleMessages": {
                    "type": "array",
                    "minItems": MANIFEST["campaign"]["sample_min"],
                    "maxItems": MANIFEST["campaign"]["sample_max"],
                }
            },
        },
    }
    paths = {
        path: {method.lower(): {"responses": {"200": {"description": "ok"}}} for method in methods}
        for path, methods in MANIFEST["critical_paths"].items()
    }
    return copy.deepcopy({"openapi": "3.1.0", "paths": paths, "components": {"schemas": schemas}})


def source(identifier: str, url: str, kind: str, checks: list[dict] | None = None) -> dict:
    value = {
        "id": identifier,
        "url": url,
        "kind": kind,
        "affected_skills": ["sent"],
        "last_verified": "2026-08-09",
    }
    if checks is not None:
        value["checks"] = checks
    return value


class OpenApiDriftTests(unittest.TestCase):
    def assert_drift(self, document: dict, fact_fragment: str) -> None:
        result = CHECKER.evaluate_openapi(document, MANIFEST, source("openapi", "https://example.com/openapi.json", "openapi"))
        self.assertEqual(result["status"], "drift")
        self.assertTrue(any(fact_fragment in fact["fact"] for fact in result["facts"] if fact["status"] == "drift"))

    def test_endpoint_removal(self) -> None:
        document = minimal_openapi()
        document["paths"].pop("/v3/messages")
        self.assert_drift(document, "path./v3/messages.methods")

    def test_enum_addition(self) -> None:
        document = minimal_openapi()
        document["components"]["schemas"]["SentDmServicesCommonEnumsMessagingUseCaseUS"]["enum"].append("NEW_CASE")
        self.assert_drift(document, "campaign.use_case_values")

    def test_property_change(self) -> None:
        document = minimal_openapi()
        document["components"]["schemas"]["SentDmServicesEndpointsCustomerAPIv3RequestsCreateTemplateRequest"]["properties"]["newField"] = {}
        self.assert_drift(document, "template.allowed_fields")


class SourceFailureTests(unittest.TestCase):
    def test_source_conflict_is_semantic_exit_one(self) -> None:
        check = {"fact": "template.body_max_length", "extractor": "regex_int", "pattern": r"Limit: (\d+)", "expected": 1024}
        catalog = {"sources": [
            source("first", "https://example.com/first.txt", "documentation", [check]),
            source("second", "https://example.com/second.txt", "documentation", [check]),
        ]}
        bodies = {"https://example.com/first.txt": "Limit: 1024", "https://example.com/second.txt": "Limit: 2048"}
        report = CHECKER.run_monitor(catalog, MANIFEST, lambda url, timeout: bodies[url], timeout=1, retries=0)
        self.assertEqual(CHECKER.exit_code(report), 1)
        self.assertEqual({item["status"] for item in report["sources"]}, {"conflict"})

    def test_timeout_retries_are_bounded_and_exit_two(self) -> None:
        calls = 0

        def timeout_fetcher(url: str, timeout: float) -> str:
            nonlocal calls
            calls += 1
            raise TimeoutError("synthetic timeout")

        catalog = {"sources": [source("docs", "https://example.com/docs.txt", "documentation", [])]}
        report = CHECKER.run_monitor(catalog, MANIFEST, timeout_fetcher, timeout=0.01, retries=2)
        self.assertEqual(calls, 3)
        self.assertEqual(report["sources"][0]["status"], "unavailable")
        self.assertEqual(CHECKER.exit_code(report), 2)

    def test_malformed_openapi_response_exits_two(self) -> None:
        catalog = {"sources": [source("openapi", "https://example.com/openapi.json", "openapi")]}
        report = CHECKER.run_monitor(catalog, MANIFEST, lambda url, timeout: "{", timeout=1, retries=0)
        self.assertEqual(report["sources"][0]["status"], "malformed")
        self.assertEqual(CHECKER.exit_code(report), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
