# Profile boundary examples

## Marketplace with fifty merchants

Use one organization and one Sender Profile per merchant. Give independently operated merchant runtimes profile keys; keep an organization key only in the trusted control plane. Each merchant can inherit organization templates while owning a dedicated campaign under the inherited organization brand if policy permits.

## One enterprise brand with regional teams

A shared profile may be defensible when every team uses the same legal/consumer brand, consent posture, WABA/numbers, billing, and operations. If a region requires a distinct number, campaign, credential, or incident boundary, split it into its own profile.

## Dedicated WABA tenant

Create the profile with:

```json
{
  "name": "Acme Support",
  "whatsapp_business_account": {
    "waba_id": "123456789012345",
    "phone_number_id": "987654321098765",
    "access_token": "<secret supplied at runtime>"
  },
  "sandbox": true
}
```

`phone_number_id` is optional. The access token must be injected from a secure runtime, never included in logs, fixtures, support tickets, or responses.

## Organization WABA inheritance

After organization Embedded Signup is complete, omit `whatsapp_business_account` on the child profile. Omitting it without an organization WABA returns `422`. This is inheritance, not an API-started Embedded Signup flow.

## Dedicated 10DLC brand

Set `inherit_tcr_brand: false` and include `brand` with `POST /v3/profiles`. Create campaigns through `/v3/profiles/{profileId}/campaigns`. Do not create a free-standing brand resource.

## Shared SMS number reference

Use `sending_phone_number_profile_id` when a profile intentionally reuses another profile's SMS configuration. Record the source profile and prevent circular references. A direct `sending_phone_number` is a different mode and should not be conflated with the profile reference.

## Webhook routing

When the send response returns message IDs, write all of them before treating the operation as accepted:

```text
message A -> tenant 42, profile P42, channel sms
message B -> tenant 42, profile P42, channel whatsapp
```

Multiple explicit channels create multiple messages. Route each webhook by `message_id`; do not expect an application tenant ID in the event.
