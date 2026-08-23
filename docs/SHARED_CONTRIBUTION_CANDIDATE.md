# Prepare a reviewed shared lesson contribution candidate

`kb-bootstrap prepare-shared-candidate` prepares one sanitized JSON artifact locally. It does not write to a shared lesson store, change Git branches, commit, push, or create a pull request.

## Required input

The input JSON must explicitly provide:

- target repository in `owner/repository` form;
- target branch;
- destination `workspace-global-lessons`;
- authenticated and repository-matched preflight evidence;
- human confirmation;
- workspace metadata compatible with the shared registry contract;
- source repository, verified `observed_in`, and `promoted_from` provenance;
- sanitized title, problem, resolution, and prevention text.

Example:

```json
{
  "target": {
    "repository": "example/shared-lessons",
    "branch": "contrib/project-0042",
    "destination": "workspace-global-lessons"
  },
  "preflight": {
    "authenticated": true,
    "repository_match": true,
    "human_confirmed": true
  },
  "metadata": {
    "scope": "workspace",
    "source_repository": "example/application",
    "observed_in": ["example/application"],
    "promoted_from": {
      "repository": "example/application",
      "lesson_id": "PROJECT-0042"
    }
  },
  "content": {
    "title": "Portable process startup failure",
    "problem": "A required executable is unavailable.",
    "resolution": "Validate the executable during preflight and fail closed.",
    "prevention": "Keep the dependency check deterministic and documented."
  }
}
```

## Preparation

```bash
kb-bootstrap prepare-shared-candidate \
  --input contribution-input.json \
  --output contribution-candidate.json
```

The command refuses to overwrite an existing output and requires its parent directory to exist; it does not create arbitrary directory trees. On success, it omits authentication details from the prepared artifact and creates a sanitized receipt containing only repository, branch, destination, verified preflight/human-confirmation status, and `prepared-for-review` outcome.

## Blocking behavior

Preparation blocks before creating output when:

- target repository, branch, or destination is missing or invalid;
- authentication is missing;
- repository preflight does not match the explicit target;
- human confirmation is missing;
- shared scope/provenance metadata is ambiguous;
- candidate content matches credential, token-bearing URL, local path, or runtime/session patterns;
- output already exists.

Blocked reports identify only the failed field/category and never echo candidate payloads.

## Review and authorized follow-up

A prepared artifact is not approval to publish. A human reviewer must inspect it and then use the destination repository's normal, explicitly targeted contribution workflow. Any later branch, commit, push, pull request, or shared-store write is a separate authorized operation with its own repository preflight and completion evidence.

The universal shared metadata and identity contracts are owned by `kb-bootstrap`. This command consumes those bundled contracts without requiring a particular consumer repository or embedding a registry path. It prepares a candidate but does not allocate or reserve a workspace-global lesson ID.
