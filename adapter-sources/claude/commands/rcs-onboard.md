---
description: Create + verify an RCS Business Messaging (RBM) agent for sending RCS via Sent, including capability + fallback decisions
---

Invoke the `rcs-agent-onboarding` skill.

Begin by asking:
1. Is this a fresh agent creation, or are you debugging a stuck verification / launch review?
2. The tenant's public brand identity (display name, logo, brand color) and verified domains
3. The use case (transactional, OTP, customer care, promotional, multi-use)
4. Which capabilities will the agent actually use (suggested replies, suggested actions, rich cards, carousel, attachments)?
5. The SMS fallback policy when a recipient isn't RCS-capable (`sms` via the same Sender Profile, `none`, or application-routed)

Then walk the agent identity setup, capability declaration, verification + launch-review path, and per-carrier rollout expectations. Flag anything that mismatches the tenant's public brand or requires re-review.
