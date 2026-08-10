# Consent, keywords, and suppression on Sent

## Table of contents

- [Default keyword set](#default-keyword-set)
- [Matching rules](#matching-rules)
- [Custom keywords](#custom-keywords)
- [Consent state and scope](#consent-state-and-scope)
- [How suppression surfaces on send](#how-suppression-surfaces-on-send)
- [Restoring consent](#restoring-consent)
- [Channel-specific consent mechanics](#channel-specific-consent-mechanics)
- [Application responsibilities](#application-responsibilities)
- [Audit expectations](#audit-expectations)

## Default keyword set

Ten keywords are seeded by default.

| Action | Keywords | Effect |
| --- | --- | --- |
| Opt out | `STOP`, `CANCEL`, `UNSUBSCRIBE`, `QUIT`, `END` | Sets `opt_out` on the contact |
| Opt in | `START`, `UNSTOP`, `SUBSCRIBE` | Clears suppression |
| Help | `HELP`, `INFO` | Triggers the help auto-reply |

Only these ten are documented defaults. Terms that appear in other platforms' keyword lists should not be presented as Sent defaults; if a specific extra term is required, add it as a custom keyword and verify it in the dashboard.

## Matching rules

Matching runs against the seeded defaults plus any custom keywords, on every inbound message received on a two-way capable channel. The rules are strict:

- the **entire trimmed body** must equal the keyword;
- comparison is case-insensitive;
- partial phrases and keywords embedded in a sentence never match.

So `stop`, `STOP`, and ` Stop ` all opt the contact out, while `please stop texting me` does not. This is deliberate: loose matching would opt out customers who used the word incidentally. It also means a real-world opt-out intent expressed in a sentence will not be caught automatically, which is a reason to route inbound text to a human queue rather than assuming keyword coverage is complete.

Mirror this exact matcher in the application when local subscriber state or audit evidence is required. The platform has already applied consent by the time the event arrives, so the local matcher must never issue a second consent write. Keep configured custom keywords synchronized and reconcile uncertain state from the contact's `opt_out` field.

## Custom keywords

Custom keywords are configured in the Sent Dashboard under Compliance, then Opt Keywords. Each entry names a single exact token and one action: Opt Out, Opt In, or Help. There is no REST or MCP surface for keyword management, so keyword changes are a dashboard operation that cannot be scripted; treat the configured set as an environment fact to be read, documented, and version-controlled in the application's own runbook.

When designing custom keywords, prefer short single tokens in the languages the audience actually writes in, and avoid tokens that collide with normal replies such as `YES` or `NO` if those are used for other flows.

## Consent state and scope

An opt-out flips `opt_out` on the contact record. Two properties of that state are load-bearing:

**Contact-level.** Consent attaches to the contact, not to a campaign, template, or sending number. There is no per-template or per-campaign suppression list.

**Channel-agnostic.** A keyword received on any channel suppresses every channel. A customer who texts `STOP` over SMS will not receive WhatsApp or RCS messages either. Applications that model consent per channel will over-send relative to the platform and see the difference as filtered messages.

Consent gates re-apply on **every** reroute attempt, not only at the initial send. A message that passed the gate at send time is still re-checked when automatic routing retries it on another route.

## How suppression surfaces on send

A send to a suppressed contact is not rejected with a `4xx`. The request is accepted, and the affected message finalizes as `FILTERED` with a terminal channel value of `auto` when the block occurred before routing. Consequences:

- Consent problems appear in delivery data rather than in API error handling, so a client that only inspects HTTP status codes will not notice them.
- `FILTERED` must never be retried. Retrying a consent block is a compliance violation, and it cannot succeed.
- Consent-driven filtering should be monitored as its own metric. A rising filtered rate usually means a stale local suppression list rather than a delivery problem.

## Restoring consent

Consent restoration is the recipient's decision. The clean path is a user-initiated opt-in keyword, which clears suppression through the same engine that set it.

`PATCH /v3/contacts/{id}` accepts `opt_out` as a writable field, so it is technically possible to clear the flag from the API. Treat that as a compliance action rather than a data fix:

1. Require documented evidence of fresh consent — a form submission, a recorded confirmation, or a written request.
2. Record who authorized the change, when, and against which evidence.
3. Never bulk-clear `opt_out` across a contact list, and never clear it to "fix" a filtered-message metric.
4. Prefer asking the customer to text an opt-in keyword, which produces platform-side evidence.

An agent asked to clear `opt_out` should surface the compliance implication and require explicit confirmation naming the consent evidence before proceeding.

## Channel-specific consent mechanics

| Channel | Inbound keyword path | Notes |
| --- | --- | --- |
| SMS | Requires an MO-capable provider and a supported number type | Alphanumeric sender IDs and SMPP paths without an inbound route never deliver `STOP`; plan compliance around that limitation |
| RCS | Typed replies match keywords; the appended STOP chip bypasses matching | Every outbound RCS message carries a STOP chip whose tap is handled directly by the consent engine |
| WhatsApp | Full inbound support | Replies to STOP, START, or HELP outside the 24-hour window require an approved template |

The RCS STOP chip means an RCS deployment always exposes an opt-out affordance the application did not author, and its taps arrive as ordinary `message.received` events with the chip's reply text in `text`. There is no distinct event type for a chip tap.

## Application responsibilities

The platform owns enforcement; the application owns reflection and evidence.

- Mirror `opt_out` into local state by exact-matching the documented and configured keyword set, and reconcile from `GET /v3/contacts/{id}` when uncertain.
- Never use the local text match to re-apply consent to Sent; it is a mirror and audit mechanism only.
- Show suppression state in any internal UI where staff could otherwise trigger a send.
- Keep the local mirror reconciled on a schedule, since a keyword can arrive at any time and a stale mirror produces filtered messages.
- For US SMS, keep the campaign-level opt-in, opt-out, and help keyword declarations consistent with what is actually configured; carrier registration expects them to match.

## Audit expectations

Retain, per consent change: the inbound `message_id`, the received timestamp, the channel, the exact matched text, and the resulting state. Inbound keyword events are the strongest evidence available that a customer opted out or back in, and they are the artifact a carrier or regulator will ask for. Because Sent applies consent before the event is delivered, the event is a record of a completed action, and treating it as a request to perform an action risks double-processing.
