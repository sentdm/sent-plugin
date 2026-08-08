---
description: Design and implement the tenant-facing UI for submitting WhatsApp templates to Sent
---

Invoke the `template-builder-ui` skill.

Begin by asking:
1. The frontend framework (React, Vue, Svelte, etc.) and existing design system
2. Whether the editor is a greenfield build or extending something
3. Which validation layers already exist on the backend (so the UI doesn't duplicate or conflict)
4. Realtime channel availability (WebSocket, SSE) for template-status updates

Then walk the editor anatomy (category first, then components, then live preview), produce component scaffolds, and surface the policy rules the UI must encode. Cross-reference `waba-template-author` for category rules.
