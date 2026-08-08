# Security policy

## Reporting a vulnerability

Do not open a public GitHub issue for a suspected vulnerability, credential exposure, privacy incident, or customer-data disclosure.

Report security concerns privately to `support@sent.dm` with the subject `Security report`. Include the affected component and version, reproduction steps, impact, and any suggested mitigation. Do not include live credentials, access tokens, private keys, or customer data; Sent support can arrange an appropriate channel if sensitive evidence is required.

## Authentication model

The plugin does not accept or store Sent credentials. A compatible MCP client performs OAuth 2.1 authorization with PKCE and stores the resulting grant. Users should revoke the grant through their MCP client or applicable Sent account controls when access is no longer needed.

## Supported versions

Security fixes are applied to the latest release. Reproduce reports against the latest published version when practical and include the exact version or commit in the report.
