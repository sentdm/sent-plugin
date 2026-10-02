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
| `sent-feedback` | Report user-authorized feedback about Sent tools | [`skills/sent-feedback/SKILL.md`](skills/sent-feedback/SKILL.md) |
| `sent-compliance` | Inspect live SMS market requirements and setup plans | [`skills/sent-compliance/SKILL.md`](skills/sent-compliance/SKILL.md) |
| `messaging-performance-analyzer` | Diagnose MDR/message-activity funnels, delivery failures, error clusters, and fallback | [`skills/messaging-performance-analyzer/SKILL.md`](skills/messaging-performance-analyzer/SKILL.md) |
| `sms-10dlc-registration` | Prepare US A2P 10DLC brand, campaign, TCR, opt-in, and remediation evidence | [`skills/sms-10dlc-registration/SKILL.md`](skills/sms-10dlc-registration/SKILL.md) |
| `waba-embedded-signup` | Connect a WABA and verify phone-number, Sender Profile, token, and webhook readiness | [`skills/waba-embedded-signup/SKILL.md`](skills/waba-embedded-signup/SKILL.md) |
| `waba-template-author` | Write, classify, lint, and revise WhatsApp templates for Meta approval | [`skills/waba-template-author/SKILL.md`](skills/waba-template-author/SKILL.md) |
| `rcs-agent-onboarding` | Prepare RBM agent identity, carrier approval, capabilities, fallback, and launch evidence | [`skills/rcs-agent-onboarding/SKILL.md`](skills/rcs-agent-onboarding/SKILL.md) |
| `sender-profile-architect` | Design multi-tenant Sender Profile boundaries, webhook routing, and lifecycle | [`skills/sender-profile-architect/SKILL.md`](skills/sender-profile-architect/SKILL.md) |
| `template-builder-ui` | Design and audit tenant-facing SMS, WhatsApp, and RCS template-builder UX | [`skills/template-builder-ui/SKILL.md`](skills/template-builder-ui/SKILL.md) |
| `sent-integration-starter` | Stand up and harden a Sent v3 integration end to end | [`skills/sent-integration-starter/SKILL.md`](skills/sent-integration-starter/SKILL.md) |
| `sent-webhook-engineer` | Build and debug verified webhook receivers and delivery health | [`skills/sent-webhook-engineer/SKILL.md`](skills/sent-webhook-engineer/SKILL.md) |
| `sent-routing-strategist` | Choose channels and diagnose route attempts and delivery outcomes | [`skills/sent-routing-strategist/SKILL.md`](skills/sent-routing-strategist/SKILL.md) |
| `sent-two-way-messaging` | Design inbound, consent, and conversational flows | [`skills/sent-two-way-messaging/SKILL.md`](skills/sent-two-way-messaging/SKILL.md) |
| `sent-profile-provisioning` | Manage live Sender Profiles; guide REST campaigns and users | [`skills/sent-profile-provisioning/SKILL.md`](skills/sent-profile-provisioning/SKILL.md) |
| `migrate-to-sent` | Migrate from another CPaaS provider onto Sent | [`skills/migrate-to-sent/SKILL.md`](skills/migrate-to-sent/SKILL.md) |

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
| Feedback | `feedback.send` |
| Sender Profiles | `sender_profiles.list`, `sender_profiles.get`, `sender_profiles.create`, `sender_profiles.update`, `sender_profiles.delete` |
| SMS compliance | `compliance.requirements`, `compliance.setup_plan` |

Use `sent-analytics` for aggregate dashboard totals and trends. Use `messaging-performance-analyzer` for message-level evidence, funnel drop-off, and root-cause diagnosis. Use `sent-templates` for existing records, `waba-template-author` for WhatsApp content, and `template-builder-ui` for product UX.

For engineering work, use `sent-integration-starter` for new integrations, `sent-webhook-engineer` for receivers, `sent-routing-strategist` for channel and route decisions, `sent-two-way-messaging` for inbound and consent, `sent-profile-provisioning` to execute what `sender-profile-architect` designs, and `migrate-to-sent` when replacing an incumbent provider.

## Authorization

Authorization is client-managed. The MCP client performs OAuth 2.1 with PKCE and Dynamic Client Registration; the package contains no token, API key, authorization header, OAuth client ID, or credential placeholder.

The grant is tied to the organization and Sender Profile selected during authorization. An organization grant can use a schema-supported `profileId` to act as an owned profile; profile grants cannot. `sender_profiles.*` uses target `id` and rejects acting `profileId`. Reauthorize for another organization or scope outside the grant. Revoke access from **Sent Dashboard → Settings → MCP Connections** when the connection is no longer needed. Never ask a user to paste credentials into a prompt.

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

## Additional MCP behavior

The public MCP surface includes 27 tools. `messages.send` uses an existing template with all required parameters; it supports `scheduledAt` with an explicit timezone offset, from 1 minute to 30 days ahead. Acceptance is not delivery, and quiet hours can defer release.

Feedback goes to Sent staff only with user authorization and a reviewed, sanitized report. It is limited to 2000 characters and 20 calls per authenticated account scope per UTC day, shared across acting profiles. Its note does not guarantee storage, open a support ticket, or promise a response. Number lookup is paid and limited to 1000 calls per authenticated account scope per UTC day.

Profile create and delete require `idempotencyKey`; interrupted outcomes require reconciliation before another operation. MCP update changes only name, short name, or description. Compliance setup plans create a new profile, support SMS only, and hand required document uploads to the dashboard or REST API.

Dashboard volume counts delivered/read outbound SMS and WhatsApp over supported windows; deliverability is an all-time outbound percentage including SENT, and contacts is a current total. Do not claim unsupported date filters or trends.

Use the connected server's tool schemas for argument names and availability. The [public MCP landing page](https://mcp.sent.dm) lists the current surface; some documentation pages may describe an earlier catalog.

The bundled migration inventory scanner reads local regular files in the selected repository and makes no network requests. It skips symbolic links and environment files and omits source excerpts from reports. Other bundled utilities validate supplied local payloads or analyze supplied local exports. Remote account reads and authorized writes use the declared Sent MCP endpoint.

The webhook signature utility runs locally with an explicitly supplied signing secret on standard input (`--secret-stdin`); it makes no network requests and does not read installer credentials or environment variables. Application integration examples require explicitly supplied API keys and signing secrets. Plugin authentication remains client-managed OAuth.
