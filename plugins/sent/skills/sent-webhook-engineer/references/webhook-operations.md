# Sent v3 webhook operations and delivery lifecycle

## Table of contents

- [Operation catalog](#operation-catalog)
- [Webhook object](#webhook-object)
- [Creating a webhook](#creating-a-webhook)
- [Event types and filters](#event-types-and-filters)
- [Delivery attempts, retries, and backoff](#delivery-attempts-retries-and-backoff)
- [Auto-disable and recovery](#auto-disable-and-recovery)
- [Delivery log triage](#delivery-log-triage)
- [Test deliveries](#test-deliveries)
- [Rate limits and sandbox behavior](#rate-limits-and-sandbox-behavior)
- [Environment and tenancy layout](#environment-and-tenancy-layout)

## Operation catalog

Ten operations manage webhooks. None of them is exposed through the Sent MCP server, so webhook work is REST-only even in an agent session that already holds an MCP connection.

| Operation | Purpose | Notes |
| --- | --- | --- |
| `POST /v3/webhooks` | Register an endpoint | `201` body carries the only full view of `signing_secret` |
| `GET /v3/webhooks` | List endpoints | Inspect `is_active` and `consecutive_failures` here first |
| `GET /v3/webhooks/event-types` | Discover subscribable event types | Use before hardcoding an `event_types` array |
| `GET /v3/webhooks/{id}` | Inspect one endpoint | Confirms configuration and health counters |
| `PUT /v3/webhooks/{id}` | Update configuration | Replaces the mutable configuration fields |
| `DELETE /v3/webhooks/{id}` | Remove an endpoint | Ignores `sandbox` and always deletes |
| `GET /v3/webhooks/{id}/events` | Delivery log | Requires `page` and `page_size`; optional `search` |
| `POST /v3/webhooks/{id}/rotate-secret` | Replace the signing secret | Old secret dies immediately; sensitive rate tier |
| `POST /v3/webhooks/{id}/test` | Send a synthetic signed delivery | Requires `event_type`; one attempt, no retry; sensitive rate tier |
| `PATCH /v3/webhooks/{id}/toggle-status` | Enable or disable | Operational pause without losing configuration |

## Webhook object

| Field | Meaning |
| --- | --- |
| `id` | Endpoint UUID; the value of `x-webhook-id` on every delivery |
| `display_name` | Required label; the only required field on create |
| `endpoint_url` | Destination; scheme must be `http://` or `https://` |
| `signing_secret` | `whsec_`-prefixed secret, fully visible only in the create and rotate responses |
| `is_active` | False after auto-disable or an explicit toggle |
| `event_types` | Subscribed event families, for example `["message", "templates"]` |
| `event_filters` | Per-family narrowing, for example `{"message": ["delivered", "failed"]}` |
| `retry_count` | 1–5, default 3 |
| `timeout_seconds` | 5–120, default 30 |
| `last_delivery_attempt_at` | Timestamp of the most recent attempt of any outcome |
| `last_successful_delivery_at` | Timestamp of the most recent 2xx |
| `consecutive_failures` | Counter of consecutive failed attempts; ten disables the endpoint |
| `created_at`, `updated_at` | Audit timestamps |

The gap between `last_delivery_attempt_at` and `last_successful_delivery_at` is the fastest health signal: a recent attempt with a stale success means the endpoint is failing right now.

## Creating a webhook

Only `display_name` is required, but a useful registration sets the destination, the subscriptions, and the delivery envelope explicitly.

```json
{
  "display_name": "Staging inbound and failures",
  "endpoint_url": "https://staging-hooks.example.com/webhooks/sent",
  "event_types": ["message"],
  "event_filters": {
    "message": ["received", "failed", "filtered", "blocked"]
  },
  "retry_count": 5,
  "timeout_seconds": 15
}
```

Choose `timeout_seconds` to match how fast the endpoint acknowledges, not how long processing takes. A receiver that returns `200` in 50 milliseconds and queues the work is compatible with the 5-second minimum; a receiver that writes to three downstream systems before responding will eventually breach even a 120-second ceiling under load and start accumulating consecutive failures.

Choose `retry_count` against the recovery profile of the receiver. Three attempts spread over roughly seven minutes suits a stateless service behind a load balancer. Five attempts, reaching further into the capped 60-minute backoff, suits a receiver whose dependency outages last longer than a few minutes.

## Event types and filters

Call `GET /v3/webhooks/event-types` rather than assuming the catalog. Two `field` families exist today: `message`, which carries an `event` naming the transition, and `templates`, which carries approval-state changes without an `event` field.

Filters matter more than they appear. An unfiltered `message` subscription delivers every transition, and because a reroute re-runs the pipeline on the same message id, `queued` and `routed` can arrive several times for one logical send. Subscribing only to the transitions the application acts on reduces both traffic and the chance of a double-processing bug.

A practical split by consumer:

| Consumer | Subscription |
| --- | --- |
| Delivery ledger and retries | `message` filtered to `delivered`, `failed`, `filtered`, `blocked` |
| Support inbox and auto-replies | `message` filtered to `received` |
| Read-receipt analytics | `message` filtered to `read` |
| Template governance | `templates` |
| Route debugging in a lower environment | `message` unfiltered |

## Delivery attempts, retries, and backoff

An attempt fails on any non-2xx response, a timeout past `timeout_seconds`, or a connection failure. Retries use exponential backoff: the first retry lands roughly one minute after the failure, each subsequent delay doubles, and the interval is capped at 60 minutes between attempts. Retries stop at the first 2xx or when `retry_count` is exhausted.

Delivery rows report `delivery_status` as `PENDING` while queued, `RETRYING` between attempts, `DELIVERED` on success, and `FAILED` once attempts are exhausted. A `DELIVERED` outcome resets the endpoint's `consecutive_failures` to zero.

Because retries are signed fresh, a retried delivery has a new `x-webhook-timestamp` and a new signature but the same payload — which is precisely why dedupe must key on payload semantics rather than on headers.

## Auto-disable and recovery

Ten consecutive failed delivery attempts disable the endpoint. Treat every failed attempt as capable of advancing the counter, whether it is a retry of one event or the first attempt for another; do not rely on event boundaries for protection. Any success resets the counter.

Once `is_active` is false, Sent stops delivering. Recovery sequence:

1. Read `GET /v3/webhooks/{id}` and confirm `is_active` and `consecutive_failures`.
2. Read the delivery log and identify the recurring `http_status_code` or `error_message`.
3. Fix the receiver and prove it locally against a signed synthetic delivery.
4. Re-enable the webhook with `PATCH /v3/webhooks/{id}/toggle-status` or in the Sent Dashboard.
5. Confirm recovery with `POST /v3/webhooks/{id}/test`, then verify the log shows `DELIVERED`.
6. Backfill the outage window from `GET /v3/messages/{id}` and `GET /v3/messages/{id}/activities` for messages whose state is stale, because events that failed permanently during the outage are not redelivered on re-enable.

Add monitoring on `consecutive_failures` so an alert fires at three or four rather than at ten.

## Delivery log triage

Each row of `GET /v3/webhooks/{id}/events` contains `id`, `event_type`, `event_data`, `delivery_status`, `http_status_code`, `response_body`, `delivery_attempts`, `error_message`, `created_at`, `processing_started_at`, and `processing_completed_at`. Both `page` and `page_size` are required; omitting them returns a validation error rather than a default page.

| Log evidence | Diagnosis |
| --- | --- |
| `http_status_code` 401 or 403 | The receiver is rejecting the signature, or authentication middleware sits in front of the webhook route |
| `http_status_code` 404 | Route path or environment mismatch in `endpoint_url` |
| `http_status_code` 5xx with a stack trace in `response_body` | Handler exception; fix the handler, not the registration |
| `error_message` naming a timeout with empty `http_status_code` | The receiver did not answer inside `timeout_seconds`; move work off the request path |
| `error_message` naming a connection or TLS failure | DNS, certificate, or firewall problem; the request never reached the application |
| `delivery_status` `DELIVERED` while the application has no record | The event was accepted and then dropped internally; instrument between acknowledgement and the queue |
| `delivery_attempts` climbing with `RETRYING` | Backoff is in progress; confirm the receiver recovered before it exhausts `retry_count` |

Keep the receiver route outside user-auth middleware. Sent authenticates by signature, and an intervening session or Bearer-auth layer produces a 401 that looks exactly like a signature bug.

## Test deliveries

`POST /v3/webhooks/{id}/test` takes an `event_type` in the body and sends a real signed request with a synthetic payload to the registered URL. It is delivered once with no retry, so each fix needs a fresh call. Treat it as the end-to-end proof that DNS, TLS, routing, signature verification, and acknowledgement all work together; use the local signing script for iteration because the test endpoint is limited to 10 requests per minute.

## Rate limits and sandbox behavior

Standard endpoints allow 200 requests per minute on a sliding window. `rotate-secret` and `test` allow 10 per minute on a fixed window. Rate-limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`) appear only on `429` responses, so a client cannot read remaining quota preemptively and must pace by design.

`"sandbox": true` on create or update validates and authenticates without persisting anything, which makes it useful for checking a payload shape in CI. `DELETE /v3/webhooks/{id}` ignores the flag and always deletes, so never use sandbox as a dry-run guard for deletion.

## Environment and tenancy layout

Register one webhook per environment and never share an endpoint across environments. Because auto-disable is per endpoint, a development receiver returning 500s cannot then disable production. For multi-tenant systems, remember that events do not carry the application's tenant identifier: persist `message_id -> {tenant, profile, logical_send_id, channel}` before sending and map inbound events by the receiving number. Organization-scoped credentials with `x-profile-id` can manage a child profile's webhooks; profile-scoped keys manage only their own and receive `403` if they send `x-profile-id`.
