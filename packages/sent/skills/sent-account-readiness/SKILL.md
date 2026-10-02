---
name: sent-account-readiness
description: Checks the authorized Sent account, organization and Sender Profile scope, balance, onboarding/KYC status, and readiness with the Sent MCP tools. Use when a user asks whether the account can send, what the MCP connection authorized, whether funds are sufficient, why onboarding is blocked, or for a preflight check before a mutation or channel launch. Route remediation to the relevant onboarding or compliance skill.
---

# Sent Account Readiness

Inspect readiness with `account.get`, `balance.get`, and `onboarding.status`.

## Authorize safely

Let the MCP client perform OAuth 2.1/PKCE. Never request, accept, print, or store tokens, API keys, authorization headers, client IDs, or secrets. The authorization grant is scoped to the organization and Sender Profile selected during the client flow. Revoke the grant through the client or applicable Sent account controls when it is no longer needed.

If MCP is unsupported or authentication fails, explain what can still be planned from the skill and direct the user to authorize or reauthorize in their MCP client. Do not ask them to paste credentials.

An organization grant may select an owned Sender Profile with the tool schema's optional `profileId`; omit it to act as the authenticated account. Validate ownership with `sender_profiles.list` or `sender_profiles.get`, and use the same selector for preflight reads, mutations, and follow-up reads. Profile grants cannot use this selector. Reauthorize for a different organization or a profile outside the grant. Never invent scope fields or request credentials.

## Check readiness

1. Use `account.get` to identify the authorized account context and surface the selected organization and Sender Profile. Return only the minimum account fields needed for the task.
2. Use `balance.get` before high-volume sends or when insufficient funds may block messaging. Report the currency and returned timestamp or freshness information when available. An account with no own balance row returns `balance: 0` and `initialized: false`; distinguish this from the returned effective balance under profile/organization billing inheritance.
3. Use `onboarding.status` to identify incomplete, pending, approved, or blocked onboarding steps. Preserve the distinction between an observed status and a remediation action. Its `found`/`item` envelope can return `found: false` when no conversion flow exists; that is not a tool error or proof of approval.

Mask identifiers where practical. Do not repeat account, KYC, contact, or billing details unnecessarily.

## Route remediation

This skill diagnoses readiness but does not mutate onboarding state.

- Route live SMS market requirements and setup calls to `sent-compliance`.
- Route Sender Profile boundary or tenancy design to `sender-profile-architect`.
- Route US A2P registration preparation to `sms-10dlc-registration`.
- Route WhatsApp Embedded Signup to `waba-embedded-signup`.
- Route RCS Business Messaging launch preparation to `rcs-agent-onboarding`.

When the user asks only whether an account is ready, report the blocking status and recommended public skill without inventing an operational fix.
