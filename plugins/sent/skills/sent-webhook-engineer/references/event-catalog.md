# Sent webhook event catalog and payload fields

## Table of contents

- [Envelope shape](#envelope-shape)
- [Outbound message status events](#outbound-message-status-events)
- [Inbound message events](#inbound-message-events)
- [Template events](#template-events)
- [Status semantics that change application logic](#status-semantics-that-change-application-logic)
- [Channel values in event payloads](#channel-values-in-event-payloads)
- [Reroute event sequences](#reroute-event-sequences)
- [Handler skeleton](#handler-skeleton)

## Envelope shape

Every delivery carries a `field` naming the event family. Message events add an `event` naming the transition. Template events carry neither `event` nor `sub_type`, and adding either to a template payload is a contract error.

```json
{
  "field": "message",
  "event": "message.delivered",
  "value": {
    "message_id": "8ba7b830-9dad-11d1-80b4-00c04fd430c8",
    "message_status": "DELIVERED",
    "channel": "sms",
    "account_id": "3f1a7c22-5d8e-4b90-91a2-6c4d0e8f7b31",
    "updated_at": "2026-03-14T09:21:44Z"
  }
}
```

Branch on `field` first and on `event` second. Preserve unrecognized values rather than throwing, because a new transition or a forwarded upstream status must not break an existing receiver.

## Outbound message status events

| Event | Final for the logical message | Meaning |
| --- | --- | --- |
| `message.queued` | No | Accepted into the pipeline; fires again after a reroute |
| `message.routed` | No | A concrete channel and provider were selected; fires again after a reroute |
| `message.sent` | No | Handed to the provider |
| `message.delivered` | Yes | Provider confirmed handset delivery |
| `message.read` | Yes | Recipient read the message; WhatsApp and RCS only |
| `message.failed` | Not always | One route attempt failed; automatic routing may queue another attempt on the same message id |
| `message.scheduled` | No | Parked by quiet-hours policy; re-enters the pipeline automatically |
| `message.filtered` | Yes | Blocked by a policy gate such as consent or a route denial |
| `message.blocked` | Yes | Blocked by an account precondition such as insufficient balance |

Payload fields on status events include `message_id`, `message_status`, `channel`, `account_id`, `updated_at`, and a sender-profile identifier when the send was profile-scoped. The application's own tenant identifier is never present, so keep a `message_id` mapping written before the send.

## Inbound message events

`message.received` carries a distinct payload:

```json
{
  "field": "message",
  "event": "message.received",
  "value": {
    "message_id": "6c1b0a99-2d7e-4c3e-8a5f-9f4e6a2c0b1d",
    "account_id": "3f1a7c22-5d8e-4b90-91a2-6c4d0e8f7b31",
    "inbound_number": "+14155550123",
    "outbound_number": "+14155559876",
    "text": "STOP",
    "channel": "sms",
    "received_at": "2026-03-14T09:22:10Z",
    "updated_at": "2026-03-14T09:22:10Z"
  }
}
```

`inbound_number` is the contact who wrote in and `outbound_number` is the number they wrote to; the naming trips up receivers that assume `inbound` means "our side." `text` may be null for non-text payloads. RCS suggestion-chip taps, including the appended STOP chip, arrive as `message.received` with the chip's reply text in `text` — there is no separate chip event type. Consent keywords are processed by Sent before the event reaches the application, so an inbound `STOP` is an audit record of an opt-out that already happened, not a request to perform one.

## Template events

```json
{
  "field": "templates",
  "value": {
    "account_id": "3f1a7c22-5d8e-4b90-91a2-6c4d0e8f7b31",
    "template_id": "7ba7b820-9dad-11d1-80b4-00c04fd430c8",
    "template_name": "order_confirmation",
    "whatsapp_template_id": "",
    "status": "APPROVED",
    "language": "en_US",
    "category": "UTILITY",
    "channel": "whatsapp"
  }
}
```

`whatsapp_template_id` is an empty string until Meta approves the template. Documented statuses are `PENDING`, `APPROVED`, `REJECTED`, and `CATEGORY_UPDATED`, and upstream Meta values such as `PAUSED` and `DISABLED` are forwarded verbatim — treat the field as an open string set. `reason` is present only when a reason exists, most often on rejection. Route rejection content to template authoring rather than trying to auto-correct copy in the receiver.

## Status semantics that change application logic

`filtered` and `blocked` are not carrier failures and must not feed retry logic. A `filtered` message hit a policy gate, most often consent or a route denial, so retrying the same send reproduces the same result and, for consent, would be a compliance violation. A `blocked` message hit an account precondition such as insufficient balance, an onboarding quota, or an unapproved template; the fix is an account action, after which a new send is appropriate.

`delivered` is the first event that proves the recipient's device received the message. The `202` from the send endpoint proves only acceptance, and `sent` proves only provider handoff. Any business rule with legal or financial weight should key on `delivered`.

`read` exists only on WhatsApp and RCS, and its absence on SMS is expected rather than a failure.

## Channel values in event payloads

| Value | Where it appears | Interpretation |
| --- | --- | --- |
| `sms`, `whatsapp`, `rcs` | Any event after routing | The concrete attempted route |
| `sent` | `message.queued`, `message.routed`, `message.scheduled` for automatic routing | Automatic routing requested; not yet a resolved route |
| `auto` | Terminal events for a message that ended before routing | Internal placeholder; the message never reached a channel |
| `null` | Per-recipient echo in the send response for auto-detect | Not a resolved route |

A terminal event carrying `auto` means the message failed or was gated before any route was attempted, which points at no matching route, invalid template parameters, a consent block, or an account precondition. Do not display `auto` to end users as a channel name.

## Reroute event sequences

Automatic routing may retry a failed message on another route, up to three distinct channel-and-provider pairs across the initial send and all reroutes. The retry re-runs the pipeline on the **same `message_id`**, so the event stream for one logical send can look like this:

```text
message.queued    channel=sent
message.routed    channel=whatsapp
message.sent      channel=whatsapp
message.failed    channel=whatsapp     (route-level failure)
message.queued    channel=sent         (reroute begins, same message_id)
message.routed    channel=sms
message.sent      channel=sms
message.delivered channel=sms
```

Three consequences for receiver design. A `message.failed` is not necessarily final, so reconcile the current message and activity state before triggering an irreversible failure action. Repeated `queued` and `routed` events for one id are normal and must be idempotent. The channel can change mid-stream, so store the channel per event rather than overwriting a single field and assuming it is stable.

Only route-level or carrier-level failures trigger a reroute. Recipient-level and content-level failures stay failed. A WhatsApp message that was accepted and then failed for a recipient-side reason both reroutes and records a recipient-scoped rule that WhatsApp is not deliverable for that number, which is the mechanism behind the WhatsApp-to-SMS fallback that customers observe on automatic routing.

## Handler skeleton

```python
from hashlib import sha256


def handle(event: dict, raw_body: bytes) -> None:
    field = event.get("field")
    value = event.get("value", {})

    if not record_receipt_once(sha256(raw_body).hexdigest(), event):
        return                         # exact transport retry; still answer 200

    if field == "templates":
        apply_template_state_once(value["template_id"], value.get("status"))
        return

    if field != "message":
        record_unknown_event(event)
        return

    name = event.get("event")
    if name == "message.received":
        record_inbound(value)          # consent already applied upstream
        return

    # Compare payload.updated_at with the projected event timestamp. Do not use
    # a global status rank: FAILED may be followed by a successful reroute.
    apply_if_newer(value["message_id"], value, value.get("updated_at"))

    if value.get("message_status") == "DELIVERED":
        perform_once(f"{value['message_id']}:DELIVERED", on_delivered, value)
```

Return `200` before doing slow work. Every branch, including the unknown-event branch, must acknowledge rather than raise, and genuine handler failures should return a non-2xx so Sent retries instead of silently discarding the event.
