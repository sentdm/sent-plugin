#!/usr/bin/env python3
"""Executable regression tests for Sent template, campaign, and routing contracts."""

from __future__ import annotations

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


class ValidatorManifestContractTests(unittest.TestCase):
    def test_manifest_statuses_and_buttons(self) -> None:
        contract = MANIFEST["template_create"]
        self.assertEqual(set(contract["button_types"]), TEMPLATE.VALID_BUTTON_TYPES)
        self.assertEqual(contract["resource_statuses"], ["DRAFT", "PENDING", "APPROVED", "REJECTED", "PAUSED"])

    def test_campaign_manifest_values_match_validator(self) -> None:
        self.assertEqual(set(MANIFEST["campaign"]["use_case_values"]), CAMPAIGN.USE_CASES)


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
