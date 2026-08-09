# Public release checklist

Use this checklist for every public release.

## Repository and package

- Confirm the GitHub repository is public and the release commit is on the default branch.
- Confirm the repository root contains `plugin.json`, `mcp.json`, `public-surface.json`, `skills/`, and `assets/` for GitHub auto-discovery.
- Confirm `.claude-plugin/marketplace.json` points to `./claude-plugins/sent`.
- Confirm the Claude plugin contains its manifest, README, license, skills, commands, assets, and HTTPS MCP configuration.
- Update the version consistently before release; plugin names are stable public identifiers and must not be renamed casually.
- Review `git ls-files` for local metadata, archives, credentials, customer data, and private operational material.

## Automated gates

```bash
python3 scripts/generate_adapters.py --check
python3 scripts/validate.py
python3 scripts/test_validation_gates.py
python3 scripts/test_fixtures.py
python3 scripts/test_contracts.py
python3 scripts/test_live_contract.py
claude plugin validate . --strict
claude plugin validate ./claude-plugins/sent --strict
```

CI must pass on the exact commit being submitted. Resolve warnings as well as errors before submission. The dedicated contract/documentation freshness workflow runs on schedule, manual dispatch, and release; review its uploaded JSON artifact separately from pull-request validation.

## Public-facing review

- Verify the homepage, documentation, privacy, terms, support, and MCP URLs are publicly reachable over HTTPS.
- Confirm the README accurately describes installation, authentication, data handling, mutation confirmation, and support.
- Confirm every public skill appears in each README catalog with a task-oriented description and a working `skills/<name>/SKILL.md` link.
- Run `npx skills add https://github.com/sentdm/sent-plugin --list` against the public release and confirm all thirteen skills are discoverable by name.
- Review every `SKILL.md` frontmatter description for natural-language triggers, product synonyms, error symptoms, and explicit scope boundaries.
- Confirm all fixtures are synthetic and all external documentation links are public.
- Confirm license and provenance notices remain present in the repository and distributable plugin.
- Complete security, privacy, legal, and product review without publishing reviewer accounts, credentials, or internal findings.

## Anthropic submission

Submit the public repository through the current Claude plugin submission form only after the exact public commit passes the gates above. Anthropic runs `claude plugin validate` and automated safety screening during review, so local strict validation should match the submitted layout.
