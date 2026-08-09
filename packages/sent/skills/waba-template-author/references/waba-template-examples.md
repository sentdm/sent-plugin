# Sent template examples

All examples in the first section are bodies for `POST /v3/templates` and are expected to pass `scripts/lint_waba_template.py`. Synthetic values are used throughout.

## Utility with a WhatsApp override

<!-- sent-template-request -->
```json
{
  "category": "UTILITY",
  "language": "en_US",
  "definition": {
    "header": null,
    "body": {
      "multiChannel": {
        "type": "body",
        "template": "Hi {{0:variable}}, your appointment is on {{1:variable}}.",
        "variables": [
          {"id": 0, "name": "customerName", "type": "variable", "props": {"sample": "Avery"}},
          {"id": 1, "name": "appointmentTime", "type": "variable", "props": {"sample": "August 14 at 10:30 AM"}}
        ]
      },
      "whatsapp": {
        "type": "body",
        "template": "Hello {{0:variable}}. Your appointment is confirmed for {{1:variable}}.",
        "variables": [
          {"id": 0, "name": "customerName", "type": "variable", "props": {"sample": "Avery"}},
          {"id": 1, "name": "appointmentTime", "type": "variable", "props": {"sample": "August 14 at 10:30 AM"}}
        ]
      }
    },
    "footer": {"type": "text", "template": "Acme Scheduling", "variables": []},
    "buttons": [
      {"id": 1, "type": "QUICK_REPLY", "props": {"text": "Confirm", "quickReplyType": "custom"}},
      {"id": 2, "type": "URL", "props": {"text": "Manage booking", "urlType": "static", "url": "https://example.com/bookings"}}
    ],
    "definitionVersion": "1.0",
    "authenticationConfig": null
  },
  "creation_source": "from-api",
  "submit_for_review": false,
  "sandbox": true
}
```

## Authentication

<!-- sent-template-request -->
```json
{
  "category": "AUTHENTICATION",
  "language": "en_US",
  "definition": {
    "header": null,
    "body": {
      "multiChannel": {
        "type": "body",
        "template": "Your verification code is {{0:variable}}.",
        "variables": [
          {"id": 0, "name": "verificationCode", "type": "variable", "props": {"sample": "482193"}}
        ]
      }
    },
    "footer": null,
    "buttons": [
      {"id": 1, "type": "COPY_CODE", "props": {"text": "Copy code", "offerCode": "482193"}}
    ],
    "definitionVersion": "1.0",
    "authenticationConfig": {
      "addSecurityRecommendation": true,
      "codeExpirationMinutes": 10
    }
  },
  "creation_source": "from-api",
  "submit_for_review": false,
  "sandbox": true
}
```

## Meta Cloud API example — not a Sent request

The following abbreviated shape is deliberately separate. It must not pass the Sent linter or be posted to `POST /v3/templates`; convert its `components[]` into Sent's `definition` structure first.

```json
{
  "name": "order_update",
  "language": "en_US",
  "category": "UTILITY",
  "components": [
    {"type": "BODY", "text": "Your order {{1}} has shipped."}
  ]
}
```
