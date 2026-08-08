---
description: Implement Meta's WhatsApp Embedded Signup flow end-to-end (or debug a stuck one)
---

Invoke the `waba-embedded-signup` skill.

Begin by asking:
1. Is this a fresh integration or debugging an existing one?
2. Tech Provider / Solution Partner status with Meta?
3. Existing Meta app state — products added (WhatsApp, FBL)? `config_id` created? Redirect URIs allowlisted?
4. If debugging, which step is stuck? (Dialog won't open, code exchange failing, webhooks not firing, etc.)

Then walk the prerequisite checklist, the launch + exchange + register + subscribe sequence, and persist the SPS state at each step. For debugging, jump to the "Common Stuck States" table and triage from there.
