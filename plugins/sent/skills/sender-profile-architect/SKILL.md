---
name: sender-profile-architect
description: Designs Sent Sender Profile architecture for multi-tenant, multi-brand, and multi-channel systems. Use for API-key scoping, x-profile-id, isolation, inheritance, sharing, billing, WABA, 10DLC campaigns, webhooks, or tenant offboarding.
---

# Sender Profile Architect

A Sender Profile is the operational boundary for tenant identity, channel configuration, inherited resources, billing, and credentials. Use this skill before provisioning when a poor boundary would mix brands, compliance posture, rate-limit impact, or webhook ownership.

## Recommended tenancy model

When tenants require isolation, recommend one Sent organization with one Sender Profile per tenant. A shared profile is appropriate only when the tenants genuinely share one brand, sender resources, compliance posture, billing/rate-limit expectations, and operational blast radius.

Do not recommend pooled-by-default architecture. Make the isolation decision explicit using [references/multi-tenancy-patterns.md](references/multi-tenancy-patterns.md).

## Authentication patterns

Sent v3 supports both:

| Pattern | Headers | Blast radius |
| --- | --- | --- |
| Profile-specific API key | `x-api-key` | Profile-scoped credentials and rate-limit context. Do not add `x-profile-id`. |
| Organization API key acting for a child | `x-api-key` plus `x-profile-id: <profile UUID>` | Organization credential can reach permitted child profiles; rate limits remain in the organization pool. |

Only organization keys may send `x-profile-id`. A profile key that sends it receives `403`. A profile outside the organization returns `404`. `X-Profile-Id` can be echoed in scoped responses.

`x-sender-id` is legacy v1/v2 terminology only. Do not use it for v3 authentication or routing.

Choose profile keys when tenant-level credential isolation and revocation are primary. Choose organization-key scoping for centrally controlled integrations that can protect a broader credential and deliberately accept a shared organization rate-limit pool.

## Profile creation model

Create with `POST /v3/profiles`. `name` is required. Current optional areas include:

- identity: `icon`, `description`, `short_name`;
- sharing: `allow_contact_sharing`, `allow_template_sharing`;
- inheritance: `inherit_contacts`, `inherit_templates`, `inherit_tcr_brand`, `inherit_tcr_campaign`;
- billing: `billing_model`, `billing_contact`, and ephemeral `payment_details`;
- dedicated WABA credentials: `whatsapp_business_account` with `waba_id`, optional `phone_number_id`, and `access_token`;
- a dedicated brand: `brand.contact`, `brand.business`, and `brand.compliance`.

Do not add a separate brand endpoint. A dedicated brand is created with the profile; campaigns are managed under `/v3/profiles/{profileId}/campaigns`.

### Inheritance rules

- `inherit_tcr_brand: true` means the profile uses the organization's brand and cannot submit its own `brand` object.
- `inherit_tcr_campaign: true` makes inherited campaigns read-only for that profile.
- An inherited brand with `inherit_tcr_campaign: false` is a supported dedicated-campaign pattern.
- Sharing flags expose a profile's contacts/templates; inheritance flags consume organization resources. Treat those directions separately.

### Billing and number references

`billing_model` currently supports `profile`, `organization`, and `profile_and_organization`. A profile or fallback billing model requires `billing_contact` when none exists. Card fields are forwarded to the payment processor and must not be logged or persisted.

Profile update can manage `sending_phone_number_profile_id`, `sending_whatsapp_number_profile_id`, `sending_phone_number`, `whatsapp_phone_number`, and `allow_number_change_during_onboarding`. Model reference IDs and direct numbers separately, and prevent cycles when one profile references another.

## WABA choices

There are three distinct paths:

1. Organization Embedded Signup in the dashboard.
2. Child profile inheritance by omitting `whatsapp_business_account` after the organization has a WABA.
3. Dedicated profile WABA using `waba_id` and `access_token`; `phone_number_id` is optional.

There is no public endpoint that starts organization Embedded Signup. Direct credentials on `POST /v3/profiles` are not an “Embedded Signup endpoint.” Use `waba-embedded-signup` for the operational flow.

## 10DLC and campaigns

Use a profile `brand` object for a dedicated brand. Manage campaigns at:

- `GET|POST /v3/profiles/{profileId}/campaigns`
- `PUT|DELETE /v3/profiles/{profileId}/campaigns/{campaignId}`

Use `sms-10dlc-registration` for the payload and policy layer.

## Completion and status handling

Complete a profile with `POST /v3/profiles/{profileId}/complete` and a required `webHookUrl`:

```json
{
  "webHookUrl": "https://example.com/webhooks/profile-complete",
  "sandbox": true
}
```

Status is surface-specific:

- Create response currently demonstrates lowercase `incomplete`.
- Completion `202` means processing started and does not contain a final status.
- Completion `200` currently demonstrates lowercase `completed` for an already-complete profile.
- Completion callbacks can report `COMPLETED`, `SUBMITTED`, or `failed`.
- REST guides and OpenAPI publish different profile status sets.

Do not assert a closed REST enum. Preserve unknown strings and record the endpoint/callback surface that produced them.

## Webhook attribution

Sent events do not contain your application tenant ID. Before sending, persist the returned `message_id` with the tenant and profile. Route outbound status events through that mapping. For inbound messages, map the receiving number/profile resource to the tenant.

```text
message_id -> tenant_id, profile_id, logical_send_id, channel
receiving_number -> tenant_id, profile_id
```

Do not infer tenant ownership from `account_id` alone. Multiple tenant profiles can belong to one organization.

## Design checklist

- [ ] Tenant/brand isolation decision is explicit.
- [ ] Credential pattern and rate-limit/blast radius are documented.
- [ ] Sharing and inheritance directions are intentional.
- [ ] Billing ownership is named.
- [ ] Number references cannot form cycles.
- [ ] WABA path is organization signup, inheritance, or dedicated credentials—not an invented hybrid.
- [ ] Dedicated brand/campaign paths are profile-based.
- [ ] `message_id` and inbound-number mappings support webhook attribution.
- [ ] Unknown profile statuses are tolerated.
- [ ] Tenant offboarding revokes credentials, disables sends, detaches resources safely, and retains audit evidence.

See [references/sender-profile-data-model.md](references/sender-profile-data-model.md) and [references/profile-boundary-examples.md](references/profile-boundary-examples.md) for implementation patterns.
