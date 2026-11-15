# Local text capture

Use this route when the user supplies one local UTF-8 text file and authorizes handling it for this study. It runs locally; Surf, QMD, and network access are not needed. Keep private input in an untracked local directory such as `sources/` after verifying the consumer repository's tracking policy. A directory name alone does not make files private or untracked.

## Produce one RawCapture

From the consumer project root, create the study and choose a dedicated input root containing only the supplied file:

```bash
python3 SKILL_DIR/scripts/new_research.py <slug> --title "<study title>" --kb kb
python3 SKILL_DIR/scripts/produce_local_capture.py kb/research/<folder> \
  --input-root <input-root> --input <relative-file> --destination 001-local-source.md \
  --title "<source title>" --url "<caller-supplied source reference>" \
  --captured-at "<known ISO-8601 timestamp with UTC offset>" \
  --captured-by "<actual handler>" --entity "" --fidelity partial
```

Replace every placeholder with a literal value. `--url` is a caller-provided, unverified reference; do not invent a URL. `--captured-at` is required: use a known, defensible time with an offset, never the current time or file modification time as a substitute. `--captured-by` names the actual person or agent handling the file. Leave `--entity` empty when no entity identity is established. Select `full`, `partial`, or `blocked` honestly; text alone does not establish completeness. `partial` is a conservative choice when capture fidelity is unknown.

The helper accepts one UTF-8 file up to 64 MiB, without a BOM or unsupported control characters. It adds RawCapture metadata while preserving the source body bytes; it does not extract attachments, normalize text, fetch the reference, or verify source identity or completeness. The destination must be a new `NNN-<lowercase-slug>.md` path under the selected study. The helper never overwrites. `BLOCKED` or `UNSUPPORTED` means no output was created; `PARTIAL` means this attempt created output that may be incomplete—inspect it and resolve explicitly before proceeding. Do not retry over an existing destination or delete/replace a partial file blindly.

Then finish the brief, review the capture and write the report using the ordinary workflow. The checker verifies required files, links and metadata markers, not source completeness or semantic correctness. For non-UX work only, set the screenshot threshold to zero; that is not evidence of UI coverage:

```bash
python3 SKILL_DIR/scripts/check_research.py kb/research/<folder> --kb kb --min-screenshots 0 --skip-validate
kb-bootstrap validate-core --dir kb
```

If `kb-bootstrap` is unavailable, report core validation as `NOT RUN`; keep consumer-owned checks separate. QMD retrieval or index maintenance remains optional and separately authorized.

## Import an already prepared RawCapture

When the supplied file is already a complete RawCapture Markdown file that passes the importer's checks, use `import_local_capture.py` instead of producing another envelope:

```bash
python3 SKILL_DIR/scripts/import_local_capture.py kb/research/<folder> \
  --input-root <input-root> --input <relative-file> --destination 001-local-source.md
```

This copies the exact selected bytes into a new study path and preserves the declared metadata. It does not create a new observation, fetch the reference, or establish independence, identity, completeness, provenance, or publication eligibility. The target must not already exist; `BLOCKED`/`UNSUPPORTED` creates no output, while `PARTIAL` indicates an incomplete copy owned by the attempt. Inspect and resolve partial output explicitly; never overwrite or retry blindly.
