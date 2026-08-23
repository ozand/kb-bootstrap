# Explicit lesson lookup bundle

`kb-bootstrap lesson-lookup` uses a dedicated read-only lookup bundle. This file is separate from the generated `lesson-stores.json`, which controls capture ownership and may point to lesson directories.

The lookup bundle names bounded JSON search exports explicitly:

```json
{
  "version": 1,
  "stores": [
    {
      "name": "project",
      "type": "local",
      "path": "project-lessons.json"
    },
    {
      "name": "workspace",
      "type": "shared",
      "path": "shared-lessons.json"
    }
  ]
}
```

Rules:

- at most one `local` and one `shared` store;
- paths are relative JSON files inside the bundle directory;
- local store accepts `PROJECT-XXXX` IDs;
- shared store accepts `KB-XXXX` IDs;
- local is searched first;
- shared is searched only when local returns no match;
- unavailable or timed-out stores are isolated;
- lookup reports sanitized store/type/lesson provenance and performs no writes.

Example:

```bash
kb-bootstrap lesson-lookup \
  --config lookup-bundle.json \
  --query "timeout" \
  --timeout 2
```

The bundle is an explicit export/search input, not hidden store discovery, capture routing, synchronization, or publication configuration.
