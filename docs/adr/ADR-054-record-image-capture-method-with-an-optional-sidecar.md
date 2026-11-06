# ADR-054: Record image capture method in an optional companion manifest

**Status**: Accepted
**Date**: 2026-11-07
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #125; ADR-029, ADR-033, ADR-050

Technical acceptance: authorized under the owner's standing delegation recorded in `AGENTS.md` and Issue #223. Independent review `independentab249` returned PASS for exact proposed revision `ac14613b57a1effa9aea3f6f1bef01e23fbfad3a`. This acceptance changes lifecycle status only; it does not implement the producer/manifest or authorize publication. The accepted decision is not implemented; its normative contract below is unchanged from the reviewed proposal.

## Context

Issue #125 criterion 6 requires truthful partial/blocked captures and specifically says a downloaded image must not be falsely reported as a screenshot of a rendered page. Current `capture_page.py::save_image` returns only a path or `None`; the caller rewrites the page Markdown link to a local image path, without retaining which branch produced its bytes. Accepted-download bytes have PNG/GIF/JPEG/WebP magic and size >2,000 and <=5,000,000. Otherwise the script navigates Surf to the image URL and asks Surf for a screenshot at a `.png` path. This is not a screenshot of the original article/product UI: the observed command navigates to the individual image URL first. The program does not verify the screenshot's visual contents.

The synthetic tests `tests/test_capture_page.py::CapturePageExclusiveTests::test_downloaded_image_uses_response_bytes_without_screenshot_fallback` and `::test_unsupported_download_uses_screenshot_fallback_bytes` assert output bytes and path only. Collision/partial tests cover preservation and status, not origin. The RawCapture frontmatter currently has page-level fields only. ADR-033's importer rejects unknown frontmatter keys and copies no attachments; ADR-050's local text producer has explicit caller claims but does not observe image acquisition. Therefore no existing retained field/sidecar supplies this information, and caller-supplied fidelity cannot establish it.

When fallback fails, `save_image` returns `None`; the Markdown retains its original image URL. Only successfully saved local images receive rewritten `img/...` links. Unselected images (`--images 0`, width below threshold, or after the cap) are not downloaded or screenshotted. A collision blocks the selected output; if earlier image outputs were created, current behavior reports partial and preserves them. These behaviors are distinct from evidence of image origin.

Research checkpoint recorded before edits at Issue #125 comment [6674397097](https://github.com/ozand/kb-bootstrap/issues/125#issuecomment-6674397097). Inspection used current main `a0baf6d619f9a0c5e91dcb65033bda236a9bd9b8`, current issue AC/comments, `capture_page.py`, its synthetic tests, `formats.md`, and accepted ADR-029/033/050. No live browser, network fetch, private images, models, QMD, or Surf execution was used.

## Decision

Propose that a future separately authorized implementation retain an optional JSON companion manifest next to a newly written RawCapture, with one entry per successfully saved local image, keyed by its exact study-relative image path. It records only the mechanism actually used by this script:

- `downloaded_response`: the bounded HTTP response byte path passed the existing size and magic checks and those bytes were saved;
- `surf_screenshot_fallback`: the download path was not accepted and the script issued Surf navigation to that image URL followed by a screenshot command, then saved the resulting file.

The second value means only that the fallback command path produced the saved file. It does **not** assert that the bytes depict the original page, product UI, a particular image, or a verified rendering. Neither value verifies source URL truth, permission, image semantics, visual completeness, or authenticity. A successfully retained artifact without a manifest entry has unknown/unrecorded origin; readers must not infer either value from absence. Older RawCapture files remain valid without this optional sidecar.

The manifest is a new, versioned artifact contract, not a new RawCapture frontmatter key: ADR-033 explicitly rejects unknown frontmatter, and changing it would break legacy import parsing. It does not revise RawCapture parsing/import or claim the sidecar is consumed by existing tools. Its exact format is UTF-8 JSON followed by one LF, with deterministic key order and no extra keys: top-level object `{"format":"kb-bootstrap-image-capture-methods","version":1,"capture":"raw/NNN-<slug>.md","images":[...]}`. `capture` is the exact study-relative POSIX path of the RawCapture. Each `images` entry is exactly `{"path":"raw/img/NNN-<k>.<ext>","method":"downloaded_response"}` or `{"path":"raw/img/NNN-<k>.png","method":"surf_screenshot_fallback"}`. Entries are ordered by image selection/save order, paths are unique, relative, and resolve only to the associated capture's `raw/img/` directory; no URL, digest, caller assertion, timestamp, or visual-content claim is included. An empty list is valid only when the run successfully saved no images; it does not classify unselected or failed images.

The companion basename is `<capture-stem>.images.json` in the same `raw/` directory, e.g. `raw/001-example.images.json` for `raw/001-example.md`. Consumers pair metadata only when both files exist at those exact paths and the manifest `capture` exactly equals the RawCapture's study-relative path. A rename/move is not transparent: do not rewrite either retained artifact; after moving, the manifest no longer pairs and image origin is unknown unless a separately reviewed copy is created at the new paths with a matching capture field. When manually retaining capture artifacts, select the RawCapture, this manifest, and all image files named in its entries together; because ADR-029 is per-file, partial selection is not atomic and must not be described as a complete provenance set.

Serialization is `json.dumps(value, ensure_ascii=False, separators=(",", ":"))` using insertion order, followed by exactly one `\\n`; `sort_keys` is not used because the field order above is part of this version-1 representation. The required top-level fields are exactly `format`, `version`, `capture`, and `images`; the required entry fields are exactly `path` and `method`. `format` is the fixed literal above, `version` is the integer `1`, and `images` is an array (possibly empty). Unknown fields, duplicate keys, non-string paths/methods, unsupported methods, malformed JSON, non-UTF-8 bytes, and missing final LF are invalid and cannot establish pairing.

Manifest publication uses ADR-029-compatible exclusive per-file no-overwrite behavior and occurs only after referenced images and the RawCapture have been created. It is not atomic with them. If manifest serialization/creation fails after capture output exists, preserve all files and report PARTIAL; do not claim any image origin not actually retained in a paired manifest. A pre-existing/raced manifest never gets overwritten or renamed. If its collision is discovered after this invocation has created image/Markdown outputs, report PARTIAL (not BLOCKED-before-write); if detected before any output creation, report BLOCKED. Never overwrite, renumber, retry under a different name, or delete output as rollback.

No origin metadata is emitted for unselected images or failed fallbacks because no local image artifact exists. Existing page-level `fidelity`, markdown rewriting, image selection, fallback, and optional Surf behavior remain unchanged. No alternate adapter framework, URL fetch change, screenshot of the original page, importer extension, migration, or automatic repair of historical captures is proposed.

## Consequences

### What gets easier

A researcher examining newly captured local image attachments can distinguish accepted response bytes from the code's Surf screenshot fallback without treating either as evidence of source truth. The explicit fallback label prevents the unsupported claim that the script captured the rendered article/product UI.

### What gets harder

The writer gains a second persisted artifact and another exclusive-write/partial-output case. Consumers that want the distinction must read and validate the optional manifest; older files and partial outputs can have unknown origin. Manifest pairing and lifecycle need focused tests and documentation.

### What does not change

Legacy RawCapture frontmatter remains parseable; no current importer or checker behavior is changed by this proposal. Surf remains optional and is still used only when the caller runs the existing Surf collector. No existing image is relabeled, no file is overwritten, and no network/browser/model/QMD action is authorized by the manifest contract.

## Alternatives Considered

- **Do nothing and rely on filenames/bytes:** rejected because neither records which code path produced an attachment, and file signatures alone do not prove transport path or screenshot observation.
- **Add an optional RawCapture frontmatter field:** rejected for this proposal because ADR-033 requires an exact supported key set and legacy import parsing would reject the new field; that alternative requires an explicit compatible importer contract.
- **Call fallback output a rendered-page screenshot:** rejected because the observed code navigates to the image URL before invoking screenshot, and there is no evidence it screenshotted the original page or that the bytes depict the expected visual content.
- **Record only caller-entered origin metadata:** rejected because the collector already knows which branch it executed; caller assertions would be weaker and could misdescribe the observed code path.
- **Encode method in image filenames or rewrite link syntax:** rejected because names/link markup are not an explicit typed provenance record and could change user-cited paths or Markdown parsing.
- **Use no sidecar but add an image-origin schema to all consumers now:** deferred; no existing consumer contract has been demonstrated, and broad parser/import integration is beyond this minimal decision stage.

## Acceptance Criteria if Implemented

- A newly written sidecar is exactly `<capture-stem>.images.json` beside its RawCapture, encoded as UTF-8 compact JSON with the specified insertion order and one final LF; its exact top-level fields are `format`, `version`, `capture`, and `images`, with `format` `kb-bootstrap-image-capture-methods`, integer `version` `1`, and a capture-relative POSIX path.
- Each image entry has exactly `path` and `method`, with a unique safe `raw/img/`-relative path and exactly one of `downloaded_response` or `surf_screenshot_fallback`; entries preserve save order. Accepted response bytes and fallback bytes are retained unchanged, and neither method claims original-page rendering, URL truth, visual identity, completeness, or authenticity.
- Pairing is valid only when the sidecar and RawCapture exist at their expected same-study paths and the sidecar `capture` equals the RawCapture study-relative path; renamed/moved or incomplete sets are unknown/unpaired, not repaired or relabeled. A retained complete set must include the RawCapture, sidecar, and every listed image, while acknowledging ADR-029 per-file non-atomicity.
- A pre-write existing/raced target yields `BLOCKED` with the winner unchanged; a collision or write/flush/close failure after this invocation created earlier outputs yields `PARTIAL` with all owned outputs preserved. No overwrite, retry, renumber, deletion, or false origin claim occurs.
- Legacy RawCapture files without a sidecar remain accepted by existing parsing/import behavior. No RawCapture frontmatter key, importer behavior, Surf optionality, URL dereference, network policy, or historical artifact is changed.

## Test Contract

| Claim if implemented | Test | Currently |
|---|---|---|
| Accepted response bytes produce the exact version-1 JSON structure and `downloaded_response` entry; image bytes are unchanged | Synthetic accepted response; assert UTF-8/LF serialization, exact top-level/entry keys, ordering, path, method, and bytes | Not implemented |
| Fallback output produces only `surf_screenshot_fallback` for that image and makes no original-page/rendering claim | Synthetic rejected response plus mocked Surf go/screenshot; assert exact entry and bounded method label | Not implemented |
| Fallback failure, unselected images, and `--images 0` produce no fabricated entry; failed fallback keeps existing original-URL Markdown behavior | Synthetic failure, width/cap and no-images cases; assert manifest contents and Markdown links | Not implemented |
| Manifest pairing requires exact path equality and listed paths stay within the paired `raw/img/`; rename/move cannot preserve an obsolete pairing claim | Synthetic consumer-validation fixtures for missing/mismatched capture, duplicate/escaping image paths, and renamed capture | Not implemented |
| Existing/raced image, Markdown, or manifest targets preserve winner; collision before writes is BLOCKED, collision after owned outputs is PARTIAL; no output is deleted | Synthetic exclusive-write collision at each publication stage and injected post-create failure | Not implemented |
| Legacy RawCapture without a manifest remains valid; complete retention selection includes capture, manifest, and referenced images | Existing importer compatibility test plus synthetic retained-file-set assertion; checker remains structural only | Not implemented |

## References

- Issue #125 acceptance criterion 6 and research checkpoint comment 6674397097
- `kb_bootstrap/templates/skills/market-research/scripts/capture_page.py`
- `tests/test_capture_page.py`
- `kb_bootstrap/templates/skills/market-research/references/formats.md`
- ADR-029, ADR-033, ADR-050
