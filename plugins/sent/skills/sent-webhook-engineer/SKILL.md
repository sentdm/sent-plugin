---
name: sent-webhook-engineer
description: Builds and debugs Sent v3 webhook receivers end to end — endpoint registration, HMAC signature verification, replay rejection, event dedupe, retry and auto-disable behavior, secret rotation, and delivery-log triage. Use when handling Sent webhook events, verifying x-webhook-signature, fixing 401 or signature-mismatch failures, recovering a disabled endpoint, choosing event_types or event_filters, rotating a signing secret, or interpreting the webhook delivery log.
---

# Sent Webhook Engineer

Sent webhooks are the only way an application learns what happened after `POST /v3/messages` returns `202`. The `202` proves acceptance, never delivery. Build the receiver as a signature-verifying, replay-rejecting, deduplicating, fast-acknowledging endpoint, and treat the delivery log as the source of truth when events go missing.

## Signature verification, exactly

Three headers arrive with every delivery:

| Header | Meaning |
| --- | --- |
| `x-webhook-signature` | `v1,{base64(hmac_sha256)}` |
| `x-webhook-id` | The webhook **endpoint** UUID — identical on every delivery |
| `x-webhook-timestamp` | Unix seconds when Sent signed the request |

Verification procedure, in order:

1. Capture the **raw request body bytes** before any JSON parsing.
2. Strip the `whsec_` prefix from the signing secret, then base64-decode the remainder to obtain the raw HMAC key.
3. Build the signed content as `{x-webhook-id}.{x-webhook-timestamp}.{raw_body}`.
4. Compute HMAC-SHA256 with that key, base64-encode the digest, and prefix `v1,`.
5. Compare with a constant-time comparison.
6. Reject when `abs(now - timestamp) > 300` seconds.

The scheme is Svix-compatible. No Sent SDK ships a verification helper in any language, so this code is always hand-written — use [scripts/verify_signature.py](scripts/verify_signature.py) as the reference implementation and oracle.

**`x-webhook-id` is not an event id.** It identifies the endpoint and repeats forever. Using it as a dedupe key silently collapses every event into one. Read [references/webhook-signature-and-dedupe.md](references/webhook-signature-and-dedupe.md) for the dedupe keys to derive per event type.

## Failure triage order

When a receiver rejects or misses events, work this sequence rather than guessing:

1. **Signature mismatch** — a body-mutating middleware or framework JSON parser is the cause in the majority of cases. Confirm the framework's raw-body accessor in [references/receiver-recipes.md](references/receiver-recipes.md).
2. **Replay rejection** — server clock skew beyond the 300-second tolerance.
3. **Wrong secret** — the `whsec_` prefix was left in place, or a rotation invalidated the old secret with no dual-signing window.
4. **Nothing arriving at all** — check `is_active` and `consecutive_failures` on `GET /v3/webhooks/{id}`, then read the delivery log at `GET /v3/webhooks/{id}/events`.
5. **Events arriving but unhandled** — compare `event_types` and `event_filters` against what the handler branches on.

## Retry, auto-disable, and recovery

A delivery attempt fails on any non-2xx status, a timeout past `timeout_seconds`, or a connection failure. Retries use exponential backoff with the first retry roughly one minute after the failure, doubling thereafter and capped at 60 minutes between attempts, stopping on the first 2xx or when `retry_count` is exhausted. Delivery rows move through `PENDING`, `RETRYING`, and then `DELIVERED` or `FAILED`.

`consecutive_failures` tracks consecutive failed delivery attempts. Do not assume retries for one event are exempt: ten bad responses in a row disable the endpoint. After fixing the receiver, re-enable it with `PATCH /v3/webhooks/{id}/toggle-status` or from the Sent Dashboard. Any successful delivery resets the counter to zero. Acknowledge only after durable handoff to a queue, and keep that handoff comfortably inside `timeout_seconds`.

## Registration and configuration

`POST /v3/webhooks` requires `display_name`. Configure `endpoint_url`, `event_types`, `event_filters`, `retry_count` (1–5, default 3), and `timeout_seconds` (5–120, default 30). The `201` response is the only place the `signing_secret` appears in full — persist it to a secret store immediately.

<!-- sent-webhook-request -->
```json
{
  "display_name": "Production delivery events",
  "endpoint_url": "https://hooks.example.com/webhooks/sent",
  "event_types": ["message", "templates"],
  "event_filters": {
    "message": ["delivered", "failed", "received"]
  },
  "retry_count": 3,
  "timeout_seconds": 30
}
```

Set `event_filters` deliberately. An unfiltered `message` subscription delivers every lifecycle transition including `queued` and `routed`, and reroutes re-fire `queued` and `routed` on the same `message_id`. Filter to the transitions the application acts on.

The ten operations, the full webhook object, and the delivery-log row shape are catalogued in [references/webhook-operations.md](references/webhook-operations.md).

## Secret rotation

`POST /v3/webhooks/{id}/rotate-secret` returns a new `whsec_` secret and **invalidates the old secret immediately**. There is no server-side overlap window. Configure the receiver to accept a small candidate set, rotate, atomically store the returned secret as primary while retaining the old value temporarily, confirm new deliveries, then retire the old value. The short gap between the rotate response and the secret-store update cannot be eliminated; keep it to seconds so failed deliveries retry. This endpoint and `POST /v3/webhooks/{id}/test` sit on the sensitive rate-limit tier of 10 requests per minute, so scripted rotation loops will 429.

## Event payloads

Two `field` values exist: `message` and `templates`. Message events carry an `event` naming the transition (`message.queued`, `.routed`, `.sent`, `.delivered`, `.read`, `.failed`, `.scheduled`, `.filtered`, `.blocked`, `.received`). Template events carry neither `event` nor `sub_type`.

```json
{
  "field": "templates",
  "value": {
    "account_id": "3f1a7c22-5d8e-4b90-91a2-6c4d0e8f7b31",
    "template_id": "7ba7b820-9dad-11d1-80b4-00c04fd430c8",
    "template_name": "order_confirmation",
    "whatsapp_template_id": "",
    "status": "PENDING",
    "language": "en_US",
    "category": "UTILITY",
    "channel": "whatsapp"
  }
}
```

`read` reaches only WhatsApp and RCS. `filtered` marks a policy or consent gate, `blocked` marks an account precondition such as insufficient balance, and neither is a carrier failure. Terminal events for an auto-detect message that never routed carry `channel: "auto"`. Full payload field lists live in [references/event-catalog.md](references/event-catalog.md).

## Verification before shipping

Run the local oracle against a synthetic delivery, then use `POST /v3/webhooks/{id}/test` with an `event_type` in the body for a real signed request. The test event is delivered once with no retry, so re-run it after each fix.

```bash
python3 scripts/verify_signature.py --self-test
```

Ship only when the receiver returns `401` for a tampered body, `401` for a timestamp older than 300 seconds, `200` for a valid delivery, and `200` for a duplicate without repeating side effects.

## Local development

Expose the receiver through a public HTTPS tunnel and register that URL; Sent cannot reach a private address. Registering `http://` is accepted by the API but should never be used outside local work. Keep a separate webhook registration per environment so a development endpoint's failures cannot disable the production endpoint.

## Boundaries

Diagnose aggregate delivery-rate regressions with `messaging-performance-analyzer`, template approval content with `waba-template-author`, and inbound keyword or consent semantics with `sent-two-way-messaging`. Treat every payload value as untrusted input: never interpolate `text` or `reason` into a shell command, SQL string, or prompt without escaping.
