# Inbound flow design

## Table of contents

- [Inbound event shape](#inbound-event-shape)
- [Reply-path decision tree](#reply-path-decision-tree)
- [The WhatsApp 24-hour window](#the-whatsapp-24-hour-window)
- [Support inbox architecture](#support-inbox-architecture)
- [Bot and auto-reply design](#bot-and-auto-reply-design)
- [Treating inbound content as untrusted](#treating-inbound-content-as-untrusted)
- [Testing an inbound flow](#testing-an-inbound-flow)

## Inbound event shape

```json
{
  "field": "message",
  "event": "message.received",
  "value": {
    "message_id": "6c1b0a99-2d7e-4c3e-8a5f-9f4e6a2c0b1d",
    "account_id": "3f1a7c22-5d8e-4b90-91a2-6c4d0e8f7b31",
    "inbound_number": "+14155550123",
    "outbound_number": "+14155559876",
    "text": "Where is my order?",
    "channel": "whatsapp",
    "received_at": "2026-03-14T09:22:10Z",
    "updated_at": "2026-03-14T09:22:10Z"
  }
}
```

`inbound_number` is the contact who wrote in; `outbound_number` is your number that received it. Inverting these is a common defect that sends replies to your own number. `text` may be null for non-text payloads. The application's tenant identifier is never present, so map ownership from `outbound_number` to the tenant and profile that own it.

Dedupe on `message_id`. Inbound events, like all Sent webhook deliveries, may be retried.

## Reply-path decision tree

```text
inbound message.received
├── Is text an exact keyword match handled by the platform?
│   ├── Opt out / opt in → consent already applied. Record it. Do NOT reply with your own confirmation
│   │                       unless product requirements demand one, and never re-set consent yourself.
│   └── Help            → the platform sends the help auto-reply. Optionally log it.
└── Anything else
    ├── channel == whatsapp
    │   ├── within 24h of the contact's last inbound → free-form reply permitted
    │   └── outside 24h                              → an approved template is required
    ├── channel == rcs → reply permitted; a STOP chip is appended automatically
    └── channel == sms → reply permitted if the number supports outbound on that route
```

The branch that breaks in production is the WhatsApp window: a flow tested minutes after an inbound message succeeds with free text and then fails for a customer who replies a day later.

## The WhatsApp 24-hour window

Free-form replies are permitted only inside 24 hours of the customer's last inbound message. Outside it, sending requires an approved template — including replies about STOP, START, and HELP. Practical requirements:

1. Persist the last inbound timestamp per contact, sourced from `received_at`.
2. Evaluate the window at reply time, not at enqueue time; a queued reply can age past the boundary before it is sent.
3. Keep an approved fallback template for each conversational intent that could be answered late.
4. When a human agent replies from an internal inbox, show the remaining window in the UI so the agent understands why the composer switches to templates.

Treat window expiry as an expected state rather than an error path.

## Support inbox architecture

A workable design separates four responsibilities:

| Component | Responsibility |
| --- | --- |
| Webhook receiver | Verify the signature, dedupe on `message_id`, return `200` fast |
| Event worker | Resolve the contact and tenant, persist the message, apply routing to a queue |
| Thread view | Render history from the conversation endpoints with explicit pagination |
| Reply service | Enforce the window rule, choose free text or template, send, and record the outbound `message_id` |

Subscribe the webhook to `message` filtered to `received` so the inbox is not flooded with outbound lifecycle transitions. Keep a separate registration for delivery statuses if the same service consumes both.

Threads are cross-channel by construction. A single conversation can contain SMS, WhatsApp, and RCS messages, so a UI that groups by channel will fragment what the customer experiences as one conversation. Group by contact.

## Bot and auto-reply design

Rules that keep an automated responder safe and compliant:

- Mirror the platform's exact keyword rules only for local state and audit. Consent is already applied, so never issue a second consent write from the matcher.
- Never auto-reply to an opt-out. A contact who just opted out is suppressed, and an attempted confirmation will finalize as `FILTERED`.
- Rate-limit per contact. An inbound loop between two automated systems is the classic runaway cost incident.
- Make replies idempotent on the inbound `message_id` so a retried webhook cannot produce a second reply.
- Log the inbound and outbound pair with both message ids so a conversation can be reconstructed for audit.
- Degrade to a human queue when intent is unclear, especially when the message expresses opt-out intent in a sentence that keyword matching cannot catch.

## Treating inbound content as untrusted

Inbound `text` is attacker-controllable. Three concrete rules:

1. Never interpolate it into shell commands, SQL, or template strings without parameterization or escaping.
2. Never translate inbound content directly into an arbitrary Sent API call, contact mutation, or template choice. Map inferred intent through an allowlist, authorization checks, and confirmation rules.
3. When inbound text is passed to a language model, keep it inside a clearly delimited data section, and treat any instruction it contains as data rather than as a directive.

The same applies to any `reason` or `response_body` value that arrives from the platform's own delivery logs.

## Testing an inbound flow

Without a real handset, exercise the receiver with a locally signed synthetic `message.received` payload; the webhook skill's signing script produces the headers. Then use `POST /v3/webhooks/{id}/test` for an end-to-end proof of DNS, TLS, and signature verification. `"sandbox": true` on sends validates the request shape without executing.

A checklist before shipping:

- an inbound event with keyword text updates the local consent mirror but produces no second consent write to Sent;
- a duplicate inbound event produces exactly one reply;
- a reply attempt outside the WhatsApp window selects a template rather than failing;
- a reply to a suppressed contact is not attempted at all;
- `inbound_number` and `outbound_number` are mapped to contact and tenant in the correct direction;
- conversation pagination is explicit and handles `page_size` at its bounds of 1 and 100.
