---
name: sent-analytics
description: Queries Sent phone-number capabilities and aggregate messaging, deliverability, and contact analytics with the Sent MCP tools. Use when a user asks for number lookup, line or channel capability, messages sent, delivery rate, contact growth, dashboard metrics, period comparisons, or date-bounded trends. Use messaging-performance-analyzer for message-level evidence and root-cause diagnosis.
---

# Sent Analytics

Use `numbers.lookup`, `dashboard.messages_sent`, `dashboard.deliverability`, and `dashboard.contacts` for analytics and paid external number lookup. `numbers.lookup` is state-changing and non-idempotent, even though it does not send a message.

## Establish context

Use client-managed OAuth 2.1/PKCE. Never request or expose a token, API key, authorization header, client ID, or secret. Identify the active organization and Sender Profile when the client exposes them.

Minimize sensitive output: mask phone numbers, aggregate where possible, and omit contact, KYC, account, and message-body data that is not needed to answer the question.

An organization grant may select an owned Sender Profile with the tool schema's optional `profileId`; omit it to act as the authenticated account. Validate ownership with `sender_profiles.list` or `sender_profiles.get`, and use the same selector for preflight reads, mutations, and follow-up reads. Profile grants cannot use this selector. Reauthorize for a different organization or a profile outside the grant. Never invent scope fields or request credentials.

## Look up a number

Use `numbers.lookup` to obtain available capability, formatting, type, or routing signals for the supplied number. A lookup describes capability; it is not evidence of opt-in, consent, ownership, identity, or permission to message. State that distinction whenever the result could be used to plan outreach. The paid lookup allowance is 1000 calls per authenticated account scope per UTC day, shared across acting profiles and resetting at 00:00 UTC. Respect quota errors; do not rotate profiles or retry in a loop. Temporary quota-check failure can allow lookup through, which does not make it free.

## Query dashboard metrics

1. Resolve a date range, timezone, and aggregation grain for `dashboard.messages_sent`. It counts delivered/read outbound SMS and WhatsApp in supported preset or custom windows, using 15-minute, hourly, or daily buckets; do not describe it as all queued sends or RCS volume.
2. `dashboard.deliverability` returns an all-time outbound percentage: `(SENT + DELIVERED + READ) / (all except FILTERED and BLOCKED)`. It is not a date-bounded delivery-only success rate. Do not invent date filters or claim a last-week comparison from this scalar.
3. `dashboard.contacts` returns the current total contact count. One snapshot does not establish contact growth, activity, or a historical trend.
4. Keep comparisons on the same organization, acting profile, supported time window, timezone, channel coverage, and grain. State the tool's actual scope: date range/timezone for volume, all-time for deliverability, snapshot for contacts.

Label processing and delivery states according to the evidence; never collapse accepted into delivered. Use exported message-level evidence or another documented source for unsupported historical comparisons.

## Choose aggregate analytics or diagnosis

Use this skill for dashboard totals, rates, and trends. Use `messaging-performance-analyzer` when the request involves message-level delivery records, funnel drop-off, error-code clustering, or root-cause diagnosis. A deliverability dashboard can locate a change; it does not by itself prove the operational cause.
