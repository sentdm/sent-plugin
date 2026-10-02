#!/usr/bin/env python3
"""Load canonical release, skill, and public MCP surface metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MUTATION_CLASSES = {"read_only", "state_changing", "destructive"}
# Security policy is independent of editable public-surface.json. A metadata
# change must never remove a required confirmation check or move it to a skill
# whose instructions do not protect that operation.
REQUIRED_CONFIRMATION_TOOLS = {
    "messages.send": ("sent-messaging", "destructive"),
    "contacts.create_many": ("sent-contacts", "state_changing"),
    "contacts.delete": ("sent-contacts", "destructive"),
    "templates.delete": ("sent-templates", "destructive"),
    "feedback.send": ("sent-feedback", "state_changing"),
    "sender_profiles.create": ("sent-profile-provisioning", "state_changing"),
    "sender_profiles.update": ("sent-profile-provisioning", "state_changing"),
    "sender_profiles.delete": ("sent-profile-provisioning", "destructive"),
}


def openai_interface(catalog: dict[str, Any]) -> dict[str, Any]:
    """Build consistent portable and Codex presentation from listing metadata."""
    fields = {
        "displayName": "display_name", "shortDescription": "short_description",
        "longDescription": "long_description", "developerName": "developer_name",
        "category": "category", "capabilities": "capabilities",
        "websiteURL": "website_url", "supportURL": "support_url",
        "privacyPolicyURL": "privacy_policy_url", "termsOfServiceURL": "terms_of_service_url",
        "defaultPrompt": "default_prompts",
    }
    return {
        **{target: catalog.get(source) for target, source in fields.items()},
        "logo": "./assets/logo.svg", "composerIcon": "./assets/logo.svg",
    }


class MetadataError(ValueError):
    """Raised when canonical repository metadata is missing or malformed."""


@dataclass(frozen=True)
class ToolMetadata:
    owner: str
    mutation: str
    confirmation_required: bool


@dataclass(frozen=True)
class RepositoryMetadata:
    version: str
    skills: tuple[str, ...]
    tools: dict[str, ToolMetadata]

    @property
    def tools_by_owner(self) -> dict[str, set[str]]:
        grouped: dict[str, set[str]] = {}
        for name, tool in self.tools.items():
            grouped.setdefault(tool.owner, set()).add(name)
        return grouped

    @property
    def confirmation_tools(self) -> dict[str, str]:
        return {
            name: tool.owner
            for name, tool in self.tools.items()
            if tool.confirmation_required
        }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise MetadataError(f"could not read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise MetadataError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MetadataError(f"{path}: root must be an object")
    return value


def load_repository_metadata(root: Path) -> RepositoryMetadata:
    package = root / "packages" / "sent"
    plugin = _read_json(package / "plugin.json")
    version = plugin.get("version")
    if not isinstance(version, str) or not version.strip():
        raise MetadataError("packages/sent/plugin.json: version must be a non-empty string")

    skill_root = package / "skills"
    if not skill_root.is_dir():
        raise MetadataError("packages/sent/skills: directory is missing")
    skills = tuple(
        sorted(
            path.name
            for path in skill_root.iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        )
    )
    if not skills:
        raise MetadataError("packages/sent/skills: no canonical skills discovered")

    surface_path = package / "public-surface.json"
    surface = _read_json(surface_path)
    if set(surface) != {"schema_version", "tools"} or surface.get("schema_version") != 1:
        raise MetadataError(f"{surface_path}: expected schema_version 1 and tools")
    raw_tools = surface.get("tools")
    if not isinstance(raw_tools, dict) or not raw_tools:
        raise MetadataError(f"{surface_path}: tools must be a non-empty object")

    tools: dict[str, ToolMetadata] = {}
    for name, value in raw_tools.items():
        if not isinstance(name, str) or not name or not isinstance(value, dict):
            raise MetadataError(f"{surface_path}: every tool entry must be a named object")
        if set(value) != {"owner", "mutation", "confirmation_required"}:
            raise MetadataError(f"{surface_path}: {name} has unsupported or missing fields")
        owner = value.get("owner")
        mutation = value.get("mutation")
        confirmation = value.get("confirmation_required")
        if owner not in skills:
            raise MetadataError(f"{surface_path}: {name} owner {owner!r} is not a canonical skill")
        if mutation not in MUTATION_CLASSES:
            raise MetadataError(f"{surface_path}: {name} has invalid mutation class {mutation!r}")
        if not isinstance(confirmation, bool):
            raise MetadataError(f"{surface_path}: {name} confirmation_required must be boolean")
        if mutation == "read_only" and confirmation:
            raise MetadataError(f"{surface_path}: read-only tool {name} cannot require mutation confirmation")
        if mutation != "read_only" and not confirmation and name != "numbers.lookup":
            raise MetadataError(f"{surface_path}: {name} must require confirmation under the independent safety policy")
        tools[name] = ToolMetadata(owner, mutation, confirmation)

    for name, (owner, mutation) in REQUIRED_CONFIRMATION_TOOLS.items():
        if tools.get(name) != ToolMetadata(owner, mutation, True):
            raise MetadataError(f"{surface_path}: {name} must retain its owner, mutation class, and confirmation under the independent safety policy")

    return RepositoryMetadata(version=version, skills=skills, tools=tools)
