---
name: sent-messaging
description: Sends SMS, WhatsApp, or RCS messages through Sent and retrieves individual message status and activity history with the Sent MCP tools. Use when a user asks to send, schedule, or preview a message, check a message ID, confirm delivery status, inspect lifecycle events, investigate a timed-out or ambiguous send, or retry safely. Use messaging-performance-analyzer for aggregate delivery diagnosis.
---

# Sent Messaging

Operate direct message workflows with `messages.send`, `messages.get`, and `messages.activities.list`.

## Establish connection and scope

1. Let the MCP client perform OAuth 2.1/PKCE authorization. Never request, accept, print, or store tokens, API keys, authorization headers, client IDs, or secrets.
2. Surface the organization and Sender Profile selected by the active connection before a mutation. If the client context does not expose both, use `sent-account-readiness` to inspect the authorized scope before continuing.
3. Use an explicit, validated acting profile when an organization grant supports it.
4. Minimize sensitive output. Mask phone numbers where practical and do not repeat message bodies after the operator has reviewed them.

If MCP is unsupported or authorization fails, keep the skill usable for payload planning. Explain that execution requires a compatible client or reauthorization; never ask the user to paste a credential.

An organization grant may select an owned Sender Profile with the tool schema's optional `profileId`; omit it to act as the authenticated account. Validate ownership with `sender_profiles.list` or `sender_profiles.get`, and use the same selector for preflight reads, mutations, and follow-up reads. Profile grants cannot use this selector. Reauthorize for a different organization or a profile outside the grant. Never invent scope fields or request credentials.

## Inspect a message

- Use `messages.get` for the current record when a message identifier is known.
- Use `messages.activities.list` for lifecycle events and delivery evidence.
- State that an accepted or queued send is not proof of delivery. Report delivered only when the returned state or activity establishes delivery.
- Return identifiers, timestamps, and status evidence needed to answer the question, masking recipient data and omitting the message body unless it is necessary.

For aggregate trends, funnels, or root-cause analysis across many delivery records, hand off to `messaging-performance-analyzer`.

## Prepare a send

1. Resolve the intended channel, Sender Profile, recipient, existing template, variables, `scheduledAt`, and `idempotencyKey`. Sends are template-only: first use `templates.list` or `templates.get` in the same acting scope, reference its real ID or name in `template`, and provide every declared variable in `template.parameters`. Never pass message text as a template name or invent a free-form text argument. Do not invent missing values.
2. For a high-volume send, use `sent-account-readiness` to check `balance.get` before preparing the mutation. Stop if the available balance or account readiness is insufficient or unclear.
3. Build the exact `messages.send` arguments without calling the tool.
4. Show a payload preview that includes the selected organization, Sender Profile, channel, exact destination, existing template identifier and its reviewed content, variables, and scheduling/idempotency inputs. Show sensitive content once only; mask it where the operator can still verify the target.
5. Ask for explicit confirmation for this exact payload. General approval given earlier in the conversation is not sufficient.
6. Call `messages.send` immediately after that confirmation. If any payload value, scope, or elapsed context changes, discard the confirmation and preview again.

Never call `messages.send` without the preview and explicit confirmation immediately before the call.

## Schedule a send

`scheduledAt` is optional. Resolve the user's date, time, and timezone into an ISO-8601 timestamp with an explicit UTC offset or `Z`; offset-free timestamps are rejected. The instant must be 1 minute to 30 days ahead at execution. Include the exact local time and UTC instant in the preview, and revalidate the window before calling.

Acceptance returns `QUEUED` with `scheduledAt`; the message then moves to `SCHEDULED`, visible through `messages.get`, and releases around the requested time within a few minutes. Recipient quiet hours can defer it to the next allowed time, reported through `message.scheduled`. Do not promise an exact delivery time. Account scheduling limits can reject the send. There is no MCP reschedule or cancellation tool; do not invent one.

For schema-supported idempotency, use camelCase `idempotencyKey`; the same key can replay a cached send result for 24 hours. Keep the original key and arguments when recovering the same operation. A different intended send needs its own key. Idempotency does not replace review and confirmation.

## Handle results and retries

- Report the message identifier and the returned acceptance state. Say "accepted" or "queued" when that is all the response establishes; do not say "delivered."
- Use `messages.get` or `messages.activities.list` when the user asks for subsequent delivery state.
- Treat every retry as a new mutation: reconstruct the payload, show a fresh preview, and obtain new explicit confirmation immediately before the retry.
- Never blindly retry an ambiguous send. If the first call times out or its outcome is unknown, inspect `messages.get` and `messages.activities.list` when an identifier exists. Without conclusive evidence, report the unknown outcome and duplication risk. Only attempt another send after the operator chooses to do so and completes a new preview and confirmation.
