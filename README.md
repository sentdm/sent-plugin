# Sent Agent Plugin

The official Sent agent plugin provides thirteen skills and a remote MCP connection for business messaging, contacts, templates, analytics, account readiness, SMS, WhatsApp, and RCS workflows. The repository root is a complete Agent Plugins 1.0.0 package so GitHub-based plugin directories can discover it directly.

## Install in Claude Code

Add this repository as a marketplace, then install the plugin:

```text
/plugin marketplace add sentdm/sent-plugin
/plugin install sent@sent
```

For local development, load the generated Claude adapter directly:

```bash
claude --plugin-dir ./claude-plugins/sent
```

## Authorization and safety

The plugin connects only to `https://mcp.sent.dm/mcp`. Authentication is handled by the MCP client through OAuth 2.1 with PKCE; this repository contains no credentials, authorization headers, or credential placeholders.

Skills require an explicit preview and confirmation immediately before sends, contact creation, and deletions. They minimize customer data in output, distinguish accepted messages from delivered messages, and do not retry an ambiguous mutation automatically. See [`packages/sent/README.md`](packages/sent/README.md) for the full behavior contract.

## Repository layout

- `plugin.json`, `mcp.json`, `skills/`, and `assets/` — generated repository-root portable package for GitHub auto-discovery.
- `packages/sent/` — canonical Agent Plugins 1.0.0 package.
- `claude-plugins/sent/` — generated Claude Code plugin and compatibility commands.
- `plugins/sent/` — generated Codex plugin.
- `.claude-plugin/marketplace.json` — Claude Code marketplace manifest.
- `.agents/plugins/marketplace.json` — Codex marketplace manifest.
- `adapter-sources/` — host-specific source files used by the generator.
- `evals/` — trigger-routing evaluations for every public skill.
- `schemas/` — pinned schemas used by repository validation.
- `scripts/` — deterministic generation, validation, and fixture tests.

Generated root and adapter trees are checked in so GitHub and marketplace installations are self-contained. Do not edit them directly; update `packages/sent` or `adapter-sources` and regenerate.

## Develop and validate

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/generate_adapters.py
python3 scripts/validate.py
python3 scripts/test_validation_gates.py
python3 scripts/test_fixtures.py
claude plugin validate . --strict
claude plugin validate ./claude-plugins/sent --strict
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the public-data policy and [`docs/PUBLIC_RELEASE.md`](docs/PUBLIC_RELEASE.md) for the publication checklist. Report security issues according to [`SECURITY.md`](SECURITY.md).
