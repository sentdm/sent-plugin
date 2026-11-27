---
name: sms-10dlc-registration
description: Prepares and validates Sent US A2P 10DLC brand and campaign registration through Sender Profiles, including inheritance, all campaign use cases, opt-in evidence, sample-message policy, autoresponses, sandbox validation, TCR status, and rejection remediation.
---

# SMS 10DLC Registration

Use this skill for US A2P SMS over 10-digit long codes. Keep three shapes apart; they have different field names and use-case values:

| Shape | Used for | Field names | 2FA use case | `MIXED` / `LOW_VOLUME` |
| --- | --- | --- | --- | --- |
| Evidence packet | Internal readiness review | snake_case, versioned | `TWO_FA` | allowed |
| MCP `compliance` map | The setup plan from `sent-compliance` | snake_case | `2FA` | refused; volume decides |
| REST campaign request | `/v3/profiles/{profileId}/campaigns` | camelCase in a `campaign` wrapper | `TWO_FA` | allowed |

For current field and document requirements or an exact SMS setup call, use `sent-compliance` before preparing the registration evidence here. From Claude, its plan is completed by creating the Sender Profile in the Sent Dashboard; it does not manage campaigns on an existing profile.

## Current Sent resource model

There is no standalone brand CRUD path in the current v3 API.

- Create a dedicated brand inside `POST /v3/profiles` using `brand` and `inherit_tcr_brand: false`.
- List/create campaigns with `GET|POST /v3/profiles/{profileId}/campaigns`.
- Update/delete with `PUT|DELETE /v3/profiles/{profileId}/campaigns/{campaignId}`.

Reject guidance that reintroduces a free-standing brand path.

## Choose inheritance deliberately

| Brand | Campaign | Settings |
| --- | --- | --- |
| Inherit both | Organization brand and campaign | `inherit_tcr_brand: true`, `inherit_tcr_campaign: true` |
| Inherit brand, own campaign | Shared legal brand with tenant-specific traffic | brand true, campaign false |
| Own both | Dedicated tenant/business | both false and supply `brand` during profile creation |

Inherited campaigns are read-only. A profile cannot supply `brand` while brand inheritance is true.

## Evidence and requests

### Evidence readiness packet

The private packet uses the explicit internal version `sent-10dlc-evidence/v1` and snake_case evidence fields. It is not an API payload.

```bash
python scripts/validate_10dlc_packet.py evidence.json
```

Collect legal identity, public website/policy links, consent proof, message flow, opt-in/opt-out/help responses and keywords, use cases, and realistic samples. See [references/10dlc-evidence-checklist.md](references/10dlc-evidence-checklist.md).

### MCP compliance map

From Claude, the registration is submitted in the Sent Dashboard. Prepare the user's answers with exactly the keys, `options`, and limits `compliance.requirements` publishes for US `TEN_DLC`; never use REST field names or values for them. Each key's notes name the TCR field it fills. For use cases, `TWO_FA` is published as `2FA`, and `MIXED` and `LOW_VOLUME` are refused because Sent derives them from `volume`, so list each kind of traffic as its own entry. No local validator checks this shape.

### REST campaign request

The REST request uses exact camelCase and a `campaign` wrapper:

<!-- sent-campaign-request -->
```json
{
  "campaign": {
    "name": "Acme account notifications",
    "description": "Account and delivery notifications for opted-in customers.",
    "type": "App",
    "useCases": [
      {
        "messagingUseCaseUs": "ACCOUNT_NOTIFICATION",
        "sampleMessages": [
          "Acme Example: Your account preference was updated. Reply STOP to opt out."
        ]
      }
    ],
    "volume": "2000",
    "messageFlow": "Customers opt in in account settings before notifications begin.",
    "privacyPolicyLink": "https://example.com/privacy",
    "termsAndConditionsLink": "https://example.com/terms",
    "optinMessage": "Acme Example: You are subscribed. Reply STOP to opt out.",
    "optoutMessage": "Acme Example: You are unsubscribed and will receive no more messages.",
    "helpMessage": "Acme Example: Visit https://example.com/support for help.",
    "optinKeywords": "START,YES",
    "optoutKeywords": "STOP,UNSUBSCRIBE",
    "helpKeywords": "HELP,INFO"
  },
  "sandbox": true
}
```

Validate it with:

```bash
python scripts/validate_campaign_payload.py campaign.json
```

## REST API use cases

The REST campaign request supports all 13 current values:

`MARKETING`, `ACCOUNT_NOTIFICATION`, `CUSTOMER_CARE`, `FRAUD_ALERT`, `TWO_FA`, `DELIVERY_NOTIFICATION`, `SECURITY_ALERT`, `M2M`, `MIXED`, `HIGHER_EDUCATION`, `POLLING_VOTING`, `PUBLIC_SERVICE_ANNOUNCEMENT`, and `LOW_VOLUME`.

Each use case structurally accepts 1–5 samples, each no longer than 1,024 characters. The compliance layer requires at least two samples for marketing and mixed traffic, including low-volume mixed. Keep that policy distinction visible instead of pretending OpenAPI requires two for all traffic.

## Volume and status

`volume` is optional and, when supplied, is a numeric string. Values below `"2000"` use the documented low-volume tier; `"2000"` is the boundary to the next tier.

Campaign responses currently expose statuses `SENT_CREATED`, `ACTIVE`, and `EXPIRED`, plus `submittedToTCR`. Preserve unknown future status strings. Do not confuse a successful Sent record creation with TCR submission or carrier activation.

## Safe workflow

1. Confirm this is US A2P 10DLC traffic and the actual sending business is identified.
2. Validate the versioned evidence packet.
3. From Claude, prepare the answers `compliance.requirements` asks for from the evidence and hand the user to the Sent Dashboard to submit them. Do not prepare or confirm a create.
4. Through REST:
   1. Select brand/campaign inheritance.
   2. Create or confirm the profile brand.
   3. Translate evidence into the exact camelCase campaign request.
   4. Validate locally and use `sandbox: true`.
   5. Show the payload and obtain confirmation before a real create/update/delete.
   6. Store profile ID, campaign ID, `submittedToTCR`, raw status, and review evidence.
   7. Complete the profile with required `webHookUrl` only after prerequisites are ready.

Never use real consumer data in fixtures or samples. Use [references/tcr-use-cases.md](references/tcr-use-cases.md) for classification and [references/10dlc-rejection-remediation.md](references/10dlc-rejection-remediation.md) for failures.
