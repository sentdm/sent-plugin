---
name: sent-compliance
description: Retrieves live SMS sender compliance requirements and a setup plan by country and number type using Sent MCP tools. Use when a user asks what a market requires, which registration fields or documents to supply, whether an SMS sender can be provisioned here, or for the exact setup call. Use sms-10dlc-registration for US campaign content and policy, and separate WhatsApp or RCS onboarding skills for those channels.
---

# Sent Compliance

Use the read-only `compliance.requirements` and `compliance.setup_plan` tools before provisioning a dedicated SMS sender. They describe a market; they do not register a sender or mutate a profile.

## Resolve the market

Use client-managed OAuth 2.1/PKCE and never request or expose credentials. Resolve `country` as an ISO 3166-1 alpha-2 code and `type` as `LOCAL`, `MOBILE`, `TEN_DLC` (or `10DLC`), `TOLL_FREE`, `SHORT_CODE`, or `ALPHANUMERIC`. `channel` defaults to `sms`; only SMS is supported. Route WhatsApp to `waba-embedded-signup` and RCS to `rcs-agent-onboarding` rather than interpreting refusal as no requirements.

The optional `profileId` selector is available only for an organization's owned profile. Requirements are account-independent; it does not change the market's rules or make the plan target an existing profile.

## Interpret requirements and plan

1. Call `compliance.requirements` for the selected market. Preserve required flags, conditional rules, options, item fields, sender pattern, and attachment field names.
2. Check `hasRegime` before interpreting an empty requirements list. An empty list with a published regime can mean no fields are demanded; `hasRegime: false` means no schema is published and is not proof that no compliance is required. US `TOLL_FREE` numbers require toll-free verification before production traffic, even when no requirements are returned; never tell the user that a toll-free number needs no registration.
3. Call `compliance.setup_plan` when the user needs the setup steps for a market. From Claude, Sender Profiles are provisioned in the Sent Dashboard: present the plan's requirements, and when it returns a Dashboard handoff, give the user that link. If the plan contains a `call` that would create a Sender Profile, do not call `sender_profiles.create`; hand the setup to the Dashboard. Do not translate the plan into an invented REST call.
4. If `canCompleteHere` is false, report `blocker` and `attachments`, then hand off document submission to the Sent dashboard or the documented multipart REST workflow. Required uploads cannot be carried through MCP. Optional attachment fields alone do not necessarily block creation.
5. When setup can proceed, direct the user to finish provisioning in the Sent Dashboard with the requirements you gathered.

The plan describes a new profile, which the user creates in the Sent Dashboard. Adding a market to an existing profile requires the dashboard or REST API. It does not establish approval, readiness, consent, or permission to send.

For US 10DLC campaign policy, samples, and opt-in evidence, use `sms-10dlc-registration` after resolving the live market requirements.
