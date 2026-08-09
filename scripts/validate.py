#!/usr/bin/env python3
"""Validate the public Sent portable package, skills, evals, and adapters."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urlparse

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "packages" / "sent"
SKILLS = PACKAGE / "skills"
ROOT_SKILLS = ROOT / "skills"
EVALS = ROOT / "evals"
SCHEMAS = ROOT / "schemas" / "agent-plugins" / "1.0.0"
OPENAI_SUBMISSION_SCHEMA = ROOT / "schemas" / "openai" / "chatgpt-app-submission.v1.json"
VERSION = "0.1.0"
MCP_URL = "https://mcp.sent.dm/mcp"
PLUGIN_SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
EXPECTED_PACKAGE_ENTRIES = {"plugin.json", "mcp.json", "skills", "assets", "README.md", "LICENSE"}
EXPECTED_SKILLS = {
    "sent",
    "sent-messaging",
    "sent-contacts",
    "sent-templates",
    "sent-analytics",
    "sent-account-readiness",
    "messaging-performance-analyzer",
    "rcs-agent-onboarding",
    "sender-profile-architect",
    "sms-10dlc-registration",
    "template-builder-ui",
    "waba-embedded-signup",
    "waba-template-author",
}
EXPECTED_TOOLS = {
    "account.get",
    "balance.get",
    "contacts.create_many",
    "contacts.delete",
    "contacts.get",
    "contacts.list",
    "contacts.message_summary",
    "dashboard.contacts",
    "dashboard.deliverability",
    "dashboard.messages_sent",
    "messages.activities.list",
    "messages.get",
    "messages.send",
    "numbers.lookup",
    "onboarding.status",
    "templates.delete",
    "templates.get",
    "templates.get_by_name",
    "templates.list",
}
MCP_SKILLS = {
    "sent-messaging": {
        "messages.send",
        "messages.get",
        "messages.activities.list",
    },
    "sent-contacts": {
        "contacts.list",
        "contacts.get",
        "contacts.create_many",
        "contacts.delete",
        "contacts.message_summary",
    },
    "sent-templates": {
        "templates.list",
        "templates.get",
        "templates.get_by_name",
        "templates.delete",
    },
    "sent-analytics": {
        "numbers.lookup",
        "dashboard.messages_sent",
        "dashboard.deliverability",
        "dashboard.contacts",
    },
    "sent-account-readiness": {
        "account.get",
        "balance.get",
        "onboarding.status",
    },
}
MUTATION_TOOLS = {
    "messages.send": "sent-messaging",
    "contacts.create_many": "sent-contacts",
    "contacts.delete": "sent-contacts",
    "templates.delete": "sent-templates",
}
PUBLIC_FORBIDDEN = {
    "Linear URL": re.compile(r"https?://(?:www\.)?linear\.app", re.IGNORECASE),
    "Slack-derived content": re.compile(r"\bSlack(?:-derived| thread| message| channel)?\b", re.IGNORECASE),
    "local macOS path": re.compile(r"/Users/[^\s)`]+"),
    "local Windows path": re.compile(r"[A-Za-z]:\\\\Users\\\\", re.IGNORECASE),
    "private source snapshot": re.compile(r"references/_inputs|sent-openapi-v3-url", re.IGNORECASE),
    "localhost URL": re.compile(r"https?://(?:localhost|127\.0\.0\.1)(?::\d+)?", re.IGNORECASE),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "bearer credential": re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{16,}", re.IGNORECASE),
    "credential placeholder": re.compile(
        r"\b(?:YOUR|REPLACE_WITH)_(?:API_KEY|TOKEN|CLIENT_ID|CLIENT_SECRET)\b",
        re.IGNORECASE,
    ),
    "unpublished roadmap": re.compile(r"\b(?:unpublished|internal) roadmap\b", re.IGNORECASE),
    "internal security system": re.compile(r"\btheShield\b", re.IGNORECASE),
    "internal portal": re.compile(r"https?://[^\s)`]+\.(?:internal|local)(?:[/:]|$)", re.IGNORECASE),
    "credential assignment": re.compile(
        r"\b(?:api[_ -]?key|access[_ -]?token|client[_ -]?secret|authorization)\b\s*[:=]\s*[\"']?[A-Za-z0-9._~-]{12,}",
        re.IGNORECASE,
    ),
    "customer identifier": re.compile(
        r"\bcustomer[_ -]?(?:id|uuid)\b\s*[:=]\s*[\"'][^\"']{4,}[\"']",
        re.IGNORECASE,
    ),
    "private vendor detail": re.compile(r"\b(?:vendor credential|carrier buy rate|private routing rule)\b", re.IGNORECASE),
    "private companion package": re.compile(r"\bsent[-]ops(?:[-]skills)?\b", re.IGNORECASE),
}
PUBLIC_ROOT_FILES = (
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "SECURITY.md",
    ROOT / "PROVENANCE.md",
    ROOT / "chatgpt-app-submission.json",
    ROOT / ".claude-plugin" / "marketplace.json",
    ROOT / ".agents" / "plugins" / "marketplace.json",
)
FORBIDDEN_KEY_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}
LEGACY_PRIVATE_NAMESPACE = "sent" + "-ops-skills:"
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
LOCAL_RESOURCE = re.compile(r"(?<![A-Za-z0-9_])(?:references|scripts)/[A-Za-z0-9_.\-/]+")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SVG_OPEN_TAG = re.compile(r"<svg\b[^>]*>", re.IGNORECASE)
SVG_VIEWBOX = re.compile(r"\bviewBox\s*=\s*([\"'])([^\"']+)\1", re.IGNORECASE)


class Validation:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def check(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def finish(self) -> None:
        if self.errors:
            print(f"Validation failed with {len(self.errors)} issue(s):", file=sys.stderr)
            for error in self.errors:
                print(f"- {error}", file=sys.stderr)
            raise SystemExit(1)
        print("Validated Sent 0.1.0: 13 skills, 19 MCP tools, manifests, evals, and adapters.")


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def parse_skill(path: Path, validation: Validation) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        validation.errors.append(f"{path.relative_to(ROOT)}: missing YAML frontmatter")
        return {}, text
    try:
        _, raw_metadata, body = text.split("---", 2)
        metadata = yaml.safe_load(raw_metadata)
    except (ValueError, yaml.YAMLError) as exc:
        validation.errors.append(f"{path.relative_to(ROOT)}: invalid YAML frontmatter: {exc}")
        return {}, text
    if not isinstance(metadata, dict):
        validation.errors.append(f"{path.relative_to(ROOT)}: frontmatter must be a mapping")
        return {}, body
    return metadata, body.strip()


def validate_manifests(validation: Validation) -> None:
    actual_entries = {entry.name for entry in PACKAGE.iterdir()}
    validation.check(
        actual_entries == EXPECTED_PACKAGE_ENTRIES,
        "packages/sent must contain only plugin.json, mcp.json, skills/, assets/, README.md, and LICENSE; "
        f"found {sorted(actual_entries)}",
    )
    plugin = load_json(PACKAGE / "plugin.json")
    mcp = load_json(PACKAGE / "mcp.json")
    plugin_schema = load_json(SCHEMAS / "plugin.schema.json")
    mcp_schema = load_json(SCHEMAS / "mcp.schema.json")
    for error in Draft202012Validator(plugin_schema).iter_errors(plugin):
        validation.errors.append(f"plugin.json schema: {error.message}")
    for error in Draft202012Validator(mcp_schema).iter_errors(mcp):
        validation.errors.append(f"mcp.json schema: {error.message}")

    validation.check(plugin.get("$schema") == PLUGIN_SCHEMA_ID, "plugin schema version must be 1.0.0")
    validation.check(mcp.get("$schema") == MCP_SCHEMA_ID, "MCP schema version must be 1.0.0")
    validation.check(plugin.get("name") == "sent", "portable plugin name must be sent")
    validation.check(plugin.get("version") == VERSION, "portable plugin version must be 0.1.0")
    expected_server = {"type": "streamable-http", "url": MCP_URL}
    validation.check(
        mcp.get("mcpServers") == {"sent": expected_server},
        "portable MCP config must contain only the exact Sent Streamable HTTP endpoint",
    )
    for field in ("homepage", "repository"):
        value = plugin.get(field, "")
        validation.check(urlparse(value).scheme == "https", f"plugin {field} must use HTTPS")
    author_url = plugin.get("author", {}).get("url", "")
    validation.check(urlparse(author_url).scheme == "https", "plugin author.url must use HTTPS")
    validation.check(urlparse(MCP_URL).scheme == "https", "MCP URL must use HTTPS")


def validate_root_discovery(validation: Validation) -> None:
    """Keep the GitHub repository root directly discoverable as one portable plugin."""
    validation.check((ROOT / "plugin.json").is_file(), "repository root must contain plugin.json")
    validation.check((ROOT / "mcp.json").is_file(), "repository root must contain mcp.json")
    validation.check(ROOT_SKILLS.is_dir(), "repository root must contain skills/")
    if not ROOT_SKILLS.is_dir():
        return
    discovered = {
        path.name
        for path in ROOT_SKILLS.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    }
    validation.check(
        discovered == EXPECTED_SKILLS,
        "repository-root skill discovery must expose all public skills; "
        f"found {sorted(discovered)}",
    )


def validate_containment(validation: Validation) -> None:
    package_root = PACKAGE.resolve()
    for path in PACKAGE.rglob("*"):
        if path.is_symlink():
            target = path.resolve()
            validation.check(
                target == package_root or package_root in target.parents,
                f"symlink escapes package: {path.relative_to(ROOT)} -> {target}",
            )


def validate_reference(skill_root: Path, target: str, source: Path, validation: Validation) -> None:
    target = target.strip().strip("`<>")
    if not target or target.startswith("#"):
        return
    parsed = urlparse(target)
    if parsed.scheme or target.startswith("//"):
        if parsed.scheme in {"http", "https"}:
            validation.check(parsed.scheme == "https", f"{source.relative_to(ROOT)}: external URLs must use HTTPS")
        return
    clean = target.split("#", 1)[0].split("?", 1)[0]
    if not clean:
        return
    candidate = Path(clean)
    validation.check(not candidate.is_absolute(), f"{source.relative_to(ROOT)}: absolute path reference {target}")
    validation.check(".." not in candidate.parts, f"{source.relative_to(ROOT)}: sibling/root path reference {target}")
    if candidate.is_absolute() or ".." in candidate.parts:
        return
    resolved = (skill_root / candidate).resolve()
    root = skill_root.resolve()
    validation.check(root == resolved or root in resolved.parents, f"{source.relative_to(ROOT)}: path escapes skill root: {target}")
    validation.check(resolved.exists(), f"{source.relative_to(ROOT)}: unresolved skill-local reference {target}")


def validate_skills(validation: Validation) -> None:
    actual = {path.name for path in SKILLS.iterdir() if path.is_dir()}
    validation.check(actual == EXPECTED_SKILLS, f"public skill tree mismatch: found {sorted(actual)}")
    for name in sorted(actual):
        skill_root = SKILLS / name
        skill_file = skill_root / "SKILL.md"
        validation.check(skill_file.is_file(), f"{name}: missing SKILL.md")
        if not skill_file.is_file():
            continue
        metadata, body = parse_skill(skill_file, validation)
        validation.check(set(metadata) == {"name", "description"}, f"{name}: frontmatter must contain only name and description")
        validation.check(all(isinstance(value, str) for value in metadata.values()), f"{name}: all metadata values must be strings")
        validation.check(metadata.get("name") == name, f"{name}: frontmatter name must match directory")
        validation.check(bool(SKILL_NAME.fullmatch(str(metadata.get("name", "")))), f"{name}: invalid skill name")
        description = metadata.get("description", "")
        validation.check(1 <= len(description) <= 1024, f"{name}: description must be 1..1024 characters")
        validation.check(bool(body), f"{name}: instructions are empty")
        validation.check(len(body.splitlines()) <= 500, f"{name}: SKILL.md exceeds 500 instruction lines")

        for forbidden in ("sent-skills:", LEGACY_PRIVATE_NAMESPACE, "{baseDir}", "packages/sent/", "plugins/sent/"):
            validation.check(forbidden not in body, f"{name}: forbidden namespace or plugin-root path {forbidden!r}")
        for markdown_file in skill_root.rglob("*.md"):
            markdown = markdown_file.read_text(encoding="utf-8")
            for target in MARKDOWN_LINK.findall(markdown):
                validate_reference(skill_root, target, markdown_file, validation)
            for match in LOCAL_RESOURCE.findall(markdown):
                validate_reference(skill_root, match.rstrip(".,:;"), markdown_file, validation)

    dispatcher = (SKILLS / "sent" / "SKILL.md").read_text(encoding="utf-8")
    for routed_skill in EXPECTED_SKILLS - {"sent"}:
        validation.check(routed_skill in dispatcher, f"sent dispatcher does not route to {routed_skill}")


def validate_public_content(validation: Validation) -> None:
    scan_roots = (PACKAGE, EVALS, ROOT / "adapter-sources" / "claude" / "commands")
    text_suffixes = {".md", ".yaml", ".yml", ".json", ".py", ".txt", ".csv"}
    candidates = list(PUBLIC_ROOT_FILES)
    candidates.extend(ROOT.glob("docs/*.md"))
    for scan_root in scan_roots:
        candidates.extend(scan_root.rglob("*"))
    for path in candidates:
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in PUBLIC_FORBIDDEN.items():
            if pattern.search(content):
                validation.errors.append(f"{path.relative_to(ROOT)}: public gate rejected {label}")


def repository_files() -> Iterable[Path]:
    git = shutil.which("git")
    if git is None:
        result = None
    else:
        result = subprocess.run(
            [git, "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
    if result is not None and result.returncode == 0:
        for raw_path in result.stdout.split(b"\0"):
            if raw_path:
                yield ROOT / raw_path.decode("utf-8", errors="surrogateescape")
        return
    for path in ROOT.rglob("*"):
        if path.is_file() and not any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
            yield path


def validate_repository_hygiene(validation: Validation) -> None:
    for path in repository_files():
        relative = path.relative_to(ROOT)
        validation.check(path.name not in {".DS_Store", "Thumbs.db"}, f"repository contains OS metadata: {relative}")
        validation.check(
            not (relative.parts and relative.parts[0] == "packages" and path.suffix.lower() == ".zip"),
            f"repository contains generated release archive: {relative}",
        )
        validation.check(path.suffix.lower() not in FORBIDDEN_KEY_SUFFIXES, f"repository contains key material: {relative}")


def validate_tool_contract(validation: Validation) -> None:
    advertised: set[str] = set()
    for name, tools in MCP_SKILLS.items():
        text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
        for tool in tools:
            validation.check(tool in text, f"{name}: missing documented MCP tool {tool}")
        advertised.update(tools)
    validation.check(len(advertised) == 19, f"expected 19 MCP tools, found {len(advertised)}")

    for tool, skill in MUTATION_TOOLS.items():
        normalized = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8").lower()
        validation.check("explicit confirmation" in normalized, f"{skill}: {tool} must require explicit confirmation")
        validation.check("immediately before" in normalized, f"{skill}: {tool} confirmation must occur immediately before the call")
        validation.check("retry" in normalized and "new" in normalized, f"{skill}: {tool} retries must require a new confirmation")

    messaging = (SKILLS / "sent-messaging" / "SKILL.md").read_text(encoding="utf-8").lower()
    validation.check("ambiguous" in messaging and "never" in messaging and "retry" in messaging, "sent-messaging must forbid blind ambiguous retries")
    validation.check("balance" in messaging and "high-volume" in messaging, "sent-messaging must check balance before high-volume sends")
    validation.check("accepted" in messaging and "delivered" in messaging, "sent-messaging must distinguish accepted from delivered")
    analytics = (SKILLS / "sent-analytics" / "SKILL.md").read_text(encoding="utf-8").lower()
    validation.check("timezone" in analytics and "date range" in analytics, "sent-analytics must state date range and timezone")
    validation.check("consent" in analytics and "capability" in analytics, "sent-analytics must not treat lookup as consent")


def validate_evals(validation: Validation) -> None:
    eval_files = {path.stem for path in EVALS.glob("*.yaml")}
    validation.check(eval_files == EXPECTED_SKILLS, f"eval set must exactly match public skills; found {sorted(eval_files)}")
    for name in sorted(eval_files & EXPECTED_SKILLS):
        path = EVALS / f"{name}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        validation.check(isinstance(data, dict), f"{path.relative_to(ROOT)}: eval must be a mapping")
        if not isinstance(data, dict):
            continue
        validation.check(data.get("skill") == name, f"{path.relative_to(ROOT)}: skill must match filename")
        cases = data.get("cases")
        validation.check(isinstance(cases, list) and bool(cases), f"{path.relative_to(ROOT)}: cases must be non-empty")
        if not isinstance(cases, list):
            continue
        outcomes = {case.get("expect") for case in cases if isinstance(case, dict)}
        validation.check("trigger" in outcomes, f"{path.relative_to(ROOT)}: missing trigger case")
        validation.check("no_trigger" in outcomes, f"{path.relative_to(ROOT)}: missing no_trigger case")
        if name in MCP_SKILLS:
            validation.check("ambiguous" in outcomes, f"{path.relative_to(ROOT)}: missing overlap/ambiguous case")
        for index, case in enumerate(cases):
            validation.check(
                isinstance(case, dict)
                and all(isinstance(case.get(field), str) and case.get(field) for field in ("query", "expect", "rationale")),
                f"{path.relative_to(ROOT)}: case {index + 1} requires string query, expect, and rationale",
            )


def validate_adapters(validation: Validation) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_adapters.py"), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    validation.check(result.returncode == 0, result.stderr.strip() or "generated adapter drift")
    if result.returncode != 0:
        return
    codex_mcp = load_json(ROOT / "plugins" / "sent" / ".mcp.json")
    claude_mcp = load_json(ROOT / "claude-plugins" / "sent" / ".mcp.json")
    expected = {"mcpServers": {"sent": {"type": "http", "url": MCP_URL}}}
    validation.check(codex_mcp == expected, "Codex adapter must use native http MCP type")
    validation.check(claude_mcp == expected, "Claude adapter must use native http MCP type")

    codex_manifest = load_json(ROOT / "plugins" / "sent" / ".codex-plugin" / "plugin.json")
    validation.check(codex_manifest.get("name") == "sent", "Codex manifest name mismatch")
    validation.check(codex_manifest.get("version") == VERSION, "Codex manifest version mismatch")
    validation.check(codex_manifest.get("skills") == "./skills/", "Codex skills path mismatch")
    validation.check(codex_manifest.get("mcpServers") == "./.mcp.json", "Codex MCP path mismatch")
    validation.check(codex_manifest.get("interface", {}).get("category") == "Productivity", "Codex category must be Productivity")
    interface = codex_manifest.get("interface", {})
    validation.check(len(interface.get("displayName", "")) <= 30, "Codex displayName exceeds final directory limit")
    validation.check(len(interface.get("shortDescription", "")) <= 30, "Codex shortDescription exceeds final directory limit")
    validation.check(len(interface.get("longDescription", "")) <= 4000, "Codex longDescription exceeds final directory limit")
    validation.check(len(interface.get("developerName", "")) <= 80, "Codex developerName exceeds final directory limit")
    validation.check(len(interface.get("capabilities", [])) <= 20, "Codex capabilities exceed final directory limit")
    prompts = interface.get("defaultPrompt", [])
    validation.check(isinstance(prompts, list) and len(prompts) <= 3, "Codex defaultPrompt must contain at most three prompts")
    if isinstance(prompts, list):
        validation.check(all(isinstance(prompt, str) and len(prompt) <= 128 and "\n" not in prompt for prompt in prompts), "Codex starter prompts must be one line and at most 128 characters")

    required_urls = ("websiteURL", "privacyPolicyURL", "termsOfServiceURL")
    for field in required_urls:
        value = interface.get(field, "")
        validation.check(urlparse(value).scheme == "https" and len(value) <= 1024, f"Codex {field} must be an HTTPS URL within final directory limits")

    for field in ("logo", "composerIcon"):
        relative = interface.get(field, "")
        validation.check(isinstance(relative, str) and bool(relative), f"Codex {field} is required")
        if not isinstance(relative, str) or not relative:
            continue
        asset = (ROOT / "plugins" / "sent" / relative).resolve()
        adapter_root = (ROOT / "plugins" / "sent").resolve()
        validation.check(adapter_root in asset.parents and asset.is_file(), f"Codex {field} must resolve inside the plugin")
        if not asset.is_file() or asset.suffix.lower() != ".svg":
            continue
        validation.check(asset.stat().st_size <= 1_000_000, f"Codex {field} SVG must not exceed 1 MB")
        if asset.stat().st_size > 1_000_000:
            continue
        try:
            svg = asset.read_text(encoding="utf-8")
            opening_tag = SVG_OPEN_TAG.search(svg)
            view_box_match = SVG_VIEWBOX.search(opening_tag.group(0)) if opening_tag else None
            view_box = view_box_match.group(2).split() if view_box_match else []
            validation.check(len(view_box) == 4, f"Codex {field} SVG requires a numeric viewBox")
            if len(view_box) == 4:
                width, height = float(view_box[2]), float(view_box[3])
                validation.check(width == height and 48 <= width <= 4096, f"Codex {field} SVG must be square and 48..4096 pixels")
        except (OSError, UnicodeError, ValueError) as exc:
            validation.errors.append(f"Codex {field} SVG is invalid: {exc}")

    codex_marketplace = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    codex_entries = codex_marketplace.get("plugins", [])
    validation.check(len(codex_entries) == 1, "Codex marketplace must contain exactly one plugin")
    if len(codex_entries) == 1:
        entry = codex_entries[0]
        validation.check(entry.get("name") == "sent", "Codex marketplace plugin name mismatch")
        validation.check(entry.get("source") == {"source": "local", "path": "./plugins/sent"}, "Codex marketplace source mismatch")
        validation.check(
            entry.get("policy") == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "Codex marketplace policy must be AVAILABLE/ON_INSTALL",
        )
        validation.check(entry.get("category") == "Productivity", "Codex marketplace category must be Productivity")

    claude_manifest = load_json(ROOT / "claude-plugins" / "sent" / ".claude-plugin" / "plugin.json")
    validation.check(claude_manifest.get("name") == "sent", "Claude manifest name mismatch")
    validation.check(claude_manifest.get("version") == VERSION, "Claude manifest version mismatch")
    validation.check(claude_manifest.get("skills") == "./skills", "Claude skills path mismatch")
    validation.check(claude_manifest.get("commands") == "./.claude/commands", "Claude command path mismatch")
    validation.check(claude_manifest.get("mcpServers") == "./.mcp.json", "Claude MCP path mismatch")
    for required_file in ("README.md", "LICENSE"):
        validation.check(
            (ROOT / "claude-plugins" / "sent" / required_file).is_file(),
            f"Claude plugin must include {required_file}",
        )

    claude_marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    claude_entries = claude_marketplace.get("plugins", [])
    validation.check(len(claude_entries) == 1, "Claude marketplace must contain exactly one plugin")
    if len(claude_entries) == 1:
        validation.check(claude_entries[0].get("name") == "sent", "Claude marketplace plugin name mismatch")
        validation.check(claude_entries[0].get("source") == "./claude-plugins/sent", "Claude marketplace source mismatch")

    commands = list((ROOT / "claude-plugins" / "sent" / ".claude" / "commands").glob("*.md"))
    validation.check(len(commands) == 8, f"Claude adapter must retain eight command shims; found {len(commands)}")
    for command in commands:
        command_text = command.read_text(encoding="utf-8")
        validation.check(
            "sent-skills:" not in command_text and LEGACY_PRIVATE_NAMESPACE not in command_text,
            f"{command.relative_to(ROOT)}: command shim uses a legacy skill namespace",
        )


def validate_openai_submission(validation: Validation) -> None:
    path = ROOT / "chatgpt-app-submission.json"
    submission = load_json(path)
    schema = load_json(OPENAI_SUBMISSION_SCHEMA)
    for error in Draft202012Validator(schema).iter_errors(submission):
        validation.errors.append(f"{path.relative_to(ROOT)}: {error.message}")
    validation.check(
        submission.get("$schema") == "https://developers.openai.com/plugins/schemas/chatgpt-app-submission.v1.json",
        "OpenAI submission schema mismatch",
    )
    validation.check(submission.get("schema_version") == 1, "OpenAI submission schema_version must be 1")

    app_info = submission.get("app_info", {})
    validation.check(0 < len(app_info.get("display_name", "")) <= 30, "OpenAI display_name must be 1..30 characters")
    validation.check(0 < len(app_info.get("subtitle", "")) <= 30, "OpenAI subtitle must be 1..30 characters")
    validation.check(bool(app_info.get("description")), "OpenAI description is required")
    validation.check(bool(app_info.get("category")), "OpenAI category is required")

    tools = submission.get("tools", {})
    validation.check(set(tools) == EXPECTED_TOOLS, f"OpenAI submission tool set mismatch: found {sorted(tools)}")
    for name, tool in tools.items():
        annotations = tool.get("annotations", {})
        validation.check(
            set(annotations) == {"readOnlyHint", "openWorldHint", "destructiveHint"}
            and all(isinstance(value, bool) for value in annotations.values()),
            f"OpenAI tool {name} must declare all three Boolean annotations",
        )
        justifications = tool.get("justifications", {})
        expected_justifications = {
            "read_only_justification",
            "open_world_justification",
            "destructive_justification",
        }
        validation.check(
            set(justifications) == expected_justifications
            and all(isinstance(value, str) and value.strip() for value in justifications.values()),
            f"OpenAI tool {name} must justify all three annotations",
        )

    positives = submission.get("test_cases", [])
    negatives = submission.get("negative_test_cases", [])
    validation.check(isinstance(positives, list) and len(positives) == 5, "OpenAI submission requires exactly five positive test cases")
    validation.check(isinstance(negatives, list) and len(negatives) == 3, "OpenAI submission requires exactly three negative test cases")
    if isinstance(positives, list):
        for index, case in enumerate(positives):
            triggered = {name.strip() for name in str(case.get("tools_triggered", "")).split(",") if name.strip()}
            validation.check(bool(triggered) and triggered <= EXPECTED_TOOLS, f"OpenAI positive test {index + 1} references unknown or missing tools")
    if isinstance(negatives, list):
        for index, case in enumerate(negatives):
            validation.check(case.get("tools_triggered") is None, f"OpenAI negative test {index + 1} must not trigger tools")


def main() -> None:
    validation = Validation()
    validate_repository_hygiene(validation)
    validate_manifests(validation)
    validate_root_discovery(validation)
    validate_containment(validation)
    validate_skills(validation)
    validate_public_content(validation)
    validate_tool_contract(validation)
    validate_evals(validation)
    validate_adapters(validation)
    validate_openai_submission(validation)
    validation.finish()


if __name__ == "__main__":
    main()
