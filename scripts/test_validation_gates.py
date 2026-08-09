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
    path = root / "scripts" / "generate_adapters.py"
    content = path.read_text(encoding="utf-8")
    path.write_text(content.replace('            "websiteURL": "https://www.sent.dm",\n', ""), encoding="utf-8")
    subprocess.run([sys.executable, str(path)], cwd=root, check=True, capture_output=True, text=True)


def wrong_openai_test_count(root: Path) -> None:
    path = root / "chatgpt-app-submission.json"
    submission = json.loads(path.read_text(encoding="utf-8"))
    submission["negative_test_cases"].pop()
    path.write_text(json.dumps(submission, indent=2) + "\n", encoding="utf-8")


CASES: tuple[tuple[str, Mutation, str], ...] = (
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
    ("OpenAI test counts", wrong_openai_test_count, "exactly three negative test cases"),
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
