# 10DLC rejection remediation

## Diagnose the layer

| Layer | Evidence |
| --- | --- |
| Local evidence packet | Version, missing consent proof, invalid URLs, incomplete autoresponses |
| Sent REST request validation | Wrong camelCase, unsupported field, invalid use case, sample count/length, volume type |
| Sent MCP `compliance` map | A key, option, or limit `compliance.requirements` does not publish, such as a REST field name, `TWO_FA`, `MIXED`, or `LOW_VOLUME` |
| TCR submission | `submittedToTCR`, registry error/reason, brand or campaign status |
| Carrier operations | Campaign active but filtering, DCA election, content mismatch |

Do not create a new campaign until the failing layer is known.

## Common fixes

- Wrong endpoint model (REST): operate campaigns under the profile and create a dedicated brand within profile creation.
- Inheritance conflict (REST): disable `inherit_tcr_campaign` before managing a dedicated campaign; do not supply `brand` while brand inheritance is true.
- Wrong field casing (REST): serialize `useCases`, `messagingUseCaseUs`, and `sampleMessages` exactly. The MCP map takes the keys and options `compliance.requirements` publishes instead.
- Too few samples: provide 1–5 structurally; provide at least two for marketing/mixed compliance.
- Weak opt-in: add observable proof and a complete message flow.
- Autoresponse failure: add brand, STOP/HELP, unsubscribe confirmation, and support details as applicable.
- Traffic mismatch: select a use case that matches actual content rather than rewriting only the example.

## Status interpretation

`SENT_CREATED` means a Sent campaign record exists. `submittedToTCR: true` records registry submission. `ACTIVE` means operational activation, while `EXPIRED` is not send-ready. Preserve unknown status strings and any `tcrSyncError` rather than replacing them with a guessed category.

## Resubmission

1. Save the original response and reason.
2. Fix the versioned evidence packet if necessary.
3. Through REST, rebuild and validate the API request and use `sandbox: true`. Through MCP, re-read `compliance.requirements` and correct the `compliance` map; MCP has no sandbox.
4. Show the exact diff.
5. Obtain confirmation before the real mutation.
