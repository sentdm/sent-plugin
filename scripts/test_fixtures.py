#!/usr/bin/env python3
"""Behavior and boundary tests for the bundled Sent utility scripts."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "packages" / "sent" / "skills"
MDR_ROOT = SKILLS / "messaging-performance-analyzer" / "scripts"
TEN_DLC_ROOT = SKILLS / "sms-10dlc-registration" / "scripts"
TEMPLATE_ROOT = SKILLS / "waba-template-author" / "scripts"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MDR = load_module("sent_mdr_analyzer", MDR_ROOT / "analyze_mdr_funnel.py")
EVIDENCE = load_module("sent_10dlc_evidence", TEN_DLC_ROOT / "validate_10dlc_packet.py")
CAMPAIGN = load_module("sent_campaign_validator", TEN_DLC_ROOT / "validate_campaign_payload.py")
TEMPLATE = load_module("sent_template_linter", TEMPLATE_ROOT / "lint_waba_template.py")


def read_fixture(root: Path, name: str) -> object:
    return json.loads((root / "fixtures" / name).read_text(encoding="utf-8"))


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


class DirectMDRTests(unittest.TestCase):
    def test_loads_list_and_wrapped_json(self) -> None:
        records = [{"message_id": "msg_test_001", "status": "DELIVERED"}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "messages.json"
            for value in (records, {"messages": records}):
                path.write_text(json.dumps(value), encoding="utf-8")
                self.assertEqual(MDR._load_messages(path), records)

    def test_rejects_malformed_json_wrong_root_and_invalid_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "messages.json"
            for value in ("{", json.dumps({"unexpected": []}), json.dumps(["not-an-object"])):
                path.write_text(value, encoding="utf-8")
                with self.subTest(value=value), self.assertRaises(MDR.InputError):
                    MDR._load_messages(path)

    def test_threshold_is_strictly_greater_than_boundary(self) -> None:
        counts = {"QUEUED": 5, "ROUTED": 5, "SENT": 5, "DELIVERED": 5, "READ": 4}
        drops = MDR.stage_dropoffs(counts)
        self.assertEqual(drops[-1], ("DELIVERED", "READ", 20.0))

    def test_error_summary_only_counts_failed_records(self) -> None:
        records = [
            {"status": "FAILED", "description": "ERR_ROUTE_DENIED then ERR_ROUTE_DENIED"},
            {"statuses": [{"stage": "FAILED"}], "description": "ERR_CONSENT_BLOCKED"},
            {"status": "DELIVERED", "description": "ERR_TEMPLATE_PARAMS_INVALID"},
        ]
        self.assertEqual(
            MDR.summarise_errors(records),
            {"ERR_ROUTE_DENIED": 1, "ERR_CONSENT_BLOCKED": 1},
        )


class DirectEvidencePacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = read_fixture(TEN_DLC_ROOT, "good.json")

    def test_checked_in_fixture_is_valid(self) -> None:
        self.assertEqual(EVIDENCE.validate(self.packet), [])

    def test_wrong_root_and_invalid_records_are_diagnostic(self) -> None:
        self.assertIn("<root>: must be a JSON object", "\n".join(EVIDENCE.validate([])))
        packet = copy.deepcopy(self.packet)
        packet["use_cases"] = ["not-an-object"]
        self.assertIn("use_cases[0]: must be an object", "\n".join(EVIDENCE.validate(packet)))

    def test_sample_count_and_length_boundaries(self) -> None:
        samples = self.packet["use_cases"][0]["sample_messages"]
        samples[:] = ["a" * 1024] * 5
        self.assertEqual(EVIDENCE.validate(self.packet), [])
        samples.append("sixth")
        self.assertIn("must contain 1–5 samples", "\n".join(EVIDENCE.validate(self.packet)))
        samples[:] = ["a" * 1025]
        self.assertIn("at most 1,024 characters", "\n".join(EVIDENCE.validate(self.packet)))


class DirectCampaignTests(unittest.TestCase):
    def test_all_use_cases_and_policy_minimum(self) -> None:
        for use_case in CAMPAIGN.USE_CASES:
            samples = 2 if use_case in CAMPAIGN.POLICY_TWO_SAMPLE_CASES else 1
            with self.subTest(use_case=use_case):
                self.assertEqual(CAMPAIGN.validate(campaign_base(use_case, samples)), [])

    def test_wrong_root_and_invalid_records_are_diagnostic(self) -> None:
        self.assertIn("<root>: must be a JSON object", "\n".join(CAMPAIGN.validate([])))
        payload = campaign_base()
        payload["campaign"]["useCases"] = ["not-an-object"]
        self.assertIn("useCases[0]: must be an object", "\n".join(CAMPAIGN.validate(payload)))

    def test_sample_count_length_and_volume_boundaries(self) -> None:
        for count, valid in ((0, False), (1, True), (5, True), (6, False)):
            issues = CAMPAIGN.validate(campaign_base("ACCOUNT_NOTIFICATION", count))
            self.assertEqual(not issues, valid, (count, issues))
        payload = campaign_base()
        payload["campaign"]["useCases"][0]["sampleMessages"] = ["a" * 1024]
        self.assertEqual(CAMPAIGN.validate(payload), [])
        payload["campaign"]["useCases"][0]["sampleMessages"] = ["a" * 1025]
        self.assertIn("at most 1,024 characters", "\n".join(CAMPAIGN.validate(payload)))
        for volume in ("1999", "2000"):
            payload = campaign_base()
            payload["campaign"]["volume"] = volume
            self.assertEqual(CAMPAIGN.validate(payload), [])
        payload["campaign"]["volume"] = 2000
        self.assertIn("numeric string", "\n".join(CAMPAIGN.validate(payload)))

    def test_marketing_and_mixed_require_two_samples(self) -> None:
        for use_case in CAMPAIGN.POLICY_TWO_SAMPLE_CASES:
            with self.subTest(use_case=use_case):
                self.assertTrue(CAMPAIGN.validate(campaign_base(use_case, 1)))
                self.assertEqual(CAMPAIGN.validate(campaign_base(use_case, 2)), [])

    def test_exact_camel_case(self) -> None:
        payload = campaign_base()
        payload["campaign"]["use_cases"] = payload["campaign"].pop("useCases")
        self.assertIn("exact camelCase", "\n".join(CAMPAIGN.validate(payload)))


class DirectTemplateTests(unittest.TestCase):
    def assert_valid(self, payload: dict) -> None:
        result = TEMPLATE.lint_template(payload)
        self.assertFalse(result.errors, result.errors)

    def assert_invalid(self, payload: object, fragment: str) -> None:
        result = TEMPLATE.lint_template(payload)
        rendered = "\n".join(f"{field}: {message}" for field, message in result.errors)
        self.assertIn(fragment, rendered)

    def test_wrong_root_and_cloud_api_shape(self) -> None:
        self.assert_invalid([], "must be a JSON object")
        self.assert_invalid({"category": "UTILITY", "components": []}, "Meta Cloud API")

    def test_button_boundaries_and_all_kinds(self) -> None:
        payload = template_base()
        payload["definition"]["buttons"] = [
            button(kind, index) for index, kind in enumerate(sorted(TEMPLATE.VALID_BUTTON_TYPES), 1)
        ]
        self.assert_valid(payload)
        payload = template_base()
        payload["definition"]["buttons"] = [button("QUICK_REPLY", index) for index in range(1, 11)]
        self.assert_valid(payload)
        payload["definition"]["buttons"].append(button("QUICK_REPLY", 11))
        self.assert_invalid(payload, "at most 10 buttons")
        payload = template_base()
        payload["definition"]["buttons"] = [button("URL", index) for index in range(1, 4)]
        self.assert_invalid(payload, "URL allows at most 2")

    def test_body_and_authentication_boundaries(self) -> None:
        payload = template_base()
        content = payload["definition"]["body"]["multiChannel"]
        content["template"] = "a" * 1024
        content["variables"] = []
        self.assert_valid(payload)
        content["template"] += "a"
        self.assert_invalid(payload, "1,024-character")
        payload = template_base()
        payload["category"] = "AUTHENTICATION"
        payload["definition"]["buttons"] = [button("COPY_CODE")]
        payload["definition"]["authenticationConfig"] = {
            "addSecurityRecommendation": True,
            "codeExpirationMinutes": 90,
        }
        self.assert_valid(payload)
        payload["definition"]["authenticationConfig"]["codeExpirationMinutes"] = 91
        self.assert_invalid(payload, "1 to 90")


class PublicCliBehaviorTests(unittest.TestCase):
    def run_cli(self, script: Path, *arguments: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *(str(argument) for argument in arguments)],
            cwd=script.parent,
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_exit(
        self,
        script: Path,
        fixture: Path,
        expected: int,
        fragment: str,
        stream: str,
    ) -> None:
        result = self.run_cli(script, fixture)
        self.assertEqual(result.returncode, expected, (result.stdout, result.stderr))
        self.assertIn(fragment, getattr(result, stream))

    def test_checked_in_success_and_policy_failure_contracts(self) -> None:
        cases = (
            (MDR_ROOT / "analyze_mdr_funnel.py", MDR_ROOT / "fixtures/good.json", 0, "OK:", "stdout"),
            (MDR_ROOT / "analyze_mdr_funnel.py", MDR_ROOT / "fixtures/bad.json", 3, "FAIL:", "stderr"),
            (TEN_DLC_ROOT / "validate_10dlc_packet.py", TEN_DLC_ROOT / "fixtures/good.json", 0, "OK", "stdout"),
            (TEN_DLC_ROOT / "validate_10dlc_packet.py", TEN_DLC_ROOT / "fixtures/bad.json", 1, "schema_version", "stderr"),
            (TEN_DLC_ROOT / "validate_campaign_payload.py", TEN_DLC_ROOT / "fixtures/campaign_good.json", 0, "OK", "stdout"),
            (TEN_DLC_ROOT / "validate_campaign_payload.py", TEN_DLC_ROOT / "fixtures/campaign_bad.json", 1, "exact camelCase", "stderr"),
            (TEMPLATE_ROOT / "lint_waba_template.py", TEMPLATE_ROOT / "fixtures/utility_good.json", 0, "OK", "stdout"),
            (TEMPLATE_ROOT / "lint_waba_template.py", TEMPLATE_ROOT / "fixtures/utility_bad.json", 1, "Meta Cloud API", "stderr"),
        )
        for script, fixture, expected, fragment, stream in cases:
            with self.subTest(script=script.name, fixture=fixture.name):
                self.assert_exit(script, fixture, expected, fragment, stream)

    def test_malformed_json_has_deterministic_input_diagnostic(self) -> None:
        cases = (
            (MDR_ROOT / "analyze_mdr_funnel.py", 2),
            (TEN_DLC_ROOT / "validate_10dlc_packet.py", 1),
            (TEN_DLC_ROOT / "validate_campaign_payload.py", 1),
            (TEMPLATE_ROOT / "lint_waba_template.py", 1),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformed.json"
            path.write_text("{", encoding="utf-8")
            for script, expected in cases:
                with self.subTest(script=script.name):
                    result = self.run_cli(script, path)
                    self.assertEqual(result.returncode, expected, (result.stdout, result.stderr))
                    self.assertIn("invalid JSON", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_missing_files_have_documented_exit_codes(self) -> None:
        cases = (
            (MDR_ROOT / "analyze_mdr_funnel.py", 2),
            (TEN_DLC_ROOT / "validate_10dlc_packet.py", 1),
            (TEN_DLC_ROOT / "validate_campaign_payload.py", 1),
            (TEMPLATE_ROOT / "lint_waba_template.py", 1),
        )
        missing = ROOT / "synthetic-missing-input.json"
        for script, expected in cases:
            with self.subTest(script=script.name):
                result = self.run_cli(script, missing)
                self.assertEqual(result.returncode, expected, (result.stdout, result.stderr))
                self.assertTrue(result.stderr.strip())
                self.assertNotIn("Traceback", result.stderr)

    def test_mdr_rejects_unsupported_extension_and_invalid_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            unsupported = Path(directory) / "messages.txt"
            unsupported.write_text("[]", encoding="utf-8")
            result = self.run_cli(MDR_ROOT / "analyze_mdr_funnel.py", unsupported)
            self.assertEqual(result.returncode, 2)
            self.assertIn("unsupported file extension", result.stderr)

            invalid = Path(directory) / "messages.json"
            invalid.write_text('["not-an-object"]', encoding="utf-8")
            result = self.run_cli(MDR_ROOT / "analyze_mdr_funnel.py", invalid)
            self.assertEqual(result.returncode, 2)
            self.assertIn("record 1 must be an object", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_mdr_exact_threshold_is_healthy(self) -> None:
        records = [
            *({"message_id": f"msg_test_{index}", "statuses": [{"stage": "READ"}]} for index in range(4)),
            {"message_id": "msg_test_5", "statuses": [{"stage": "DELIVERED"}]},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "boundary.json"
            path.write_text(json.dumps(records), encoding="utf-8")
            result = self.run_cli(MDR_ROOT / "analyze_mdr_funnel.py", path, "--threshold", 20)
        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
        self.assertIn("DELIVERED -> READ: 20.0%", result.stdout)


class FixturePrivacyTests(unittest.TestCase):
    def test_checked_in_fixtures_are_synthetic_and_privacy_safe(self) -> None:
        fixture_paths = sorted(SKILLS.glob("*/scripts/fixtures/*"))
        self.assertTrue(fixture_paths)
        corpus = "\n".join(path.read_text(encoding="utf-8") for path in fixture_paths)
        self.assertIn("example.com", corpus)
        for forbidden in ("api_key", "access_token", "@gmail.com", "@sent.dm"):
            self.assertNotIn(forbidden, corpus.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
