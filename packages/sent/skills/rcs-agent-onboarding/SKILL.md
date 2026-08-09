---
name: rcs-agent-onboarding
description: Guides current Sent RCS and RBM onboarding, launch evidence, carrier approval, text and suggestion-chip templates, Sender Profile readiness, and safe routing. Use for RCS launch, fallback, pinned-channel tests, or broadcast prevention.
---

# RCS Agent Onboarding

Sent RCS setup is not self-service. Sent and carrier approval are required. Prepare a complete launch packet, hand it to Sent, and verify the resulting Sender Profile with controlled messages.

## Current capability boundary

Current Sent RCS supports:

- text content; and
- up to four suggestion chips.

Rich cards, carousels, and media attachments are roadmap features, not current Sent workflows. Do not request them as launch requirements, expose them as current template-builder controls, or declare them as active agent capabilities.

## Routing semantics

Channel selection on `POST /v3/messages` is not an ordered fallback list.

| Request | Behavior |
| --- | --- |
| Omit `channel` | Automatic Sent routing with fallback. |
| `channel: ["sent"]` | Explicit automatic Sent routing with fallback. |
| `channel: ["rcs"]` | Pinned RCS only; no cross-channel fallback. |
| Two or more explicit channel values | Broadcast: one separately created and billable message per recipient/channel pair. |

Never put RCS and SMS together in an explicit array to describe fallback. Use omitted `channel` or `["sent"]` for automatic routing. Use explicit arrays only when broadcast is intended and confirmed.

## Onboarding workflow

### 1. Define the launch use case

Collect brand, audience, countries, consent source, message purpose, support path, estimated volume, and whether automatic fallback is required. Keep examples synthetic and within current text/chip capabilities.

### 2. Verify Sender Profile readiness

Record the v3 profile UUID. Do not use legacy `x-sender-id` as v3 authentication. Choose a profile-specific API key or an organization API key with `x-profile-id`; only organization keys may use that header.

If automatic routing may select US SMS, complete the appropriate 10DLC/compliance work first. An approved RCS agent does not make an SMS route compliant.

### 3. Prepare the evidence packet

Use [references/rcs-launch-evidence-packet.md](references/rcs-launch-evidence-packet.md). Include:

- consumer-facing brand name and website;
- logo and brand color;
- privacy policy and terms;
- support contacts;
- clear use case and consent flow;
- representative text messages;
- zero-to-four suggestion chips per message;
- target markets and requested timeline;
- automatic-routing or pinned-RCS test intent.

### 4. Hand off to Sent

Because setup is not self-service, request Sent initiation and carrier approval. Do not fabricate RBM console clicks, public provisioning endpoints, capability declaration APIs, or carrier-approval status endpoints.

### 5. Build current templates

Use Sent's template `definition` contract. RCS may have a complete `definition.body.rcs` override. Keep the RCS override text-based and limit suggestions to four. The `multiChannel` body remains required for template portability; routing fallback is still chosen at send time.

### 6. Test deliberately

- Validate templates and messages in sandbox where supported.
- Pin `["rcs"]` to prove the RCS path without cross-channel fallback.
- Omit `channel` or use `["sent"]` to verify automatic routing.
- If testing broadcast, state the expected recipient × channel message count and cost before sending.
- Persist every returned `message_id` with tenant, profile, channel, and logical test case.

Use `GET /v3/messages/{id}`, activities, and signed webhooks to verify actual routing and delivery. Do not infer fallback from the request alone.

## Launch acceptance

- [ ] Sent and carrier approval are confirmed.
- [ ] Profile UUID and credential pattern are recorded.
- [ ] Brand, consent, policy, and support evidence is complete.
- [ ] Templates use only text and up to four suggestion chips for RCS.
- [ ] Automatic fallback uses omitted `channel` or `["sent"]`.
- [ ] Pinned RCS uses `["rcs"]`.
- [ ] Broadcast is clearly labelled and costed.
- [ ] SMS compliance is ready wherever automatic routing can select SMS.
- [ ] Message IDs are mapped for webhook attribution.

Use [references/rbm-agent-spec.md](references/rbm-agent-spec.md) for the current launch specification and [references/rcs-fallback-patterns.md](references/rcs-fallback-patterns.md) for routing tests. Use `messaging-performance-analyzer` after enough message evidence exists.
