#!/usr/bin/env python3
"""Executable regression tests for Sent template, campaign, and routing contracts."""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "packages" / "sent" / "skills"
MANIFEST = json.loads((ROOT / "schemas" / "sent" / "v3-contract-manifest.json").read_text(encoding="utf-8"))


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TEMPLATE = load_module(
    "sent_template_linter",
    SKILLS / "waba-template-author" / "scripts" / "lint_waba_template.py",
)
CAMPAIGN = load_module(
    "sent_campaign_validator",
    SKILLS / "sms-10dlc-registration" / "scripts" / "validate_campaign_payload.py",
)


def template_base() -> dict:
    return {
        "category": "UTILITY",
        "language": "en_US",
        "definition": {
            "header": None,
            "body": {
                "multiChannel": {
                    "type": "body",
                    "template": "Hi {{0:variable}}.",
                    "variables": [
                        {"id": 0, "name": "name", "type": "variable", "props": {"sample": "Avery"}}
                    ],
                }
            },
            "footer": None,
            "buttons": [],
            "definitionVersion": "1.0",
            "authenticationConfig": None,
        },
        "creation_source": "from-api",
        "submit_for_review": False,
        "sandbox": True,
    }


def button(button_type: str, index: int = 1) -> dict:
    props: dict[str, object] = {"text": f"Action {index}"}
    if button_type == "QUICK_REPLY":
        props["quickReplyType"] = "custom"
    elif button_type == "URL":
        props.update(urlType="static", url=f"https://example.com/{index}")
    elif button_type in {"VOICE_CALL", "PHONE_NUMBER"}:
        props.update(countryCode="US", phoneNumber="+12025550100")
    elif button_type == "COPY_CODE":
        props["offerCode"] = "482193"
    return {"id": index, "type": button_type, "props": props}


def campaign_base(use_case: str = "ACCOUNT_NOTIFICATION", samples: int = 1) -> dict:
    return {
        "campaign": {
            "name": "Synthetic campaign",
            "description": "Synthetic account notifications for opted-in recipients.",
            "type": "App",
            "useCases": [
                {
                    "messagingUseCaseUs": use_case,
                    "sampleMessages": [f"Acme Example: Sample notification {index}." for index in range(samples)],
                }
            ],
            "volume": "2000",
        },
        "sandbox": True,
    }


class TemplateContractTests(unittest.TestCase):
    def assert_valid(self, payload: dict) -> None:
        result = TEMPLATE.lint_template(payload)
        self.assertFalse(result.errors, result.errors)

    def assert_invalid(self, payload: dict, fragment: str) -> None:
        result = TEMPLATE.lint_template(payload)
        rendered = "\n".join(f"{field}: {message}" for field, message in result.errors)
        self.assertIn(fragment, rendered)

    def test_all_button_types_and_mixed_kinds(self) -> None:
        payload = template_base()
        payload["definition"]["buttons"] = [button(kind, index) for index, kind in enumerate(sorted(TEMPLATE.VALID_BUTTON_TYPES), 1)]
        self.assert_valid(payload)

    def test_button_boundaries(self) -> None:
        payload = template_base()
        payload["definition"]["buttons"] = [button("QUICK_REPLY", index) for index in range(1, 11)]
        self.assert_valid(payload)
        payload["definition"]["buttons"].append(button("QUICK_REPLY", 11))
        self.assert_invalid(payload, "at most 10 buttons")
        payload = template_base()
        payload["definition"]["buttons"] = [button("URL", index) for index in range(1, 4)]
        self.assert_invalid(payload, "URL allows at most 2")

    def test_body_length_and_variable_boundaries(self) -> None:
        payload = template_base()
        content = payload["definition"]["body"]["multiChannel"]
        content["template"] = "a" * 1024
        content["variables"] = []
        self.assert_valid(payload)
        content["template"] += "a"
        self.assert_invalid(payload, "1,024-character")
        payload = template_base()
        payload["definition"]["body"]["multiChannel"]["variables"][0]["props"] = {}
        self.assert_invalid(payload, "props.sample")

    def test_channel_override(self) -> None:
        payload = template_base()
        payload["definition"]["body"]["whatsapp"] = {
            "type": "body",
            "template": "Hello {{1:variable}}.",
            "variables": [{"id": 1, "name": "name", "type": "variable", "props": {"sample": "Morgan"}}],
        }
        self.assert_valid(payload)

    def test_authentication_restrictions(self) -> None:
        payload = template_base()
        payload["category"] = "AUTHENTICATION"
        payload["definition"]["buttons"] = [button("COPY_CODE")]
        payload["definition"]["authenticationConfig"] = {
            "addSecurityRecommendation": True,
            "codeExpirationMinutes": 10,
        }
        self.assert_valid(payload)
        payload["definition"]["authenticationConfig"]["codeExpirationMinutes"] = 91
        self.assert_invalid(payload, "1 to 90")

    def test_cloud_api_shape_rejected(self) -> None:
        result = TEMPLATE.lint_template({"category": "UTILITY", "components": []})
        rendered = "\n".join(message for _, message in result.errors)
        self.assertIn("Meta Cloud API", rendered)

    def test_manifest_statuses_and_buttons(self) -> None:
        contract = MANIFEST["template_create"]
        self.assertEqual(set(contract["button_types"]), TEMPLATE.VALID_BUTTON_TYPES)
        self.assertEqual(contract["resource_statuses"], ["DRAFT", "PENDING", "APPROVED", "REJECTED", "PAUSED"])


class CampaignContractTests(unittest.TestCase):
    def test_all_use_case_values(self) -> None:
        for use_case in MANIFEST["campaign"]["use_case_values"]:
            samples = 2 if use_case in CAMPAIGN.POLICY_TWO_SAMPLE_CASES else 1
            self.assertEqual(CAMPAIGN.validate(campaign_base(use_case, samples)), [], use_case)

    def test_sample_count_boundaries(self) -> None:
        for count, valid in ((0, False), (1, True), (2, True), (5, True), (6, False)):
            issues = CAMPAIGN.validate(campaign_base("ACCOUNT_NOTIFICATION", count))
            self.assertEqual(not issues, valid, (count, issues))

    def test_marketing_and_mixed_policy(self) -> None:
        for use_case in CAMPAIGN.POLICY_TWO_SAMPLE_CASES:
            self.assertTrue(CAMPAIGN.validate(campaign_base(use_case, 1)), use_case)
            self.assertFalse(CAMPAIGN.validate(campaign_base(use_case, 2)), use_case)

    def test_sample_length_and_volume_boundary(self) -> None:
        payload = campaign_base()
        payload["campaign"]["useCases"][0]["sampleMessages"] = ["a" * 1024]
        self.assertFalse(CAMPAIGN.validate(payload))
        payload["campaign"]["useCases"][0]["sampleMessages"] = ["a" * 1025]
        self.assertTrue(CAMPAIGN.validate(payload))
        for volume in ("1999", "2000"):
            payload = campaign_base()
            payload["campaign"]["volume"] = volume
            self.assertFalse(CAMPAIGN.validate(payload), volume)
        payload["campaign"]["volume"] = 2000
        self.assertTrue(CAMPAIGN.validate(payload))

    def test_exact_camel_case(self) -> None:
        payload = campaign_base()
        payload["campaign"]["use_cases"] = payload["campaign"].pop("useCases")
        rendered = "\n".join(CAMPAIGN.validate(payload))
        self.assertIn("exact camelCase", rendered)


class BundledExampleTests(unittest.TestCase):
    def test_every_markdown_json_block_parses(self) -> None:
        for path in SKILLS.rglob("*.md"):
            for index, match in enumerate(re.finditer(r"```json\s*\n(.*?)```", path.read_text(encoding="utf-8"), re.DOTALL), 1):
                with self.subTest(path=path, block=index):
                    json.loads(match.group(1))

    def test_marked_sent_template_examples_lint(self) -> None:
        pattern = re.compile(r"<!-- sent-template-request -->\s*```json\s*\n(.*?)```", re.DOTALL)
        found = 0
        for path in SKILLS.rglob("*.md"):
            for match in pattern.finditer(path.read_text(encoding="utf-8")):
                found += 1
                result = TEMPLATE.lint_template(json.loads(match.group(1)))
                self.assertFalse(result.errors, (path, result.errors))
        self.assertGreaterEqual(found, 2)

    def test_marked_campaign_examples_validate(self) -> None:
        pattern = re.compile(r"<!-- sent-campaign-request -->\s*```json\s*\n(.*?)```", re.DOTALL)
        found = 0
        for path in SKILLS.rglob("*.md"):
            for match in pattern.finditer(path.read_text(encoding="utf-8")):
                found += 1
                self.assertEqual(CAMPAIGN.validate(json.loads(match.group(1))), [], path)
        self.assertGreaterEqual(found, 1)

    def test_no_retired_paths_or_false_fallback(self) -> None:
        corpus = "\n".join(path.read_text(encoding="utf-8") for path in SKILLS.rglob("*.md"))
        for retired in MANIFEST["retired_guidance_paths"]:
            self.assertNotIn(retired, corpus)
        self.assertNotRegex(corpus, r'\[\s*"rcs"\s*,\s*"sms"\s*\]')
        self.assertNotRegex(corpus, r'\[\s*"sms"\s*,\s*"rcs"\s*\]')


if __name__ == "__main__":
    unittest.main(verbosity=2)
