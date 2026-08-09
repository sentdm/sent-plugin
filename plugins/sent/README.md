# Sent Agent Plugin

This generated host adapter packages thirteen official Sent Agent Skills and nineteen remote MCP operations for SMS, WhatsApp, RCS, contacts, templates, analytics, account readiness, delivery diagnosis, compliance, and onboarding.

## Skills

| Skill | Use for | Path |
|---|---|---|
| `sent` | Route broad or multi-step Sent requests | [`skills/sent/SKILL.md`](skills/sent/SKILL.md) |
| `sent-messaging` | Send messages and inspect message status or activity | [`skills/sent-messaging/SKILL.md`](skills/sent-messaging/SKILL.md) |
| `sent-contacts` | List, inspect, bulk-create, summarize, or delete contacts | [`skills/sent-contacts/SKILL.md`](skills/sent-contacts/SKILL.md) |
| `sent-templates` | Find, inspect, or delete existing templates | [`skills/sent-templates/SKILL.md`](skills/sent-templates/SKILL.md) |
| `sent-analytics` | Query aggregate messaging, deliverability, contact, or number data | [`skills/sent-analytics/SKILL.md`](skills/sent-analytics/SKILL.md) |
| `sent-account-readiness` | Check account scope, balance, onboarding, and readiness | [`skills/sent-account-readiness/SKILL.md`](skills/sent-account-readiness/SKILL.md) |
| `messaging-performance-analyzer` | Diagnose MDR funnels, delivery failures, and fallback | [`skills/messaging-performance-analyzer/SKILL.md`](skills/messaging-performance-analyzer/SKILL.md) |
| `sms-10dlc-registration` | Prepare US A2P 10DLC and TCR registration evidence | [`skills/sms-10dlc-registration/SKILL.md`](skills/sms-10dlc-registration/SKILL.md) |
| `waba-embedded-signup` | Connect WhatsApp Business Accounts and Sender Profiles | [`skills/waba-embedded-signup/SKILL.md`](skills/waba-embedded-signup/SKILL.md) |
| `waba-template-author` | Author, classify, lint, and revise WhatsApp templates | [`skills/waba-template-author/SKILL.md`](skills/waba-template-author/SKILL.md) |
| `rcs-agent-onboarding` | Prepare an RBM agent for approval and launch | [`skills/rcs-agent-onboarding/SKILL.md`](skills/rcs-agent-onboarding/SKILL.md) |
| `sender-profile-architect` | Design multi-tenant Sender Profile architecture | [`skills/sender-profile-architect/SKILL.md`](skills/sender-profile-architect/SKILL.md) |
| `template-builder-ui` | Design cross-channel template-builder UX | [`skills/template-builder-ui/SKILL.md`](skills/template-builder-ui/SKILL.md) |

To install the skills without the host adapter, list or select them with the Skills CLI:

```bash
npx skills add https://github.com/sentdm/sent-plugin --list
npx skills add https://github.com/sentdm/sent-plugin --skill sent
```

## MCP and authorization

The adapter connects only to `https://mcp.sent.dm/mcp`. The MCP client performs OAuth 2.1 with PKCE and Dynamic Client Registration; no credentials or credential placeholders are included. The grant is tied to the organization and Sender Profile selected during authorization. Reauthorize to change scope and revoke access from **Sent Dashboard → Settings → MCP Connections**.

MCP-backed live operations cover:

- messaging: send, get status, and list activity;
- contacts: list, get, bulk-create, delete, and summarize messaging;
- templates: list, get by ID or name, and delete;
- analytics: number lookup, message volume, deliverability, and contact metrics; and
- account: account details, balance, and onboarding status.

Mutating workflows preview the exact scope and payload, then require explicit confirmation immediately before execution. They do not retry ambiguous sends blindly and do not equate an accepted message with delivery.

## Source and development

For source, full installation options, developer workflow, and security reporting, visit [github.com/sentdm/sent-plugin](https://github.com/sentdm/sent-plugin). Current machine-readable Sent product documentation is indexed at [docs.sent.dm/llms.txt](https://docs.sent.dm/llms.txt).

This directory is generated. Make source changes in `packages/sent` or `adapter-sources`, then run `python3 scripts/generate_adapters.py`.
