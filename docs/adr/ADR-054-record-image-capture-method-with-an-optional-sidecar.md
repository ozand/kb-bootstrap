# ADR-054: Record image capture method in an optional companion manifest

**Status**: Proposed
**Date**: 2026-11-07
**Authors**: Pi coding agent
**Supersedes**: None
**Related**: Issue #125; ADR-029, ADR-033, ADR-050

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

The manifest is a new, versioned artifact contract, not a new RawCapture frontmatter key: ADR-033 explicitly rejects unknown frontmatter, and changing it would break legacy import parsing. The proposal does not revise RawCapture parsing/import or claim the sidecar is consumed by existing tools. Pairing the sidecar to a page and validating paths must be bounded and explicit. Manifest publication must use ADR-029-compatible exclusive, per-file no-overwrite behavior. It is not atomic with Markdown/images: if the sidecar cannot be written after files exist, retain those files as ADR-029 requires, report PARTIAL, and make no origin claim for entries not retained in the manifest. Existing/raced sidecar is BLOCKED; never overwrite or renumber.

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

## Test Contract

| Claim if implemented | Test | Currently |
|---|---|---|
| Accepted response bytes are recorded as `downloaded_response`, not screenshot | Synthetic response bytes with valid magic/size; assert image bytes and exact manifest entry | Not implemented |
| Fallback output records only `surf_screenshot_fallback` and never claims original-page rendering | Synthetic rejected response + mocked Surf go/screenshot; assert saved bytes and bounded wording/value | Not implemented |
| Fallback failure produces no local-image origin entry and leaves source Markdown link behavior unchanged | Synthetic Surf failure; assert no image/manifest entry and original URL remains | Not implemented |
| Existing/raced output and manifest collisions preserve winner; earlier successful outputs remain and report PARTIAL | Synthetic exclusive-write collision/order fixtures | Not implemented |
| No image-selected/non-image cases create misleading metadata; old RawCapture without manifest remains valid | No-image/non-image fixtures and existing importer/legacy capture compatibility test | Not implemented |
| End-to-end saved artifact has a resolvable manifest-to-image association without overwriting previous captures | Synthetic capture-to-retained-artifact verification of Markdown, image and manifest paths | Not implemented |

## References

- Issue #125 acceptance criterion 6 and research checkpoint comment 6674397097
- `kb_bootstrap/templates/skills/market-research/scripts/capture_page.py`
- `tests/test_capture_page.py`
- `kb_bootstrap/templates/skills/market-research/references/formats.md`
- ADR-029, ADR-033, ADR-050
