#!/usr/bin/env python3
"""Generate the repository-root package and host adapters from the canonical package."""

from __future__ import annotations

import argparse
import filecmp
import json
import shutil
import tempfile
from pathlib import Path

from repository_metadata import load_repository_metadata, openai_interface


ROOT = Path(__file__).resolve().parents[1]
MCP_URL = "https://mcp.sent.dm/mcp"
GENERATED_TREES = (
    Path("skills"),
    Path("assets"),
    Path("plugins/sent"),
    Path("claude-plugins/sent"),
)
GENERATED_FILES = (
    Path("plugin.json"),
    Path("mcp.json"),
    Path("public-surface.json"),
    Path(".agents/plugins/marketplace.json"),
    Path(".claude-plugin/marketplace.json"),
)


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


def reset_tree(path: Path, output_root: Path) -> None:
    resolved_root = output_root.resolve()
    resolved_parent = path.parent.resolve()
    if resolved_root != resolved_parent and resolved_root not in resolved_parent.parents:
        raise RuntimeError(f"refusing to replace path outside output root: {path}")
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def build(output_root: Path, source_root: Path = ROOT) -> None:
    package = source_root / "packages" / "sent"
    commands = source_root / "adapter-sources" / "claude" / "commands"
    adapter_readme = source_root / "adapter-sources" / "shared" / "README.md"
    marketplace = read_json(source_root / "adapter-sources" / "shared" / "marketplace.json")
    metadata = load_repository_metadata(source_root)
    portable_manifest = read_json(package / "plugin.json")
    portable_mcp = read_json(package / "mcp.json")
    public_surface = read_json(package / "public-surface.json")
    version = metadata.version
    endpoint = portable_mcp["mcpServers"]["sent"]["url"]
    if endpoint != MCP_URL:
        raise RuntimeError(f"unexpected Sent MCP URL: {endpoint}")

    root_skills = output_root / "skills"
    root_assets = output_root / "assets"
    reset_tree(root_skills, output_root)
    reset_tree(root_assets, output_root)
    copy_tree(package / "skills", root_skills)
    copy_tree(package / "assets", root_assets)
    write_json(output_root / "plugin.json", portable_manifest)
    write_json(output_root / "mcp.json", portable_mcp)
    write_json(output_root / "public-surface.json", public_surface)

    codex_root = output_root / "plugins" / "sent"
    claude_root = output_root / "claude-plugins" / "sent"
    reset_tree(codex_root, output_root)
    reset_tree(claude_root, output_root)

    copy_tree(package / "skills", codex_root / "skills")
    copy_tree(package / "assets", codex_root / "assets")
    copy_tree(package / "skills", claude_root / "skills")
    copy_tree(package / "assets", claude_root / "assets")
    copy_tree(commands, claude_root / ".claude" / "commands")
    for adapter_root in (codex_root, claude_root):
        shutil.copy2(adapter_readme, adapter_root / "README.md")
        shutil.copy2(package / "LICENSE", adapter_root / "LICENSE")
        write_json(adapter_root / "public-surface.json", public_surface)

    common = {
        "name": "sent",
        "version": version,
        "description": portable_manifest["description"],
        "author": portable_manifest["author"],
        "homepage": portable_manifest["homepage"],
        "repository": portable_manifest["repository"],
        "license": portable_manifest["license"],
        "keywords": portable_manifest["keywords"],
    }
    codex_manifest = {
        **common,
        "skills": "./skills/",
        "mcpServers": "./.mcp.json",
        "interface": openai_interface(marketplace),
    }
    adapter_mcp = {
        "mcpServers": {
            "sent": {
                "type": "http",
                "url": endpoint,
            }
        }
    }
    write_json(codex_root / ".codex-plugin" / "plugin.json", codex_manifest)
    write_json(codex_root / ".mcp.json", adapter_mcp)

    claude_manifest = {
        **common,
        "commands": "./.claude/commands",
        "skills": "./skills",
        "mcpServers": "./.mcp.json",
    }
    write_json(claude_root / ".claude-plugin" / "plugin.json", claude_manifest)
    write_json(claude_root / ".mcp.json", adapter_mcp)

    write_json(
        output_root / ".agents" / "plugins" / "marketplace.json",
        {
            "name": "sent",
            "interface": {"displayName": marketplace["display_name"]},
            "plugins": [
                {
                    "name": "sent",
                    "source": {"source": "local", "path": "./plugins/sent"},
                    "policy": {
                        "installation": "AVAILABLE",
                        "authentication": "ON_INSTALL",
                    },
                    "category": "Productivity",
                }
            ],
        },
    )
    write_json(
        output_root / ".claude-plugin" / "marketplace.json",
        {
            "name": "sent",
            "owner": {"name": "Sent", "url": "https://sent.dm"},
            "metadata": {
                "description": marketplace["marketplace_description"],
                "version": version,
            },
            "plugins": [
                {
                    "name": "sent",
                    "source": "./claude-plugins/sent",
                    "description": portable_manifest["description"],
                    "category": "Productivity",
                }
            ],
        },
    )


def compare_tree(expected: Path, actual: Path) -> list[str]:
    if not actual.exists():
        return [f"missing generated tree: {actual.relative_to(ROOT)}"]
    comparison = filecmp.dircmp(expected, actual)
    errors: list[str] = []
    prefix = actual.relative_to(ROOT)
    errors.extend(f"missing generated path: {prefix / name}" for name in comparison.left_only)
    errors.extend(f"unexpected generated path: {prefix / name}" for name in comparison.right_only)
    errors.extend(f"type mismatch: {prefix / name}" for name in comparison.common_funny)
    for name in comparison.common_files:
        if not filecmp.cmp(expected / name, actual / name, shallow=False):
            errors.append(f"generated file differs: {prefix / name}")
    for name, child in comparison.subdirs.items():
        errors.extend(compare_tree(expected / name, actual / name))
    return errors


def check() -> None:
    with tempfile.TemporaryDirectory(prefix="sent-adapters-") as temp_dir:
        expected_root = Path(temp_dir)
        build(expected_root)
        errors: list[str] = []
        for relative in GENERATED_TREES:
            errors.extend(compare_tree(expected_root / relative, ROOT / relative))
        for relative in GENERATED_FILES:
            expected = expected_root / relative
            actual = ROOT / relative
            if not actual.exists():
                errors.append(f"missing generated file: {relative}")
            elif expected.read_bytes() != actual.read_bytes():
                errors.append(f"generated file differs: {relative}")
        if errors:
            raise SystemExit("Adapter drift detected:\n- " + "\n- ".join(errors))
    print("Generated adapters match canonical package.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated files drift")
    args = parser.parse_args()
    if args.check:
        check()
    else:
        build(ROOT)
        metadata = load_repository_metadata(ROOT)
        print(f"Generated repository-root, Codex, and Claude packages for sent {metadata.version}.")


if __name__ == "__main__":
    main()
