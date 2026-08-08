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

Generated changes under `plugins/sent`, `claude-plugins/sent`, `.agents`, and `.claude-plugin` should be committed with their source changes.
