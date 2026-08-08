---
description: Plan multi-tenant architecture around Sent's Sender Profile — data model, channel routing across SMS/WhatsApp/RCS, rate limits, lifecycle
---

Invoke the `sender-profile-architect` skill.

Begin by asking:
1. Which channels does the tenant need (SMS, WhatsApp, RCS, or a mix)?
2. Tenant scale — current and 12-month projection (10? 1,000? 100,000?)
3. Isolation requirements — any regulated tenants (PHI, government, data-residency)?
4. Existing stack — datastore, queue, cache, language/framework
5. The specific design question — data model, webhook routing, rate limits, or lifecycle?

Then walk the Sender Profile framing and produce a concrete model / sequence / state-machine sketch tailored to the answers. Recommend pooled by default; recommend silos only when the answers justify them. Reference the channel-specific onboarding skills (`sms-10dlc-registration`, `waba-embedded-signup`, `rcs-agent-onboarding`) for the parts that fall outside the architecture concern.
