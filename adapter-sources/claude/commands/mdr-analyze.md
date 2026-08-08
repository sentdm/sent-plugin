---
description: Analyze Sent Message Delivery Reports (MDRs) across SMS, WhatsApp, and RCS to find where a funnel is leaking
---

Invoke the `messaging-performance-analyzer` skill.

Begin by pinning the question. Ask:
1. Which channel is this about — SMS, WhatsApp, RCS, or a cross-channel comparison?
2. What's the specific concern? ("delivery dropped today", "this template underperforms in Brazil", "RCS not reaching T-Mobile recipients", "leads aren't replying")
3. The cohort: which template / campaign / agent, which country/countries, which tenant(s), which time window?
4. The data source: CSV/JSON dump, paste, log file path, or a database the user can query?

If the question is too vague to answer (e.g. "how are we doing"), narrow it before pulling data. Always require a defined cohort and a named channel. For RCS funnels, also ask whether SMS fallback is in play so the analysis can separate it.
