---
description: Register a brand + campaign with The Campaign Registry (TCR) for 10DLC A2P SMS on Sent
---

Invoke the `sms-10dlc-registration` skill.

Begin by asking:
1. Is this a fresh registration, or are you debugging a rejection / low vetting score?
2. The legal entity that's sending (parent company vs sub-brand) and its strongest external identifier (EIN, DUNS, GIIN, LEI)
3. The specific use case for this campaign — transactional notifications, 2FA, customer care, marketing, mixed?
4. Expected volume per day and which carriers (T-Mobile / AT&T / Verizon / all)?
5. The opt-in mechanism (how recipients agreed to receive these messages)

Then walk the Brand → Campaign sequence, pick the narrowest accurate TCR use case, produce sample messages that match production traffic and include opt-out language, and call out any attributes likely to trigger a downgrade.
