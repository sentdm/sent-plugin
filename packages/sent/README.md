# Sent Agent Plugin

Sent `0.1.0` is a portable [Agent Plugins 1.0.0](https://agent-plugins.org/) package. It combines thirteen Agent Skills with the remote Sent MCP server for messaging, contacts, templates, analytics, account readiness, SMS, WhatsApp, and RCS work.

The skills remain discoverable when a host does not support MCP or when authentication is unavailable. MCP-backed operations require a compatible client and an authorized Sent account.

## Skills

- `sent` — route a Sent request to the appropriate direct-operation or specialist skill.
- `sent-messaging` — send messages and inspect message activity.
- `sent-contacts` — list, inspect, create, summarize, and delete contacts.
- `sent-templates` — find, inspect, and delete templates.
- `sent-analytics` — look up number capabilities and query dashboard metrics.
- `sent-account-readiness` — check account, balance, and onboarding status.
- `messaging-performance-analyzer` — diagnose messaging performance from delivery records.
- `rcs-agent-onboarding` — design RCS Business Messaging onboarding.
- `sender-profile-architect` — design Sender Profile boundaries and tenancy.
- `sms-10dlc-registration` — prepare US A2P 10DLC registration evidence.
- `template-builder-ui` — design tenant-facing template-builder experiences.
- `waba-embedded-signup` — implement WhatsApp Embedded Signup.
- `waba-template-author` — author and lint WhatsApp templates.

## MCP and authorization

The package declares `https://mcp.sent.dm/mcp` as a Streamable HTTP server. Authorization is client-managed: this package contains no token, API key, authorization header, OAuth client ID, or credential placeholder.

A compatible client performs OAuth 2.1 authorization with PKCE and follows the server's authorization metadata. The grant applies to the organization and Sender Profile selected during authorization. Reauthorize when switching that scope or when a grant expires. Revoke access through the MCP client or the applicable Sent account controls when the connection is no longer needed.

Before every mutation, the skills surface the selected organization and Sender Profile, show the exact payload or delete target, and require explicit confirmation immediately before the tool call. A retry is a new mutation and requires a new preview and confirmation. Ambiguous send outcomes are never retried blindly.

## Privacy and operational safety

- Mask phone numbers where practical and avoid repeating message bodies, contact data, KYC data, or account details.
- Check balance before high-volume sends.
- Treat an accepted message as queued for processing, not as delivered; inspect activity for delivery state.
- State the date range and timezone for analytics results.
- Treat number lookup as a capability signal, never as proof of consent.

## Portable installation

Install the `packages/sent` directory with any Agent Plugins 1.0.0-compatible client. Host-specific Codex and Claude packages are generated separately from this canonical directory and are not part of the portable artifact.
