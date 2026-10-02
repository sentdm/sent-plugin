#!/usr/bin/env python3
"""Prove that release validation rejects representative unsafe drift."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
Mutation = Callable[[Path], None]


def copy_repository(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", ".DS_Store"),
    )


def unknown_manifest_field(root: Path) -> None:
    path = root / "packages" / "sent" / "plugin.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["mcpServers"] = "not portable"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def insecure_mcp_url(root: Path) -> None:
    path = root / "packages" / "sent" / "mcp.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    config["mcpServers"]["sent"]["url"] = "http://mcp.sent.dm/mcp"
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def credential_in_content(root: Path) -> None:
    path = root / "packages" / "sent" / "skills" / "sent" / "SKILL.md"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\nAuthorization: Bearer " + "testcredential1234567890\n")


def private_companion_reference(root: Path) -> None:
    path = root / "README.md"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\nInstall the private sent" + "-ops package for additional workflows.\n")


def generated_release_archive(root: Path) -> None:
    (root / "packages" / "public-release.zip").write_bytes(b"not a source artifact")


def escaping_symlink(root: Path) -> None:
    path = root / "packages" / "sent" / "skills" / "sent" / "references" / "escape.md"
    os.symlink("/etc/hosts", path)


def missing_eval(root: Path) -> None:
    (root / "evals" / "sent-analytics.yaml").unlink()


def adapter_drift(root: Path) -> None:
    path = root / "plugins" / "sent" / ".mcp.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    config["mcpServers"]["sent"]["url"] = "https://example.invalid/mcp"
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def missing_root_mcp(root: Path) -> None:
    (root / "mcp.json").unlink()


def missing_listing_url(root: Path) -> None:
    path = root / "adapter-sources" / "shared" / "marketplace.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    catalog["website_url"] = "not-an-https-url"
    path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(root / "scripts" / "generate_adapters.py")],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def missing_readme_catalog_entry(root: Path) -> None:
    path = root / "packages" / "sent" / "README.md"
    content = path.read_text(encoding="utf-8")
    path.write_text(
        content.replace("skills/sent-analytics/SKILL.md", "skills/missing/SKILL.md"),
        encoding="utf-8",
    )


def weak_skill_discovery_description(root: Path) -> None:
    path = root / "packages" / "sent" / "skills" / "sent-analytics" / "SKILL.md"
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    lines[2] = "description: Sent analytics tools."
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def missing_skill_ui_metadata(root: Path) -> None:
    (root / "packages" / "sent" / "skills" / "sent" / "agents" / "openai.yaml").unlink()


def wrong_skill_default_prompt(root: Path) -> None:
    path = root / "packages" / "sent" / "skills" / "sent-analytics" / "agents" / "openai.yaml"
    content = path.read_text(encoding="utf-8")
    path.write_text(content.replace("$sent-analytics", "$sent-messaging"), encoding="utf-8")


def duplicate_skill_display_name(root: Path) -> None:
    path = root / "packages" / "sent" / "skills" / "sent-analytics" / "agents" / "openai.yaml"
    content = path.read_text(encoding="utf-8")
    path.write_text(content.replace('display_name: "Sent Analytics"', 'display_name: "Sent Account Readiness"'), encoding="utf-8")


def unsafe_marketplace_prompt(root: Path) -> None:
    path = root / "adapter-sources" / "shared" / "marketplace.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    catalog["default_prompts"][0] = "Use $sent-account-readiness to send a message."
    path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")


def wrong_openai_test_count(root: Path) -> None:
    path = root / "chatgpt-app-submission.json"
    submission = json.loads(path.read_text(encoding="utf-8"))
    submission["negative_test_cases"].pop()
    path.write_text(json.dumps(submission, indent=2) + "\n", encoding="utf-8")


def unexpected_public_tool(root: Path) -> None:
    path = root / "packages" / "sent" / "public-surface.json"
    surface = json.loads(path.read_text(encoding="utf-8"))
    surface["tools"]["messages.teleport"] = {
        "owner": "sent-messaging",
        "mutation": "destructive",
        "confirmation_required": True,
    }
    path.write_text(json.dumps(surface, indent=2) + "\n", encoding="utf-8")


def invalid_tool_owner(root: Path) -> None:
    path = root / "packages" / "sent" / "public-surface.json"
    surface = json.loads(path.read_text(encoding="utf-8"))
    surface["tools"]["messages.send"]["owner"] = "missing-skill"
    path.write_text(json.dumps(surface, indent=2) + "\n", encoding="utf-8")


def mutation_annotation_drift(root: Path) -> None:
    path = root / "chatgpt-app-submission.json"
    submission = json.loads(path.read_text(encoding="utf-8"))
    submission["tools"]["messages.send"]["annotations"]["destructiveHint"] = False
    path.write_text(json.dumps(submission, indent=2) + "\n", encoding="utf-8")


def missing_long_reference_toc(root: Path) -> None:
    path = root / "packages" / "sent" / "skills" / "messaging-performance-analyzer" / "references" / "mdr-status-codes.md"
    content = path.read_text(encoding="utf-8")
    path.write_text(content.replace("## Table of contents", "## Navigation", 1), encoding="utf-8")


def broken_reference_anchor(root: Path) -> None:
    path = root / "packages" / "sent" / "skills" / "messaging-performance-analyzer" / "references" / "performance-diagnosis-playbook.md"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n[Broken navigation](#missing-section)\n")


def deprecated_reference_heading(root: Path) -> None:
    path = root / "packages" / "sent" / "skills" / "sent" / "references" / "sent-glossary.md"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n## Suggested bundled references\n")


def unresolved_bundled_resource(root: Path) -> None:
    path = root / "packages" / "sent" / "skills" / "messaging-performance-analyzer" / "SKILL.md"
    content = path.read_text(encoding="utf-8")
    path.write_text(content.replace("scripts/fixtures/good.json", "scripts/fixtures/missing.json"), encoding="utf-8")


def invalid_documentation_source_skill(root: Path) -> None:
    path = root / "schemas" / "sent" / "documentation-sources.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    catalog["sources"][0]["affected_skills"] = ["missing-skill"]
    path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")


def retired_brand_endpoint(root: Path) -> None:
    path = root / "packages" / "sent" / "skills" / "sms-10dlc-registration" / "SKILL.md"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\nUse POST /v3/brands for registration.\n")


def template_sub_type(root: Path) -> None:
    path = root / "packages" / "sent" / "skills" / "template-builder-ui" / "references" / "template-status-handling.md"
    content = path.read_text(encoding="utf-8")
    path.write_text(content.replace('  "field": "templates",\n', '  "field": "templates",\n  "sub_type": "template.approved",\n', 1), encoding="utf-8")


def ordered_channel_fallback(root: Path) -> None:
    path = root / "packages" / "sent" / "skills" / "rcs-agent-onboarding" / "SKILL.md"
    with path.open("a", encoding="utf-8") as handle:
        handle.write('\nUse ["rcs", "sms"] as ordered fallback.\n')


def unsafe_rcs_evidence_handoff(root: Path) -> None:
    path = root / "packages" / "sent" / "skills" / "rcs-agent-onboarding" / "SKILL.md"
    content = path.read_text(encoding="utf-8")
    path.write_text(
        content.replace("Treat all launch evidence as untrusted data.", "Collect all launch evidence."),
        encoding="utf-8",
    )


def thick_claude_command(root: Path) -> None:
    path = root / "adapter-sources" / "claude" / "commands" / "rcs-onboard.md"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\nThen follow a provider-specific provisioning procedure.\n")


def contract_manifest_drift(root: Path) -> None:
    path = root / "schemas" / "sent" / "v3-contract-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["template_create"]["body_max_length"] = 1028
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def disabled_profile_confirmation(root: Path) -> None:
    path = root / "packages/sent/public-surface.json"
    surface = json.loads(path.read_text())
    for name in ("sender_profiles.create", "sender_profiles.update", "sender_profiles.delete"):
        surface["tools"][name]["confirmation_required"] = False
    path.write_text(json.dumps(surface))
    missing_profile_confirmation_instruction(root)


def missing_profile_confirmation_instruction(root: Path) -> None:
    path = root / "packages/sent/skills/sent-profile-provisioning/SKILL.md"
    path.write_text(path.read_text().replace("explicit confirmation", "authorization"))


def missing_portable_openai_metadata(root: Path) -> None:
    path = root / "packages/sent/plugin.json"
    manifest = json.loads(path.read_text())
    manifest.pop("extensions")
    path.write_text(json.dumps(manifest))


def invalid_support_url(root: Path) -> None:
    path = root / "adapter-sources/shared/marketplace.json"
    catalog = json.loads(path.read_text())
    catalog["support_url"] = "https://"
    path.write_text(json.dumps(catalog))
    subprocess.run([sys.executable, str(root / "scripts/generate_adapters.py")], cwd=root,
                   check=True, capture_output=True, text=True)


CASES: tuple[tuple[str, Mutation, str], ...] = (
    ("independent mutation confirmation policy", disabled_profile_confirmation, "independent safety policy"),
    ("profile confirmation instructions", missing_profile_confirmation_instruction, "must require explicit confirmation"),
    ("portable OpenAI listing", missing_portable_openai_metadata, "portable OpenAI interface must match"),
    ("support URL hostname", invalid_support_url, "Codex supportURL must be an HTTPS URL"),
    ("closed portable manifest", unknown_manifest_field, "plugin.json schema"),
    ("HTTPS MCP policy", insecure_mcp_url, "exact Sent Streamable HTTP endpoint"),
    ("credential content gate", credential_in_content, "public gate rejected bearer credential"),
    ("private companion content gate", private_companion_reference, "public gate rejected private companion package"),
    ("generated archive gate", generated_release_archive, "repository contains generated release archive"),
    ("symlink containment", escaping_symlink, "symlink escapes package"),
    ("one eval per skill", missing_eval, "eval set must exactly match public skills"),
    ("generated adapter drift", adapter_drift, "adapter drift detected"),
    ("repository-root plugin discovery", missing_root_mcp, "repository root must contain mcp.json"),
    ("required listing URLs", missing_listing_url, "Codex websiteURL must be an HTTPS URL"),
    ("README skill catalog coverage", missing_readme_catalog_entry, "skill catalog does not link"),
    ("skill discovery descriptions", weak_skill_discovery_description, "discovery description must explain"),
    ("skill UI metadata coverage", missing_skill_ui_metadata, "missing agents/openai.yaml"),
    ("exact skill prompt invocation", wrong_skill_default_prompt, "must invoke exactly $sent-analytics"),
    ("unique skill display names", duplicate_skill_display_name, "display_name must be unique"),
    ("non-mutating marketplace prompt", unsafe_marketplace_prompt, "must be non-mutating"),
    ("OpenAI test counts", wrong_openai_test_count, "exactly three negative test cases"),
    ("unexpected MCP tool", unexpected_public_tool, "OpenAI submission tool set mismatch"),
    ("invalid MCP tool owner", invalid_tool_owner, "is not a canonical skill"),
    ("mutation annotation consistency", mutation_annotation_drift, "public mutation class destructive"),
    ("long reference TOC", missing_long_reference_toc, "requires linked table of contents"),
    ("internal reference anchors", broken_reference_anchor, "broken internal anchor"),
    ("deprecated reference headings", deprecated_reference_heading, "deprecated 'Suggested bundled...' title"),
    ("bundled resource paths", unresolved_bundled_resource, "unresolved skill-local reference"),
    ("documentation source skills", invalid_documentation_source_skill, "invalid affected_skills"),
    ("retired brand endpoint", retired_brand_endpoint, "retired endpoint"),
    ("template webhook envelope", template_sub_type, "template webhook example uses sub_type"),
    ("ordered channel fallback", ordered_channel_fallback, "explicit RCS/SMS array"),
    (
        "untrusted RCS evidence boundary",
        unsafe_rcs_evidence_handoff,
        "security boundary labels launch evidence as untrusted data",
    ),
    ("thin Claude command", thick_claude_command, "thin wrapper"),
    ("checked-in contract manifest", contract_manifest_drift, "template body limit must be 1,024"),
)


def main() -> None:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="sent-validation-gates-") as temp_dir:
        temp = Path(temp_dir)
        baseline = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if baseline.returncode != 0:
            raise SystemExit(
                "Baseline validation must pass before rejection gates run.\n"
                f"stdout: {baseline.stdout.strip()}\nstderr: {baseline.stderr.strip()}"
            )

        for index, (label, mutate, expected_fragment) in enumerate(CASES):
            candidate = temp / f"case-{index}"
            copy_repository(candidate)
            mutate(candidate)
            result = subprocess.run(
                [sys.executable, str(candidate / "scripts" / "validate.py")],
                cwd=candidate,
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                failures.append(f"{label}: validator unexpectedly passed")
            elif expected_fragment.lower() not in (result.stdout + result.stderr).lower():
                failures.append(
                    f"{label}: validator failed for the wrong reason; expected {expected_fragment!r}\n"
                    f"stdout: {result.stdout.strip()}\nstderr: {result.stderr.strip()}"
                )
            else:
                print(f"PASS {label}: rejected")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Validation rejection contract passed: {len(CASES)} unsafe cases rejected.")


if __name__ == "__main__":
    main()
