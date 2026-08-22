# Repository context manifest schema

`kb-bootstrap manifest` generates a deterministic JSON description of repository
identity needed for routing and preflight. It intentionally excludes local paths,
remote URLs, credentials, branches other than the default branch, Git objects,
Issues, pull requests, and runtime state.

## Generate

```bash
kb-bootstrap manifest \
  --repo example/consumer-project \
  --output repository-context.json
```

Generation fails without writing the file when Git root, GitHub identity, default
branch, or matching `origin` identity cannot be verified.

## Validate

```bash
kb-bootstrap manifest \
  --output repository-context.json \
  --check
```

Validation is local and deterministic; it does not call Git or GitHub.

## Schema version 1

```json
{
  "default_branch": "main",
  "remotes": {
    "origin": {
      "repository": "example/consumer-project"
    },
    "upstream": {
      "repository": "ozand/kb-bootstrap"
    }
  },
  "repository": "example/consumer-project",
  "schema_version": 1
}
```

Required rules:

- root keys are exactly `schema_version`, `repository`, `default_branch`, and
  `remotes`;
- `schema_version` is `1`;
- repository identities use `owner/repository` format;
- `origin` is required and must match `repository`;
- `upstream` is optional;
- remote entries contain only the sanitized `repository` identity;
- `default_branch` is a non-empty string.

The manifest never contains token-bearing URLs, credentials, filesystem paths,
commit/object listings, local runtime checkpoints, `.pi/` data, or arbitrary Git
configuration.
