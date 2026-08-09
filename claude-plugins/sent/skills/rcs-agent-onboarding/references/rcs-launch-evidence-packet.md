# RCS launch evidence packet

## Brand

- Legal and consumer-facing brand names
- Public website
- Square logo and brand color
- Privacy policy and terms URLs
- Support email, phone, or URL

## Use case and consent

- Audience and target countries
- Transactional, authentication, marketing, support, or mixed intent
- Exact opt-in flow and proof
- Message frequency and estimated volume
- STOP/HELP handling where SMS can be selected by automatic routing

## Current message examples

Provide at least five representative text messages. For each, include zero-to-four suggestion chips and what each chip does. Do not include rich-card, carousel, or media-attachment requirements; those are not current Sent capabilities.

## Sender Profile

- v3 profile UUID
- Credential pattern: profile key or organization key plus `x-profile-id`
- Relevant numbers and markets
- SMS compliance state if automatic routing can select SMS

## Routing plan

Choose one or more test modes:

- automatic routing: omitted `channel` or `["sent"]`;
- pinned RCS: `["rcs"]`;
- intentional broadcast: multiple explicit channels with expected message count and cost.

Do not describe an explicit multi-channel array as fallback.

## Handoff note

Ask Sent to initiate RCS setup and carrier review for the named profile. Attach brand/consent evidence, message examples, target markets, support details, routing plan, and requested launch window. Avoid claims about approval timing that Sent or carriers have not confirmed.
