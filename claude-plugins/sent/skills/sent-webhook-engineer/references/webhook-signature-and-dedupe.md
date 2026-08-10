# Webhook signature verification and event deduplication

## Table of contents

- [Signature scheme](#signature-scheme)
- [Why the raw body matters](#why-the-raw-body-matters)
- [Replay rejection](#replay-rejection)
- [Secret handling and rotation](#secret-handling-and-rotation)
- [Deduplication without an event id](#deduplication-without-an-event-id)
- [Ordering and out-of-sequence events](#ordering-and-out-of-sequence-events)
- [Acceptance tests for a receiver](#acceptance-tests-for-a-receiver)

## Signature scheme

Sent signs each delivery with HMAC-SHA256 and publishes three headers.

| Header | Example | Notes |
| --- | --- | --- |
| `x-webhook-signature` | `v1,K7t9...==` | Version tag, comma, base64 digest |
| `x-webhook-id` | `0f8fad5b-d9cb-469f-a165-70867728950e` | Endpoint UUID, constant across deliveries |
| `x-webhook-timestamp` | `1767225600` | Unix seconds |

The signed content is the concatenation `{x-webhook-id}.{x-webhook-timestamp}.{raw_body}`, where the first two components are joined by literal `.` characters and the third is the untouched request body. The HMAC key is the signing secret with the leading `whsec_` removed and the remainder base64-decoded, which yields raw key bytes rather than an ASCII string. The digest is base64-encoded and prefixed with `v1,`.

The construction is compatible with Svix-style verification, so an existing Svix helper can usually be adapted by pointing it at these header names. No Sent SDK provides a built-in verifier in any of the seven supported languages, so this logic is application code in every deployment.

Compare signatures with a constant-time function (`hmac.compare_digest`, `crypto.timingSafeEqual`, `MessageDigest.isEqual`, `hash_equals`, `subtle.ConstantTimeCompare`). A plain `==` on a signature invites a timing oracle.

## Why the raw body matters

The signature covers exact bytes. Any transformation between the socket and the verification step invalidates it: JSON parse and re-serialize, key reordering, whitespace normalization, Unicode escaping changes, trailing-newline insertion, gzip re-encoding, or a proxy that rewrites the body. This is the single most common cause of signature failures, and it usually appears as "verification works with curl but fails behind the framework."

Diagnose it by logging the byte length and a SHA-256 of the body at the verification point and comparing against the `Content-Length` header. A mismatch means something consumed and rebuilt the body upstream.

## Replay rejection

Reject a delivery when `abs(now - x-webhook-timestamp) > 300` seconds. The five-minute tolerance is the documented value and appears as `TOLERANCE_SECONDS = 300` in the official samples for every language. Two operational consequences follow. First, hosts must run NTP; clock drift beyond five minutes rejects perfectly valid traffic and the symptom looks identical to a signature bug. Second, because retries can arrive up to 60 minutes after the original attempt, each retry is signed with its own fresh timestamp — the receiver must never cache the first timestamp and compare later deliveries against it.

For forensic replay of an archived delivery, verify the HMAC while explicitly skipping the freshness check rather than widening the production tolerance.

## Secret handling and rotation

The full `signing_secret` appears exactly once, in the `201` body of `POST /v3/webhooks`. Store it in a secret manager keyed by webhook id and environment. `GET /v3/webhooks/{id}` is the way to confirm which endpoint a stored secret belongs to.

`POST /v3/webhooks/{id}/rotate-secret` returns the replacement and invalidates the previous secret immediately. There is no dual-signing window on Sent's side, so the receiver must provide the overlap:

1. Deploy a receiver that reads a primary secret and an optional secondary secret and accepts a delivery that verifies under either.
2. Put the current secret in both slots and deploy.
3. Rotate, and write the new secret into the primary slot.
4. Confirm from the delivery log that recent attempts are `DELIVERED`.
5. Clear the secondary slot and deploy again.

Rotate on compromise, on operator offboarding, and on a fixed schedule. The rotate endpoint is on the sensitive tier of 10 requests per minute, so automation must not loop over many webhooks quickly.

## Deduplication without an event id

Sent does not publish a per-event unique identifier. `x-webhook-id` names the endpoint and is identical on every delivery, so using it as a dedupe key collapses all events into a single row. Derive keys from event semantics instead:

| Event | Idempotency key | Rationale |
| --- | --- | --- |
| Outbound status (`message.queued`, `.routed`, `.sent`, `.delivered`, `.read`, `.failed`, `.scheduled`, `.filtered`, `.blocked`) | `sha256(raw_body)` for receipt dedupe; `{message_id}:{message_status}` for one-time business effects | Exact delivery retries carry the same payload, while a reroute may legitimately repeat a status with a different channel or timestamp |
| Inbound (`message.received`) | `{message_id}` | Each inbound message has its own id |
| Template (`field: "templates"`) | `{template_id}:{status}` | Approval transitions are the meaningful unit |
| Anything unrecognized | `sha256(raw_body)` | Absorbs an exact retry without depending on a fresh retry timestamp |

Persist the key with a unique constraint and treat an insert conflict as "already processed, return 200." A duplicate must never repeat side effects such as charging a card, sending a follow-up message, or writing a second audit row.

Reroutes make two layers necessary. Use a raw-body hash to suppress exact transport retries, but retain distinct reroute events in an append-only receipt ledger because their channel or `updated_at` differs. Gate one-time business effects separately—for example, send a receipt only once for `{message_id}:DELIVERED`—so preserving route evidence does not duplicate side effects.

## Ordering and out-of-sequence events

Delivery order is not guaranteed, and a global status rank is unsafe: automatic routing can emit `FAILED`, then a newer `QUEUED`, `ROUTED`, and `DELIVERED` on the same message id. Persist the append-only receipt first, then update the current projection only when the payload's `updated_at` is newer than the projected event timestamp. Use receipt order only as a tie-breaker, preserve the attempted channel per event, and reconcile uncertain final state with `GET /v3/messages/{id}` plus activities. Never make `FAILED` permanently outrank a later successful reroute.

## Acceptance tests for a receiver

A receiver is ready when all of the following hold:

1. A validly signed delivery returns `200`.
2. A body with a single byte changed returns `401`.
3. A delivery signed with a different secret returns `401`.
4. A delivery whose timestamp is 400 seconds old returns `401`.
5. A delivery whose `x-webhook-id` is altered returns `401`.
6. The same valid delivery sent twice returns `200` twice and performs side effects once.
7. A `message.delivered` followed by a late `message.sent` leaves the stored status at `DELIVERED`.
8. A handler exception still returns a non-2xx status so Sent retries, rather than swallowing the error and returning `200`.
9. Processing that exceeds one second happens after the response, not before it.

Use `scripts/verify_signature.py --sign` to produce headers for cases 1, 6, and 7, and mutate them for the negative cases.
