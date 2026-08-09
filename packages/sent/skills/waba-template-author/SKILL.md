---
name: waba-template-author
description: Writes, classifies, validates, and repairs WhatsApp templates using the Sent v3 template definition contract. Use for utility, marketing, authentication, OTP, Meta review, rejected templates, variables, buttons, channel overrides, or submission-ready Sent payloads.
---

# WhatsApp Template Author

Use this skill to turn a messaging intent into a valid body for `POST /v3/templates`, review it for WhatsApp policy risk, and explain the resulting lifecycle. Sent's template request is not Meta's Cloud API `components[]` shape.

## Source precedence

When official sources disagree:

1. Use the live Sent v3 OpenAPI for paths, request fields, and response shapes.
2. Use the most specific current Sent guide for lifecycle and policy semantics.
3. Preserve unknown provider values instead of forcing them into a closed enum.

The canonical references are the Sent template-definition guide, the v3 OpenAPI, and the webhook events reference. Do not use snapshot-era v2 examples.

## Authoring workflow

### 1. Establish intent and category

Collect the business event, recipient expectation, requested action, language, channel overrides, and realistic sample values. Choose:

- `UTILITY` for a specific non-promotional transaction, account, or service event.
- `MARKETING` for promotions, offers, re-engagement, product discovery, or mixed promotional content.
- `AUTHENTICATION` for one-time verification codes and supported authentication flows.

If content mixes utility and promotion, classify it as marketing or split it. See [references/waba-template-categories.md](references/waba-template-categories.md).

### 2. Build the Sent create request

`POST /v3/templates` accepts these top-level fields:

| Field | Requirement |
| --- | --- |
| `definition` | Required. Contains `header`, `body`, `footer`, `buttons`, optional `definitionVersion`, and optional `authenticationConfig`. |
| `category` | Optional: `UTILITY`, `MARKETING`, or `AUTHENTICATION`; omit for detection only when ambiguity is acceptable. |
| `language` | Optional locale such as `en_US`. |
| `creation_source` | Optional source string; `from-api` is the documented default. |
| `submit_for_review` | Optional Boolean; default `false`. Draft and validate before review. |
| `sandbox` | Optional Boolean for validation without side effects. |

Do not put `name`, `channels`, `body`, `header`, `buttons`, or `components` at the request root. `name` exists on update/response surfaces, not on the current create request.

```json
{
  "category": "UTILITY",
  "language": "en_US",
  "definition": {
    "header": null,
    "body": {
      "multiChannel": {
        "type": "body",
        "template": "Hi {{0:variable}}, order {{1:variable}} has shipped.",
        "variables": [
          {
            "id": 0,
            "name": "customerName",
            "type": "variable",
            "props": {"sample": "Avery"}
          },
          {
            "id": 1,
            "name": "orderNumber",
            "type": "variable",
            "props": {"sample": "A-1042"}
          }
        ]
      },
      "sms": null,
      "whatsapp": null,
      "rcs": null
    },
    "footer": null,
    "buttons": null,
    "definitionVersion": "1.0",
    "authenticationConfig": null
  },
  "creation_source": "from-api",
  "submit_for_review": false,
  "sandbox": true
}
```

Use `definition.body.multiChannel` as the channel-neutral body. `sms`, `whatsapp`, and `rcs` are complete channel overrides, not fragments. Keep each body at or below 1,024 characters.

### 3. Define variables exactly

Use placeholders such as `{{0:variable}}`, `{{1:link}}`, or `{{2:media}}`. Each placeholder needs one matching definition with:

- a unique non-negative integer `id`;
- a readable `name`;
- a matching `type`;
- `props.sample` with realistic review and preview data.

Keep placeholder IDs and variable IDs aligned inside every body override. Never output naked `{{1}}` placeholders in a Sent request.

### 4. Add supported buttons

Sent currently recognizes `QUICK_REPLY`, `URL`, `VOICE_CALL`, `PHONE_NUMBER`, and `COPY_CODE`. Enforce:

- 10 buttons total;
- at most 2 URL buttons;
- at most 1 voice-call button;
- at most 1 phone-number button;
- at most 1 copy-code button;
- quick replies may use the remaining slots, up to the total of 10.

Buttons use `id`, `type`, and `props`. Labels are at most 25 characters. Require type-specific properties: `quickReplyType`; `urlType` and `url`; `countryCode` and `phoneNumber`; or `offerCode`. Quick replies and calls-to-action may coexist—do not invent an XOR rule.

### 5. Handle authentication templates

For `AUTHENTICATION`, use `definition.authenticationConfig`:

```json
{
  "addSecurityRecommendation": true,
  "codeExpirationMinutes": 10
}
```

Expiration is 1–90 minutes. Keep authentication content to the verification purpose, use one code variable and the supported copy-code action, and do not add marketing language, unrelated links, media, or promotional buttons.

### 6. Validate before submission

Run:

```bash
python scripts/lint_waba_template.py template.json
```

The linter validates the Sent request shape, variables, the 1,024-character limit, channel overrides, every current button type, per-type limits, and authentication configuration. A Meta Cloud API example with `components[]` must fail with an explicit conversion error.

Use `sandbox: true` and `submit_for_review: false` while integrating. When the user is ready for provider review, show the final payload and explain that submission changes external state before proceeding.

### 7. Track the right lifecycle surface

Sent template resources use the known states `DRAFT`, `PENDING`, `APPROVED`, `REJECTED`, and `PAUSED`. Do not claim this is every value the API may ever return.

Template webhooks are WhatsApp approval events. They use `field: "templates"`, omit `sub_type` and `event`, and carry the provider status in `payload.status`:

```json
{
  "field": "templates",
  "timestamp": "2026-08-09T12:00:00Z",
  "payload": {
    "account_id": "00000000-0000-0000-0000-000000000000",
    "template_id": "11111111-1111-1111-1111-111111111111",
    "template_name": "order_update",
    "whatsapp_template_id": "2222222222222222",
    "status": "APPROVED",
    "language": "en_US",
    "category": "UTILITY",
    "channel": "whatsapp",
    "reason": null
  }
}
```

Common forwarded values include `PENDING`, `APPROVED`, `REJECTED`, and `CATEGORY_UPDATED`. Meta can also send values such as `PAUSED` or `DISABLED`. Persist the raw string, handle known values, and safely surface unknown ones. See [references/template-rejection-playbook.md](references/template-rejection-playbook.md).

## Boundaries

Use `template-builder-ui` for editor architecture and client-side validation UX. Use `sent-templates` to list, inspect, or delete existing templates through the connected Sent tools. Use `waba-embedded-signup` for WABA connection. Use `rcs-agent-onboarding` for current RCS launch capabilities.

Meta Cloud API payloads may appear in [references/waba-template-examples.md](references/waba-template-examples.md), but every such example must be clearly labelled non-Sent and must never be passed to the Sent linter as a valid request.
