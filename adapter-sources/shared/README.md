# Sent Agent Plugin

This generated plugin adapter provides thirteen Sent skills and a remote MCP connection for messaging, contacts, templates, analytics, account readiness, SMS, WhatsApp, and RCS workflows.

The plugin connects only to `https://mcp.sent.dm/mcp`. Authentication is handled by the MCP client through OAuth 2.1 with PKCE; no credentials or credential placeholders are included. Mutating workflows preview the exact action and require explicit confirmation immediately before execution.

For installation, source, documentation, and security reporting, visit [github.com/sentdm/sent-plugin](https://github.com/sentdm/sent-plugin).

This directory is generated. Make source changes in `packages/sent` or `adapter-sources` and run `scripts/generate_adapters.py`.
