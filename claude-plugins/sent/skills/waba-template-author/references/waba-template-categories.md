# WhatsApp template categories

Supporting policy reference for `waba-template-author`. The request contract comes from Sent; category review is ultimately performed by Meta for WhatsApp.

## Decision order

1. Identify why the recipient expects the message.
2. Identify the single action the message asks them to take.
3. Remove optional promotional language and classify again.
4. If promotion remains, use `MARKETING`.
5. If the sole purpose is a verification code, use `AUTHENTICATION`.
6. Otherwise use `UTILITY` only when the message is tied to a specific transaction, account, or service event.

## Category guide

| Category | Suitable intent | Common rejection or recategorization risk |
| --- | --- | --- |
| `UTILITY` | Order state, appointment reminder, account change, service interruption, requested support update | Discounts, upsells, product discovery, vague re-engagement, or calls to purchase |
| `MARKETING` | Offers, launches, recommendations, reminders to shop, abandoned-cart messages, mixed promotional content | Missing consent, misleading urgency, or attempting to disguise promotion as utility |
| `AUTHENTICATION` | OTP, login verification, account recovery code | Free-form content, promotional text, unrelated links/media, or multiple actions |

Transactional context does not make promotional content utility. “Your receipt is ready” is utility; “Your receipt is ready—buy again for 20% off” is marketing.

## Authentication restrictions

- Set top-level `category` to `AUTHENTICATION`.
- Include `definition.authenticationConfig`.
- `codeExpirationMinutes`, when present, is an integer from 1 through 90.
- Keep the body to the verification purpose and one code variable.
- Use the supported `COPY_CODE` action for the code.
- Do not add promotion, unrelated URLs, media, or extra calls to action.

## Variables and samples

Provider reviewers see samples. Every placeholder such as `{{0:variable}}` must have the same numeric ID in the channel's variables array and a realistic `props.sample`. Do not use real customer data or secrets in samples.

## Revision discipline

When Meta returns `REJECTED` or `CATEGORY_UPDATED`, retain the raw reason, change only what it supports, lint again, and resubmit deliberately. Do not repeatedly submit unchanged content.
