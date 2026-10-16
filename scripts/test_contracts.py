#!/usr/bin/env python3
"""Executable regression tests for Sent template, campaign, and routing contracts."""

from __future__ import annotations

import datetime
import importlib.util
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

import generate_adapters as GENERATOR
import repository_metadata as REPOSITORY_METADATA
import yaml


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


class RepositoryMetadataContractTests(unittest.TestCase):
    def test_confirmation_policy_cannot_be_downgraded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "packages", root / "packages")
            path = root / "packages" / "sent" / "public-surface.json"
            original = json.loads(path.read_text())
            for tool in REPOSITORY_METADATA.REQUIRED_CONFIRMATION_TOOLS:
                for downgrade in ("confirmation", "read_only", "remove", "owner"):
                    with self.subTest(tool=tool, downgrade=downgrade):
                        surface = json.loads(json.dumps(original))
                        entry = surface["tools"][tool]
                        if downgrade == "remove":
                            del surface["tools"][tool]
                        elif downgrade == "owner":
                            entry["owner"] = "sent"
                        else:
                            entry["confirmation_required"] = False
                            if downgrade == "read_only":
                                entry["mutation"] = "read_only"
                        path.write_text(json.dumps(surface))
                        with self.assertRaisesRegex(REPOSITORY_METADATA.MetadataError, "independent safety policy"):
                            REPOSITORY_METADATA.load_repository_metadata(root)

    def test_portable_and_codex_openai_listing_match(self) -> None:
        portable = json.loads((ROOT / "packages/sent/plugin.json").read_text())["extensions"]["com.openai"]["interface"]
        codex = json.loads((ROOT / "plugins/sent/.codex-plugin/plugin.json").read_text())["interface"]
        self.assertEqual(portable, codex)
        for field in ("websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL"):
            self.assertTrue(portable[field].startswith("https://"))

    def test_public_surface_matches_skills_and_openai_submission(self) -> None:
        metadata = REPOSITORY_METADATA.load_repository_metadata(ROOT)
        submission = json.loads((ROOT / "chatgpt-app-submission.json").read_text(encoding="utf-8"))
        self.assertEqual(set(metadata.tools), set(submission["tools"]))
        self.assertEqual(set(metadata.skills), {path.stem for path in (ROOT / "evals").glob("*.yaml")})
        self.assertTrue(all(tool.owner in metadata.skills for tool in metadata.tools.values()))

    def test_version_change_propagates_to_generated_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "source"
            output = temporary / "output"
            shutil.copytree(ROOT / "packages", source / "packages")
            shutil.copytree(ROOT / "adapter-sources", source / "adapter-sources")
            plugin_path = source / "packages" / "sent" / "plugin.json"
            plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
            plugin["version"] = "9.8.7"
            plugin_path.write_text(json.dumps(plugin, indent=2) + "\n", encoding="utf-8")

            GENERATOR.build(output, source_root=source)

            generated = (
                output / "plugin.json",
                output / "plugins" / "sent" / ".codex-plugin" / "plugin.json",
                output / "claude-plugins" / "sent" / ".claude-plugin" / "plugin.json",
            )
            self.assertTrue(all(json.loads(path.read_text(encoding="utf-8"))["version"] == "9.8.7" for path in generated))
            marketplace = json.loads(
                (output / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
            )
            self.assertEqual(marketplace["metadata"]["version"], "9.8.7")


class ClaudeOverlayContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metadata = REPOSITORY_METADATA.load_repository_metadata(ROOT)
        self.overlay = REPOSITORY_METADATA.load_claude_overlay(ROOT, self.metadata)
        self.canonical = json.loads((ROOT / "packages" / "sent" / "public-surface.json").read_text(encoding="utf-8"))

    def test_claude_surface_is_canonical_minus_withheld(self) -> None:
        claude = json.loads((ROOT / "claude-plugins" / "sent" / "public-surface.json").read_text(encoding="utf-8"))
        self.assertEqual(set(self.overlay.withheld_tools), {"sender_profiles.create", "sender_profiles.delete"})
        self.assertEqual(
            claude["tools"],
            {name: tool for name, tool in self.canonical["tools"].items() if name not in self.overlay.withheld_tools},
        )

    def test_non_claude_surfaces_match_canonical(self) -> None:
        for path in (ROOT / "public-surface.json", ROOT / "plugins" / "sent" / "public-surface.json"):
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), self.canonical, path)

    def test_claude_overlay_applies_each_edit_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            GENERATOR.build(output)
            claude = output / "claude-plugins" / "sent"
            codex = output / "plugins" / "sent"
            for relative, edits in self.overlay.edits.items():
                claude_text = (claude / relative).read_text(encoding="utf-8")
                codex_text = (codex / relative).read_text(encoding="utf-8")
                for find, replace in edits:
                    self.assertIn(replace, claude_text, relative)
                    self.assertIn(find, codex_text, relative)


class SkillUiMetadataContractTests(unittest.TestCase):
    def test_every_skill_has_unique_valid_openai_metadata(self) -> None:
        metadata = REPOSITORY_METADATA.load_repository_metadata(ROOT)
        display_names: set[str] = set()
        descriptions: set[str] = set()
        for name in metadata.skills:
            path = SKILLS / name / "agents" / "openai.yaml"
            with self.subTest(skill=name):
                self.assertTrue(path.is_file(), path)
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                interface = data["interface"]
                display_name = interface["display_name"].strip()
                description = interface["short_description"].strip()
                prompt = interface["default_prompt"].strip()
                self.assertTrue(display_name)
                self.assertTrue(description)
                self.assertNotIn(display_name.casefold(), display_names)
                self.assertNotIn(description.casefold(), descriptions)
                self.assertEqual(re.findall(r"\$[a-z0-9-]+", prompt), [f"${name}"])
                display_names.add(display_name.casefold())
                descriptions.add(description.casefold())

    def test_marketplace_prompts_include_specialists(self) -> None:
        metadata = REPOSITORY_METADATA.load_repository_metadata(ROOT)
        path = ROOT / "adapter-sources" / "shared" / "marketplace.json"
        catalog = json.loads(path.read_text(encoding="utf-8"))
        prompts = catalog["default_prompts"]
        invoked = {
            match.group(1)
            for prompt in prompts
            if (match := re.search(r"\$([a-z0-9-]+)", prompt))
        }
        specialists = set(metadata.skills) - set(metadata.tools_by_owner) - {"sent"}
        self.assertGreaterEqual(len(invoked & specialists), 2)
        self.assertEqual(catalog["website_url"], "https://github.com/sentdm/sent-plugin#readme")


class DocumentationSourceContractTests(unittest.TestCase):
    def test_source_catalog_covers_freshness_domains(self) -> None:
        metadata = REPOSITORY_METADATA.load_repository_metadata(ROOT)
        path = ROOT / "schemas" / "sent" / "documentation-sources.json"
        catalog = json.loads(path.read_text(encoding="utf-8"))
        sources = {source["id"]: source for source in catalog["sources"]}
        self.assertEqual(
            set(sources),
            {
                "llms-index",
                "mcp-catalog",
                "openapi",
                "templates",
                "webhooks",
                "webhook-signatures",
                "webhook-receiver",
                "sender-profiles",
                "profile-provisioning",
                "waba",
                "routing-rcs",
                "two-way-messaging",
                "sdks",
                "per-request-credentials",
                "idempotency",
                "10dlc",
            },
        )
        for source in sources.values():
            self.assertTrue(source["url"].startswith("https://"))
            self.assertTrue(set(source["affected_skills"]) <= set(metadata.skills))
            datetime.date.fromisoformat(source["last_verified"])

    def test_network_monitoring_is_isolated_from_pr_validation(self) -> None:
        validation = (ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")
        freshness = (ROOT / ".github" / "workflows" / "documentation-freshness.yml").read_text(encoding="utf-8")
        self.assertNotIn("schedule:", validation)
        self.assertNotIn("python scripts/check_live_contract.py\n", validation)
        for required in (
            "workflow_dispatch:",
            "release:",
            "schedule:",
            "python scripts/check_live_contract.py",
            "--output artifacts/documentation-freshness.json",
            "if: always()",
            "actions/upload-artifact@",
            "python scripts/run_model_routing_eval.py",
        ):
            self.assertIn(required, freshness)


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
