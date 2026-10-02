# Sent Agent Plugin

This generated host adapter packages the official Sent Agent Skills and remote MCP operations for SMS, WhatsApp, RCS, contacts, templates, analytics, account readiness, delivery diagnosis, compliance, and onboarding.

## Skills

| Skill | Use for | Path |
|---|---|---|
| `sent` | Route broad or multi-step Sent requests | [`skills/sent/SKILL.md`](skills/sent/SKILL.md) |
| `sent-messaging` | Send or schedule templates and inspect message status or activity | [`skills/sent-messaging/SKILL.md`](skills/sent-messaging/SKILL.md) |
| `sent-contacts` | List, inspect, bulk-create, summarize, or delete contacts | [`skills/sent-contacts/SKILL.md`](skills/sent-contacts/SKILL.md) |
| `sent-templates` | Find, inspect, or delete existing templates | [`skills/sent-templates/SKILL.md`](skills/sent-templates/SKILL.md) |
| `sent-analytics` | Query aggregate messaging, deliverability, contact, or number data | [`skills/sent-analytics/SKILL.md`](skills/sent-analytics/SKILL.md) |
| `sent-account-readiness` | Check account scope, balance, onboarding, and readiness | [`skills/sent-account-readiness/SKILL.md`](skills/sent-account-readiness/SKILL.md) |
| `sent-feedback` | Report user-authorized feedback about Sent tools | [`skills/sent-feedback/SKILL.md`](skills/sent-feedback/SKILL.md) |
| `sent-compliance` | Inspect live SMS market requirements and setup plans | [`skills/sent-compliance/SKILL.md`](skills/sent-compliance/SKILL.md) |
| `messaging-performance-analyzer` | Diagnose MDR funnels, delivery failures, and fallback | [`skills/messaging-performance-analyzer/SKILL.md`](skills/messaging-performance-analyzer/SKILL.md) |
| `sms-10dlc-registration` | Prepare US A2P 10DLC and TCR registration evidence | [`skills/sms-10dlc-registration/SKILL.md`](skills/sms-10dlc-registration/SKILL.md) |
| `waba-embedded-signup` | Connect WhatsApp Business Accounts and Sender Profiles | [`skills/waba-embedded-signup/SKILL.md`](skills/waba-embedded-signup/SKILL.md) |
| `waba-template-author` | Author, classify, lint, and revise WhatsApp templates | [`skills/waba-template-author/SKILL.md`](skills/waba-template-author/SKILL.md) |
| `rcs-agent-onboarding` | Prepare an RBM agent for approval and launch | [`skills/rcs-agent-onboarding/SKILL.md`](skills/rcs-agent-onboarding/SKILL.md) |
| `sender-profile-architect` | Design multi-tenant Sender Profile architecture | [`skills/sender-profile-architect/SKILL.md`](skills/sender-profile-architect/SKILL.md) |
| `template-builder-ui` | Design cross-channel template-builder UX | [`skills/template-builder-ui/SKILL.md`](skills/template-builder-ui/SKILL.md) |
| `sent-integration-starter` | Stand up and harden a Sent v3 integration | [`skills/sent-integration-starter/SKILL.md`](skills/sent-integration-starter/SKILL.md) |
| `sent-webhook-engineer` | Build and debug verified webhook receivers | [`skills/sent-webhook-engineer/SKILL.md`](skills/sent-webhook-engineer/SKILL.md) |
| `sent-routing-strategist` | Choose channels and diagnose route outcomes | [`skills/sent-routing-strategist/SKILL.md`](skills/sent-routing-strategist/SKILL.md) |
| `sent-two-way-messaging` | Design inbound, consent, and conversational flows | [`skills/sent-two-way-messaging/SKILL.md`](skills/sent-two-way-messaging/SKILL.md) |
| `sent-profile-provisioning` | Manage live Sender Profiles; guide REST users | [`skills/sent-profile-provisioning/SKILL.md`](skills/sent-profile-provisioning/SKILL.md) |
| `migrate-to-sent` | Migrate from another CPaaS provider onto Sent | [`skills/migrate-to-sent/SKILL.md`](skills/migrate-to-sent/SKILL.md) |

To install the skills without the host adapter, list or select them with the Skills CLI:

```bash
npx skills add https://github.com/sentdm/sent-plugin --list
npx skills add https://github.com/sentdm/sent-plugin --skill sent
```

## MCP and authorization

The adapter connects only to `https://mcp.sent.dm/mcp`. The MCP client performs OAuth 2.1 with PKCE and Dynamic Client Registration; no credentials or credential placeholders are included. The grant is tied to the organization and Sender Profile selected during authorization. An organization grant can use a schema-supported `profileId` to act as an owned profile; profile grants cannot. `sender_profiles.*` uses target `id` and rejects acting `profileId`. Reauthorize for another organization or scope outside the grant and revoke access from **Sent Dashboard → Settings → MCP Connections**.

MCP-backed live operations cover:

- messaging: send or schedule templates, get status, and list activity;
- contacts: list, get, bulk-create, delete, and summarize messaging;
- templates: list, get by ID or name, and delete;
- analytics: number lookup, message volume, deliverability, and contact metrics; and
- account: account details, balance, and onboarding status;
- feedback: user-authorized reports to Sent with `feedback.send`;
- Sender Profiles: `sender_profiles.list`, `.get`, `.create`, `.update`, and `.delete`; and
- SMS compliance: `compliance.requirements` and `compliance.setup_plan`.

Mutating workflows preview the exact scope and payload, then require explicit confirmation immediately before execution. They do not retry ambiguous sends blindly and do not equate an accepted message with delivery.

## Source and development

For source, full installation options, developer workflow, and security reporting, visit [github.com/sentdm/sent-plugin](https://github.com/sentdm/sent-plugin). Current machine-readable Sent product documentation is indexed at [docs.sent.dm/llms.txt](https://docs.sent.dm/llms.txt).

This directory is generated. Make source changes in `packages/sent` or `adapter-sources`, then run `python3 scripts/generate_adapters.py`.

## Additional MCP behavior

The public MCP surface includes 27 tools. `messages.send` uses an existing template with all required parameters; it supports `scheduledAt` with an explicit timezone offset, from 1 minute to 30 days ahead. Acceptance is not delivery, and quiet hours can defer release.

Feedback goes to Sent staff only with user authorization and a reviewed, sanitized report. It is limited to 2000 characters and 20 calls per authenticated account scope per UTC day, shared across acting profiles. Its note does not guarantee storage, open a support ticket, or promise a response. Number lookup is paid and limited to 1000 calls per authenticated account scope per UTC day.

Profile create and delete require `idempotencyKey`; interrupted outcomes require reconciliation before another operation. MCP update changes only name, short name, or description. Compliance setup plans create a new profile, support SMS only, and hand required document uploads to the dashboard or REST API.

Dashboard volume counts delivered/read outbound SMS and WhatsApp over supported windows; deliverability is an all-time outbound percentage including SENT, and contacts is a current total. Do not claim unsupported date filters or trends.

Use the connected server's tool schemas for argument names and availability. The [public MCP landing page](https://mcp.sent.dm) lists the current surface; some documentation pages may describe an earlier catalog.

The bundled migration inventory scanner reads local regular files in the selected repository and makes no network requests. It skips symbolic links and environment files and omits source excerpts from reports. Other bundled utilities validate supplied local payloads or analyze supplied local exports. Remote account reads and authorized writes use the declared Sent MCP endpoint.

The webhook signature utility runs locally with an explicitly supplied signing secret on standard input (`--secret-stdin`); it makes no network requests and does not read installer credentials or environment variables. Application integration examples require explicitly supplied API keys and signing secrets. Plugin authentication remains client-managed OAuth.
