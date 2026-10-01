# W12-A5: checkpoint byte-verifier compatibility

Refs #133 and #121. Base is PR #144 at b389181827b64aade6ccd2d5e7bd2d85b5263bb9, which already fixes the imported raw-manifest signature helper.

Only kb_bootstrap/gliner_checkpoint.py and new tests/test_checkpoint_stat_compatibility.py may change.
Replace the remaining unsupported Path.stat keyword call with the minimum compatible implementation, preserving regular-file verification and all accepted ADR-011 byte-digest rules.
Use only invented small local files. Do not acquire, install, parse or load any model; the function verifies bytes only.
Reproduce the legacy API error, test valid and mismatched digests, symlink rejection and preservation of input bytes, then run existing checkpoint tests and the full suite.
Do not edit raw_manifest, graph, governance, lessons, dependencies, schemas or the support floor. The older-runtime simulation does not establish real Python 3.8 support.
Return the full exact two-file diff, byte count, SHA-256 and source identities, with actual test results. The coordinator publishes; no merge or branch updates by the executor.
