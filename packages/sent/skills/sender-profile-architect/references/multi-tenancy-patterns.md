# Multi-tenancy patterns

## Preferred: one profile per isolated tenant

Use one organization and one Sender Profile per tenant when tenants have distinct brands, consent evidence, 10DLC campaigns, WABAs, phone numbers, billing, credentials, or incident blast radius.

Benefits:

- profile-specific key issuance and revocation;
- explicit organization-key scoping through `x-profile-id`;
- separate inheritance and sharing choices;
- clean tenant offboarding;
- reliable number/profile and message/profile attribution.

Organization-key scoping does not create a separate rate-limit pool: the organization's pool remains shared.

## Shared profile

Use a shared profile only if all participants genuinely operate as one sender identity with one brand, resource set, compliance posture, billing/rate-limit expectations, and incident boundary. Lower object count is not sufficient justification.

A shared profile makes tenant credential isolation and webhook attribution application responsibilities. Document that tradeoff.

## Hybrid inheritance

Common supported patterns include:

| Brand | Campaign | Flags |
| --- | --- | --- |
| Organization brand | Organization campaign | `inherit_tcr_brand: true`, `inherit_tcr_campaign: true` |
| Organization brand | Dedicated profile campaign | `inherit_tcr_brand: true`, `inherit_tcr_campaign: false` |
| Dedicated profile brand | Dedicated profile campaign | both false, with `brand` at profile creation |

Do not set `brand` while `inherit_tcr_brand` is true. Inherited campaigns are read-only.

## Credentials

- A profile key uses only `x-api-key`.
- An organization key may add `x-profile-id` for a child.
- A profile key with `x-profile-id` receives `403`.
- `x-sender-id` is legacy v1/v2 terminology.

Store credentials in a secret manager. Never expose organization keys to tenant-controlled runtimes.

## Webhook fan-out

Outbound events carry `payload.message_id`, not your tenant ID. Persist:

```text
message_id -> tenant_id, profile_id, channel, logical_send_id
```

Inbound events carry destination number/channel information. Persist:

```text
channel + destination_number -> tenant_id, profile_id
```

Verify signatures before lookup, deduplicate events, and route unknown mappings to a quarantine queue. Never guess the tenant from organization `account_id`.

## Offboarding

1. Block new application sends.
2. Revoke profile keys; rotate organization credentials if exposure is possible.
3. Disable or reroute webhooks and number references.
4. Preserve message/profile mappings for retention and disputes.
5. Delete the profile only after resource ownership and compliance retention are resolved.
