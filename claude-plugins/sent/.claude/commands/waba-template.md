---
description: Author a WhatsApp Business API template and classify it as utility, marketing, or authentication per Meta's policy
---

Invoke the `waba-template-author` skill.

Begin by asking the user:
1. The use case in one sentence ("After a customer pays, confirm the order…")
2. The recipient's relationship to the event (did they trigger it, or is the business reaching out cold?)
3. Whether this is a code / OTP (authentication template) or a regular template
4. The target language (BCP-47 code, e.g. `en_US`, `pt_BR`)

Then walk the decision tree, draft the components, and produce a submission-ready Cloud API payload. Flag any wording or imagery that's likely to flip the category at Meta's review.
