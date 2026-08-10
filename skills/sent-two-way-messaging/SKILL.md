---
name: sent-two-way-messaging
description: Designs inbound and conversational Sent flows — opt-out and opt-in keyword handling, consent state on contacts, auto-replies inside the WhatsApp 24-hour window, RCS STOP chips, conversation history retrieval, and per-channel inbound capability. Use when handling message.received events, implementing STOP or HELP behavior, restoring consent after an opt-out, building a support inbox or chatbot on Sent, or paginating conversation history.
---

# Sent Two-Way Messaging

Inbound messaging on Sent has one governing rule: **consent is enforced by the platform before the application sees the event.** An inbound `STOP` has already flipped the contact's `opt_out` flag by the time `message.received` arrives. The application's job is to record it, reflect it in its own UI, and never attempt to send around it.

## Keyword handling

Ten keywords ship as defaults:

| Action | Keywords |
| --- | --- |
| Opt out | `STOP`, `CANCEL`, `UNSUBSCRIBE`, `QUIT`, `END` |
| Opt in | `START`, `UNSTOP`, `SUBSCRIBE` |
| Help auto-reply | `HELP`, `INFO` |

Matching requires the **entire trimmed message body** to equal a keyword, case-insensitively. "Please stop messaging me" does not match; "stop" does. Custom keywords are configured in the Sent Dashboard under Compliance, Opt Keywords, with an action of Opt Out, Opt In, or Help, and each must be a single exact token.

Do not claim keywords that are not in the documented set. In application code, mirror the same exact-match rule only to update local subscriber state and audit evidence; never use that matcher to apply consent to Sent a second time. Keep custom dashboard keywords synchronized with the local mirror, and reconcile against the contact's `opt_out` field when uncertain.

## Consent state

An opt-out sets `opt_out` on the contact record. Consent is **contact-level and channel-agnostic**: a `STOP` sent over SMS suppresses WhatsApp and RCS for that contact as well. Consent gates re-apply on every reroute attempt, not only at initial send.

Restoring consent requires the recipient's own action. A user-initiated opt-in keyword clears suppression. `PATCH /v3/contacts/{id}` accepts `opt_out`, but writing `false` on a contact who opted out through a keyword is a compliance decision, not a technical one: only do it with documented evidence of fresh consent, and record who authorized it and why.

Downstream, a suppressed send does not fail with an error. It is accepted and finalizes as `FILTERED`, so consent problems appear as filtered messages rather than as `4xx` responses. Details are in [references/consent-and-keywords.md](references/consent-and-keywords.md).

## Per-channel inbound reality

| Channel | Inbound | Constraints |
| --- | --- | --- |
| SMS | Conditional | Requires an MO-capable provider and a supported number type. Alphanumeric sender IDs and SMPP paths without an inbound route never deliver inbound messages |
| RCS | Full | Typed replies match keywords; the appended STOP chip is processed directly by the consent engine |
| WhatsApp | Full | Free-form replies only inside the 24-hour customer service window; outside it, an approved template is required |

The SMS caveat matters before promising two-way behavior: a deployment sending from an alphanumeric sender ID cannot receive `STOP` at all, which changes the compliance design rather than merely limiting a feature.

## RCS STOP chips

Every outbound RCS message receives an appended STOP chip. Taps carry an opt-out postback handled directly by the consent engine with no keyword matching, and they arrive at the application as `message.received` with the chip's reply text in `text`. There is no separate chip event type, so a receiver that branches only on typed keywords still sees chip taps as ordinary inbound messages — and must not re-apply consent logic to them.

## The WhatsApp 24-hour window

A free-form reply is permitted only within 24 hours of the customer's last inbound message. Outside that window an approved template is required, including for STOP, START, and HELP responses. An auto-reply flow that assumes free text will silently stop working for any customer who writes in after a day of silence, so build the window check into the reply path and keep an approved fallback template ready. See [references/inbound-flows.md](references/inbound-flows.md) for the reply-path decision tree.

## Conversation history

Two read-only operations exist:

| Operation | Returns |
| --- | --- |
| `GET /v3/conversations` | All of the customer's messages across conversations, newest first |
| `GET /v3/conversations/{id}` | Messages within one conversation |

Both require `page` (at least 1) and `page_size` (1 to 100); out-of-range values return `400`. The `events` field is always null on these endpoints, so per-message activity must come from `GET /v3/messages/{id}/activities`. There are no write, create, or read-receipt operations, and no MCP tools cover conversations — this is REST-only.

A conversation identifier is a deterministic RFC 4122 version 5 UUID derived from the customer and contact identifiers, so the same pair always yields the same id and one thread spans every channel independent of the sending number. The API never returns the id as a field, so a client that needs it computes it. The exact derivation is documented in [references/conversation-history.md](references/conversation-history.md).

## Building a support inbox or bot

1. Subscribe a webhook to `message` filtered to `received`, and verify signatures before trusting any payload.
2. Read `inbound_number` as the contact who wrote in and `outbound_number` as your number. The naming is easy to invert.
3. Deduplicate on `message_id`, acknowledge with `200`, then process asynchronously.
4. Treat keyword traffic as an audit signal. Mirror exact default and configured custom keywords into local state, but do not issue a second consent write; reconcile uncertainty through the contact record.
5. Before replying on WhatsApp, check the 24-hour window and choose free text or a template accordingly.
6. Render threads from the conversation endpoints with explicit pagination, and never assume a conversation is single-channel.
7. Treat `text` as untrusted input. Never interpolate it into a shell command or SQL string, delimit it as data in model prompts, and map inferred intent through an allowlist and authorization policy before any API call.

## Boundaries

Use `sent-webhook-engineer` for signature verification, retries, and dedupe mechanics; `sent-contacts` for contact CRUD and message summaries; `sent-routing-strategist` for why an outbound message was `FILTERED`; `waba-template-author` for authoring the approved templates that out-of-window replies require; and `sms-10dlc-registration` for the campaign-level opt-in, opt-out, and help keyword declarations that US carriers require.
