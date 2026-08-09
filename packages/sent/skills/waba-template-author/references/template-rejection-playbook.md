# Template rejection and lifecycle playbook

Use this reference when a Sent template is pending, rejected, paused, disabled, or recategorized by the WhatsApp provider.

## Keep lifecycle surfaces separate

Sent template resources have these known states:

- `DRAFT`
- `PENDING`
- `APPROVED`
- `REJECTED`
- `PAUSED`

The template webhook is a provider-forwarding surface. Common `payload.status` values are `PENDING`, `APPROVED`, `REJECTED`, and `CATEGORY_UPDATED`; provider values such as `PAUSED` and `DISABLED` can also arrive. These lists serve different purposes. Persist the original status string and surface unknown values safely.

## Correct template event envelope

```json
{
  "field": "templates",
  "timestamp": "2026-08-09T12:00:00Z",
  "payload": {
    "account_id": "00000000-0000-0000-0000-000000000000",
    "template_id": "11111111-1111-1111-1111-111111111111",
    "template_name": "order_update",
    "whatsapp_template_id": "2222222222222222",
    "status": "REJECTED",
    "language": "en_US",
    "category": "UTILITY",
    "channel": "whatsapp",
    "reason": "Promotional content is not utility content."
  }
}
```

Template events use `field: "templates"` and omit both `sub_type` and `event`. Message events are different and do use `sub_type`.

## Response procedure

1. Verify the webhook signature using the raw body and reject stale timestamps.
2. Deduplicate on template ID plus status transition.
3. Persist the raw payload and reason.
4. Retrieve the current Sent template before editing; webhooks can be delayed or reordered.
5. Map the reason to the smallest justified change.
6. Convert any Meta-shaped source into the Sent `definition` contract.
7. Run the local linter and use `sandbox: true`.
8. Show the final diff and obtain confirmation before review submission.

## Common remediations

| Symptom | Appropriate response |
| --- | --- |
| Utility content recategorized | Remove promotion or deliberately use `MARKETING`; do not argue from transactional context alone. |
| Missing or unrealistic samples | Add `props.sample` for every placeholder without using customer data. |
| Invalid variable format | Replace naked placeholders with `{{0:variable}}` and align IDs. |
| Unsupported create shape | Move fields into `definition`; reject Meta `components[]` as a Sent request. |
| Button validation | Enforce 10 total and per-type limits; allow quick replies and CTA buttons to coexist. |
| `PAUSED` or `DISABLED` | Stop new WhatsApp sends with the template, preserve the provider value, and surface it for review. |
| Unknown status | Store and display it; do not silently coerce it to rejected or approved. |

Do not claim provider approval timing as a guarantee, and do not repeatedly resubmit unchanged content.
