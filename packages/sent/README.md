# Sent Agent Plugin

This is the canonical portable [Agent Plugins 1.0.0](https://agent-plugins.org/) package for the official Sent skills collection and remote MCP operations for SMS, WhatsApp, RCS, contacts, templates, analytics, account readiness, delivery diagnosis, compliance, and onboarding.

Skills remain usable for planning and implementation guidance when a host does not support MCP or when authorization is unavailable. Live account reads and mutations require a compatible client connected to the Sent MCP server.

## Install the skills

List this repository's skills:

```bash
npx skills add https://github.com/sentdm/sent-plugin --list
```

Install the broad-request dispatcher:

```bash
npx skills add https://github.com/sentdm/sent-plugin --skill sent
```

Install all skills:

```bash
npx skills add https://github.com/sentdm/sent-plugin --skill '*'
```

Install only the focused skills needed by a project by repeating `--skill <name>`.

## Available skills

| Skill | Use for | Path |
|---|---|---|
| `sent` | Route broad, ambiguous, or multi-step Sent work to the correct operation or specialist | [`skills/sent/SKILL.md`](skills/sent/SKILL.md) |
| `sent-messaging` | Send SMS, WhatsApp, or RCS; inspect message status and activity; handle ambiguous outcomes | [`skills/sent-messaging/SKILL.md`](skills/sent-messaging/SKILL.md) |
| `sent-contacts` | List, inspect, bulk-create, summarize, or delete contacts | [`skills/sent-contacts/SKILL.md`](skills/sent-contacts/SKILL.md) |
| `sent-templates` | List, find, inspect, or delete existing templates | [`skills/sent-templates/SKILL.md`](skills/sent-templates/SKILL.md) |
| `sent-analytics` | Query aggregate volume, deliverability, contact metrics, and number capabilities | [`skills/sent-analytics/SKILL.md`](skills/sent-analytics/SKILL.md) |
| `sent-account-readiness` | Check the authorized account, balance, onboarding/KYC status, and selected scope | [`skills/sent-account-readiness/SKILL.md`](skills/sent-account-readiness/SKILL.md) |
| `messaging-performance-analyzer` | Diagnose MDR/message-activity funnels, delivery failures, error clusters, and fallback | [`skills/messaging-performance-analyzer/SKILL.md`](skills/messaging-performance-analyzer/SKILL.md) |
| `sms-10dlc-registration` | Prepare US A2P 10DLC brand, campaign, TCR, opt-in, and remediation evidence | [`skills/sms-10dlc-registration/SKILL.md`](skills/sms-10dlc-registration/SKILL.md) |
| `waba-embedded-signup` | Connect a WABA and verify phone-number, Sender Profile, token, and webhook readiness | [`skills/waba-embedded-signup/SKILL.md`](skills/waba-embedded-signup/SKILL.md) |
| `waba-template-author` | Write, classify, lint, and revise WhatsApp templates for Meta approval | [`skills/waba-template-author/SKILL.md`](skills/waba-template-author/SKILL.md) |
| `rcs-agent-onboarding` | Prepare RBM agent identity, carrier approval, capabilities, fallback, and launch evidence | [`skills/rcs-agent-onboarding/SKILL.md`](skills/rcs-agent-onboarding/SKILL.md) |
| `sender-profile-architect` | Design multi-tenant Sender Profile boundaries, webhook routing, and lifecycle | [`skills/sender-profile-architect/SKILL.md`](skills/sender-profile-architect/SKILL.md) |
| `template-builder-ui` | Design and audit tenant-facing SMS, WhatsApp, and RCS template-builder UX | [`skills/template-builder-ui/SKILL.md`](skills/template-builder-ui/SKILL.md) |

Each `SKILL.md` contains the discovery metadata and core workflow. Skill-local `references/` hold deeper specifications and examples, `scripts/` hold deterministic validators or analyzers, and `agents/openai.yaml` supplies optional host UI metadata.

## MCP tools

The package declares `https://mcp.sent.dm/mcp` as a Streamable HTTP server.

| Area | Tools |
|---|---|
| Messaging | `messages.send`, `messages.get`, `messages.activities.list` |
| Contacts | `contacts.list`, `contacts.get`, `contacts.create_many`, `contacts.delete`, `contacts.message_summary` |
| Templates | `templates.list`, `templates.get`, `templates.get_by_name`, `templates.delete` |
| Lookup and analytics | `numbers.lookup`, `dashboard.messages_sent`, `dashboard.deliverability`, `dashboard.contacts` |
| Account | `account.get`, `balance.get`, `onboarding.status` |

Use `sent-analytics` for aggregate dashboard totals and trends. Use `messaging-performance-analyzer` for message-level evidence, funnel drop-off, and root-cause diagnosis. Use `sent-templates` for existing records, `waba-template-author` for WhatsApp content, and `template-builder-ui` for product UX.

## Authorization

Authorization is client-managed. The MCP client performs OAuth 2.1 with PKCE and Dynamic Client Registration; the package contains no token, API key, authorization header, OAuth client ID, or credential placeholder.

The grant is tied to the organization and Sender Profile selected during authorization. Reauthorize to change that scope. Revoke access from **Sent Dashboard → Settings → MCP Connections** when the connection is no longer needed. Never ask a user to paste credentials into a prompt.

## Mutation and privacy contract

- Surface the selected organization and Sender Profile before a mutation.
- Show the exact payload or delete target and require explicit confirmation immediately before the tool call.
- Treat every retry as a new mutation with a new preview and confirmation.
- Never retry an ambiguous send blindly; inspect status and activity evidence first when possible.
- Report `accepted` or `queued` as processing states, not as delivered.
- Mask phone numbers where practical and minimize contact, message, KYC, account, and billing data.
- Treat number lookup as capability information, not consent.

## Package development

Edit this directory as the source of truth. The repository root, Codex adapter, and Claude Code adapter are generated from it. After a skill or manifest change, run from the repository root:

```bash
python3 scripts/generate_adapters.py
python3 scripts/validate.py
python3 scripts/test_validation_gates.py
python3 scripts/test_fixtures.py
python3 scripts/test_contracts.py
python3 scripts/test_live_contract.py
```

For current product and API behavior, use the [Sent MCP documentation](https://docs.sent.dm/start/llm-docs/mcp-server), the [machine-readable documentation index](https://docs.sent.dm/llms.txt), and the [Sent API reference](https://docs.sent.dm/reference/api).

Live network checks are isolated from pull-request validation. The scheduled/manual/release freshness workflow compares normalized facts from the source catalog, classifies drift separately from source failures, and uploads a JSON diagnostic artifact.
