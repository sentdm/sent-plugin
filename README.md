# Sent Agent Skills for SMS, WhatsApp, RCS, and MCP

The official Sent agent plugin combines thirteen [Agent Skills](https://agentskills.io/) with nineteen live [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) tools. Use it to send and track business messages, manage contacts and templates, query analytics and account readiness, diagnose delivery failures, and guide SMS 10DLC, WhatsApp Business, RCS/RBM, and Sender Profile implementations.

This repository is both:

- a skills collection that can be discovered and installed with the `skills` CLI; and
- a portable [Agent Plugins 1.0.0](https://agent-plugins.org/) package with generated Codex and Claude Code adapters.

Each skill's canonical documentation lives in its `SKILL.md`. The collection READMEs provide the searchable task index; skill-specific `references/`, `scripts/`, and `agents/openai.yaml` files provide deeper guidance only where needed.

## Install

### Install skills with the Skills CLI

List the available skills without installing them:

```bash
npx skills add https://github.com/sentdm/sent-plugin --list
```

Install the `sent` dispatcher when you want the agent to route broad Sent requests:

```bash
npx skills add https://github.com/sentdm/sent-plugin --skill sent
```

Install one or more focused skills when the task is already known:

```bash
npx skills add https://github.com/sentdm/sent-plugin \
  --skill sent-messaging \
  --skill messaging-performance-analyzer
```

Install all thirteen skills:

```bash
npx skills add https://github.com/sentdm/sent-plugin --skill '*'
```

The Skills CLI installs agent instructions. Live account reads and mutations additionally require the Sent MCP server through a compatible, authorized client.

### Install the Claude Code plugin

```text
/plugin marketplace add sentdm/sent-plugin
/plugin install sent@sent
```

For local plugin development:

```bash
claude --plugin-dir ./claude-plugins/sent
```

### Install as a portable agent plugin

The repository root is directly discoverable as an Agent Plugins 1.0.0 package. [`packages/sent`](packages/sent) is the canonical portable artifact; [`plugins/sent`](plugins/sent) and [`claude-plugins/sent`](claude-plugins/sent) are generated host adapters.

## Find the right skill

| Skill | Use for | Example searches and requests | Path |
|---|---|---|---|
| `sent` | Route broad, ambiguous, or multi-step Sent work | “What can Sent do?”, “set up business messaging”, “which Sent skill should I use?” | [`skills/sent/SKILL.md`](skills/sent/SKILL.md) |
| `sent-messaging` | Send SMS, WhatsApp, or RCS messages; inspect one message and its activity timeline; handle ambiguous send outcomes | “send this approved template”, “did message `msg_123` deliver?”, “the send timed out” | [`skills/sent-messaging/SKILL.md`](skills/sent-messaging/SKILL.md) |
| `sent-contacts` | List, find, inspect, bulk-create, summarize, or delete Sent contacts | “import these contacts”, “find this contact”, “show messaging history”, “delete contact” | [`skills/sent-contacts/SKILL.md`](skills/sent-contacts/SKILL.md) |
| `sent-templates` | List, find by name or ID, inspect, or delete existing templates | “find an approved template”, “get template status”, “delete this template” | [`skills/sent-templates/SKILL.md`](skills/sent-templates/SKILL.md) |
| `sent-analytics` | Query message volume, aggregate deliverability, contact metrics, or phone-number capabilities | “delivery rate last week”, “messages sent this month”, “look up this number” | [`skills/sent-analytics/SKILL.md`](skills/sent-analytics/SKILL.md) |
| `sent-account-readiness` | Check the authorized account, balance, onboarding/KYC status, organization, and Sender Profile scope | “am I ready to send?”, “check balance”, “what is blocking onboarding?” | [`skills/sent-account-readiness/SKILL.md`](skills/sent-account-readiness/SKILL.md) |
| `messaging-performance-analyzer` | Diagnose MDR/message-activity funnels, delivery failures, error-code clusters, read-rate gaps, and channel fallback | “why did SMS delivery drop?”, “analyze this MDR”, “why are RCS messages falling back?” | [`skills/messaging-performance-analyzer/SKILL.md`](skills/messaging-performance-analyzer/SKILL.md) |
| `sms-10dlc-registration` | Prepare US A2P 10DLC brand, campaign, TCR, opt-in, sample-message, and rejection-remediation evidence | “register a 10DLC campaign”, “TCR brand vetting”, “carrier filtering”, “opt-in proof” | [`skills/sms-10dlc-registration/SKILL.md`](skills/sms-10dlc-registration/SKILL.md) |
| `waba-embedded-signup` | Connect a WhatsApp Business Account, map WABA and phone-number identifiers, and verify webhook/profile readiness | “connect WhatsApp”, “Embedded Signup failed”, “map this WABA to a Sender Profile” | [`skills/waba-embedded-signup/SKILL.md`](skills/waba-embedded-signup/SKILL.md) |
| `waba-template-author` | Write, classify, lint, and revise WhatsApp utility, marketing, and authentication templates | “utility or marketing?”, “fix Meta rejection”, “draft an OTP template” | [`skills/waba-template-author/SKILL.md`](skills/waba-template-author/SKILL.md) |
| `rcs-agent-onboarding` | Prepare an RCS Business Messaging agent, carrier-approval evidence, capabilities, SMS fallback, and launch checks | “onboard an RBM agent”, “RCS carrier approval”, “design SMS fallback” | [`skills/rcs-agent-onboarding/SKILL.md`](skills/rcs-agent-onboarding/SKILL.md) |
| `sender-profile-architect` | Design multi-tenant and multi-brand Sender Profile boundaries, webhook routing, lifecycle, and channel ownership | “model 50 messaging tenants”, “profile per brand?”, “route webhooks by tenant” | [`skills/sender-profile-architect/SKILL.md`](skills/sender-profile-architect/SKILL.md) |
| `template-builder-ui` | Design or audit a tenant-facing SMS, WhatsApp, and RCS template editor and submission workflow | “build a WhatsApp template editor”, “design template validation”, “handle approval states” | [`skills/template-builder-ui/SKILL.md`](skills/template-builder-ui/SKILL.md) |

Use `sent-analytics` for aggregate dashboard totals and trends. Use `messaging-performance-analyzer` for message-level evidence, funnel drop-off, and root-cause analysis. Use `sent-templates` for existing records, `waba-template-author` for WhatsApp content and policy decisions, and `template-builder-ui` for product UX.

## Live MCP capabilities

The plugin declares the Streamable HTTP endpoint `https://mcp.sent.dm/mcp` and exposes these operations through the authorized connection:

| Area | Tools |
|---|---|
| Messaging | `messages.send`, `messages.get`, `messages.activities.list` |
| Contacts | `contacts.list`, `contacts.get`, `contacts.create_many`, `contacts.delete`, `contacts.message_summary` |
| Templates | `templates.list`, `templates.get`, `templates.get_by_name`, `templates.delete` |
| Lookup and analytics | `numbers.lookup`, `dashboard.messages_sent`, `dashboard.deliverability`, `dashboard.contacts` |
| Account | `account.get`, `balance.get`, `onboarding.status` |

The MCP client performs OAuth 2.1 authorization with PKCE and Dynamic Client Registration. The user selects an organization and Sender Profile during authorization; the client stores the resulting grant. Reauthorize to change scope and revoke access from **Sent Dashboard → Settings → MCP Connections**. Do not paste API keys or tokens into prompts.

## Mutation and data-safety contract

- Preview the exact organization, Sender Profile, target, and payload before every send, contact creation, or deletion.
- Require explicit confirmation immediately before the mutation. Any changed payload or retry needs a fresh preview and confirmation.
- Never retry an ambiguous send automatically; inspect the message and activity history first when possible.
- Treat `accepted` or `queued` as processing states, not proof of delivery.
- Mask phone numbers where practical and avoid repeating message bodies, contact data, KYC data, or billing details.
- Treat number lookup as a capability signal, never as evidence of consent.

## Developer workflow

The canonical source is [`packages/sent`](packages/sent). Root discovery files and host adapters are generated; do not edit generated copies directly.

```text
packages/sent/                # canonical portable package
├── plugin.json               # searchable package metadata
├── mcp.json                  # remote MCP declaration
├── README.md                 # portable-package documentation
└── skills/<name>/
    ├── SKILL.md              # trigger metadata and workflow
    ├── agents/openai.yaml    # optional UI metadata
    ├── references/           # optional deep reference docs
    └── scripts/              # optional deterministic helpers

evals/                        # positive, negative, and overlap routing cases
adapter-sources/              # shared and host-specific adapter sources
plugins/sent/                 # generated Codex adapter
claude-plugins/sent/          # generated Claude Code adapter
scripts/                      # generation, validation, and fixture tests
```

When adding or changing a skill, update the canonical `SKILL.md`, keep its frontmatter description rich in user intent and domain terms, add routing evaluations, update the `sent` dispatcher and README catalogs when scope changes, then regenerate and validate:

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/generate_adapters.py
python3 scripts/validate.py
python3 scripts/test_validation_gates.py
python3 scripts/test_fixtures.py
claude plugin validate . --strict
claude plugin validate ./claude-plugins/sent --strict
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the public-data policy, [`docs/PUBLIC_RELEASE.md`](docs/PUBLIC_RELEASE.md) for the release checklist, and [`SECURITY.md`](SECURITY.md) for security reporting.

## Developer resources

- [Sent MCP server documentation](https://docs.sent.dm/start/llm-docs/mcp-server)
- [Sent machine-readable documentation index](https://docs.sent.dm/llms.txt)
- [Sent API documentation](https://docs.sent.dm/reference/api)
- [Agent Skills specification](https://agentskills.io/specification)
- [Agent Plugins specification](https://agent-plugins.org/specification)
