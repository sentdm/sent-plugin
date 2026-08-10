# Conversation history retrieval

## Operations

| Operation | Returns | Required query parameters |
| --- | --- | --- |
| `GET /v3/conversations` | All of the calling customer's messages across conversations, newest first | `page` (>= 1), `page_size` (1–100) |
| `GET /v3/conversations/{id}` | Messages within one conversation | `page` (>= 1), `page_size` (1–100) |

Both are read-only. There is no create, update, delete, participant, or read-receipt operation, and no MCP tool covers conversations, so this is REST-only work even inside an MCP-authorized session. Out-of-range pagination values return `400`; missing credentials return `401`.

The OpenAPI summaries for these two operations are swapped relative to their descriptions — the list endpoint is summarized as "list conversation messages" while its description says messages across all conversations, and the single-conversation variant reads the opposite way. Trust the descriptions and the behavior above.

## Message record fields

Each returned message carries:

`id`, `customer_id`, `contact_id`, `phone`, `phone_international`, `region_code`, `template_id`, `template_name`, `template_category`, `channel`, `message_body` (with `header`, `content`, `footer`, and `buttons`), `status`, `direction` (`INBOUND` or `OUTBOUND`), `created_at`, `price`, `active_contact_price`, and `events`.

`events` is always null on these endpoints. Per-message activity history must come from `GET /v3/messages/{id}/activities`, which is also the only place a reroute's sequence of attempted routes is visible.

## Conversation identifiers

A conversation id is a deterministic RFC 4122 version 5 UUID. It is derived from the namespace `9f4e6a2c-0b1d-4c3e-8a5f-2d7e6c1b0a99` and the name `{customer_id}:{contact_id}`, where both identifiers are lowercase canonical UUIDs and the customer id comes first. Version 5 uses SHA-1 name-based hashing, equivalent to PostgreSQL's `uuid_generate_v5`.

```python
import uuid

NAMESPACE = uuid.UUID("9f4e6a2c-0b1d-4c3e-8a5f-2d7e6c1b0a99")


def conversation_id(customer_id: str, contact_id: str) -> str:
    name = f"{customer_id.lower()}:{contact_id.lower()}"
    return str(uuid.uuid5(NAMESPACE, name))
```

Three properties follow. The same customer-and-contact pair always yields the same id, so it can be computed offline and used as a stable local key. The API never returns the id as a field, so a client that needs it must derive it. And because the id depends only on customer and contact, **one thread spans every channel** and is independent of which sending number or channel was used — a customer who moves between SMS and WhatsApp stays in one conversation.

## Pagination strategy

Always pass `page` and `page_size` explicitly; there is no usable default. Results are newest-first, so page 1 is the most recent slice and a thread view should either reverse each page for display or fetch from the oldest page.

Because the collection grows while it is being read, a long backfill can shift items across page boundaries. For an initial sync, page through quickly with `page_size: 100` and reconcile by message `id`, then switch to incremental updates driven by `message.received` and status webhooks rather than repeated full scans. Pacing matters as well: the standard limit is 200 requests per minute and quota headers appear only on `429` responses, so a paginated backfill must be throttled by design.

## Choosing between conversations and messages endpoints

| Need | Use |
| --- | --- |
| Render a customer thread | `GET /v3/conversations/{id}` with derived id |
| Show a recent-activity feed across all customers | `GET /v3/conversations` |
| Current status of one specific message | `GET /v3/messages/{id}` |
| Route attempts and reroute history | `GET /v3/messages/{id}/activities` |
| React to new inbound traffic in real time | `message.received` webhook |

Do not poll the conversation endpoints for near-real-time inbound handling. Webhooks are the delivery mechanism for new inbound messages, and polling both wastes quota and adds latency.
