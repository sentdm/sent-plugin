# Contributing

Contributions must be suitable for a public repository and safe to distribute as an agent plugin.

## Public-data policy

Never commit:

- credentials, tokens, authorization headers, private keys, or local environment files;
- real customer, contact, message, KYC, billing, or account data;
- private repository links, internal-system names, unpublished operational procedures, or non-public roadmap details;
- local filesystem paths, private network addresses, or production-only diagnostic output;
- generated archives or operating-system metadata.

Use synthetic fixtures with reserved `example.com` addresses and fictional or reserved phone numbers. If a change is based on non-public material, rewrite it against public documentation and remove source-specific identifiers before opening a pull request.

## Development workflow

Edit the canonical files in `packages/sent` or `adapter-sources`, then run:

```bash
python3 scripts/generate_adapters.py
python3 scripts/validate.py
python3 scripts/test_validation_gates.py
python3 scripts/test_fixtures.py
claude plugin validate . --strict
claude plugin validate ./claude-plugins/sent --strict
```

Generated changes in root-level `plugin.json`, `mcp.json`, `skills/`, and `assets/`, plus `plugins/sent`, `claude-plugins/sent`, `.agents`, and `.claude-plugin`, should be committed with their source changes.

## Adding or changing a skill

Treat `packages/sent/skills/<skill-name>/` as the source of truth.

1. Keep `SKILL.md` frontmatter limited to `name` and `description`. Write the description for discovery: state what the skill does and include the user intents, product terms, error symptoms, and boundaries that should trigger it.
2. Keep the core workflow concise. Put detailed specifications, examples, and decision tables in skill-local `references/`; put repeated deterministic checks in `scripts/` and test those scripts with synthetic fixtures.
3. Add or update `agents/openai.yaml` when the skill has OpenAI UI metadata, and keep its display name, short description, and default prompt aligned with `SKILL.md`.
4. Add positive, negative, and relevant overlap cases in `evals/<skill-name>.yaml`.
5. Add the skill to the `sent` dispatcher and to the catalogs in the root README, `packages/sent/README.md`, and `adapter-sources/shared/README.md`.
6. Regenerate every adapter and run the complete validation suite above. Do not edit generated skill copies directly.

The repository validator enforces the expected skill set, frontmatter shape, routing coverage, README catalog coverage, local reference integrity, MCP safety contract, generated parity, and public-data policy.
