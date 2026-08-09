# Sender Profile data model

## Core records

```text
organization
  id
  organization_key_secret_ref

tenant
  id
  organization_id
  sent_profile_id
  profile_key_secret_ref
  credential_pattern
  billing_model

profile_policy
  profile_id
  allow_contact_sharing
  allow_template_sharing
  inherit_contacts
  inherit_templates
  inherit_tcr_brand
  inherit_tcr_campaign

channel_binding
  profile_id
  channel
  direct_number
  source_profile_id
  waba_id

message_attribution
  message_id
  logical_send_id
  tenant_id
  profile_id
  channel

inbound_route
  channel
  destination_number
  tenant_id
  profile_id
```

`source_profile_id` models `sending_phone_number_profile_id` and `sending_whatsapp_number_profile_id`. Enforce referential integrity and prevent cycles.

## Profile request fields

Create supports identity, sharing/inheritance, billing, dedicated WABA credentials, and a profile-owned `brand`. Update additionally supports number reference/direct-number fields and onboarding number-change policy.

Brand request fields are grouped into:

- `contact`: representative and business-facing contact data;
- `business`: legal identity, tax/entity type, address, country, URL;
- `compliance`: vertical, brand relationship, primary use case, TCR flag, number prefix, destination countries, notes.

Treat request camelCase inside `brand` separately from snake_case response fields. Do not round-trip by blindly serializing a response object as a create request.

## Authentication invariant

```text
profile key       -> x-api-key only
organization key  -> x-api-key + optional x-profile-id
```

Only the organization pattern may include `x-profile-id`. Rate limits for organization-scoped requests remain in the organization pool.

## Campaign ownership

Campaigns belong to the brand selected through a profile but are operated through profile paths:

```text
/v3/profiles/{profileId}/campaigns
/v3/profiles/{profileId}/campaigns/{campaignId}
```

An inherited brand can have profile-owned campaigns when campaign inheritance is disabled.

## Status storage

Store at least:

```text
profile_id
status_raw
status_surface       # create_response, rest_profile, completion_200, completion_callback
observed_at
payload_version
```

Known examples vary in case and vocabulary. Do not normalize unknown values into a closed enum.

## Secret boundaries

WABA `access_token` and payment card fields are write-only operational secrets. Never log, echo, or persist raw values in profile records. Keep only secret-manager references and non-sensitive identifiers such as `waba_id`.
