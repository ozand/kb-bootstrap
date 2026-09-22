import hashlib
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import kb_bootstrap.published_bundle_export as MODULE
from kb_bootstrap.published_bundle_export import build_published_bundle, write_published_bundle


def write(root, relative, content):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class PublishedBundleTests(unittest.TestCase):
    def concept(self, root, relative="concept.md"):
        return write(root, relative, "---\ntype: Concept\n---\n# Concept\n")

    def test_members_metadata_determinism_and_source_immutability(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.concept(root, "nested/concept.md")
            write(root, "index.md", "# Index\n")
            write(root, "nested/log.md", "## 2026-09-21\n")
            write(root, "RAW/private.md", "not canonical\n")
            write(root, "lessons/PROJECT-0001.md", "not canonical\n")
            write(root, "image.png", "ignored")
            original = source.read_bytes()
            first, report, valid = build_published_bundle(root)
            second, _, again = build_published_bundle(root)
            self.assertTrue(valid and again)
            self.assertEqual(first, second)
            self.assertEqual(hashlib.sha256(first).digest(), hashlib.sha256(second).digest())
            self.assertEqual(source.read_bytes(), original)
            self.assertIn("Excluded layers: raw/, lessons/", report)
            with zipfile.ZipFile(__import__("io").BytesIO(first)) as archive:
                self.assertEqual(archive.namelist(), ["index.md", "nested/concept.md", "nested/log.md"])
                for info in archive.infolist():
                    self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                    self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                    self.assertEqual(info.extra, b"")
                    self.assertFalse(info.is_dir())

    def test_reserved_rules_and_case_variants_block_deterministically(self):
        fixtures = (
            ("INDEX.MD", "# Index\n", "reserved filename must use exact lowercase"),
            ("nested/index.md", "---\nokf_version: '0.2'\n---\n", "reserved file must not have frontmatter"),
            ("log.md", "---\nkey: value\n---\n", "reserved file must not have frontmatter"),
            ("log.md", "## 2026-02-30\n", "log date heading is invalid"),
            ("log.md", "## 2026-09-2\n", "log date heading is invalid"),
            ("log.md", "## 2026/09/21\n", "log date heading is invalid"),
        )
        for relative, content, message in fixtures:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.concept(root)
                write(root, relative, content)
                data, report, valid = build_published_bundle(root)
                self.assertFalse(valid)
                self.assertEqual(data, b"")
                self.assertIn(message, report)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.concept(root)
            write(root, "index.md", "---\ncustom: retained\n---\n# Index\n")
            write(root, "log.md", "## 2026-09-20\n## 2026-09-21\n")
            _, report, valid = build_published_bundle(root)
            self.assertTrue(valid)
            self.assertIn("WARNING: index.md: root index has unknown metadata", report)
            self.assertIn("WARNING: log.md: log dates are not newest-first", report)

    def test_index_readability_warning_ignores_fenced_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.concept(root)
            write(root, "index.md", "```markdown\n# Not a heading\n- not a list\n```\nplain\n")
            _, report, valid = build_published_bundle(root)
            self.assertTrue(valid)
            self.assertIn("WARNING: index.md: index has no heading or list entry", report)

    def test_output_safety_race_and_hard_link_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); kb = root / "kb"; kb.mkdir(); self.concept(kb)
            existing = root / "bundle.zip"; existing.write_text("foreign", encoding="utf-8")
            report, valid = write_published_bundle(root, "kb", "bundle.zip")
            self.assertFalse(valid); self.assertIn("output already exists", report)
            self.assertEqual(existing.read_text(encoding="utf-8"), "foreign")
            for output, message in (("../bundle.zip", "output path must be relative"), ("kb/bundle.zip", "outside the canonical root"), ("bundle.tar", "must end with .zip")):
                report, valid = write_published_bundle(root, "kb", output)
                self.assertFalse(valid); self.assertIn(message, report)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); kb = root / "kb"; kb.mkdir(); self.concept(kb)
            with patch.object(MODULE.os, "link", side_effect=OSError("unsupported")):
                report, valid = write_published_bundle(root, "kb", "bundle.zip")
            self.assertFalse(valid); self.assertIn("cannot be published exclusively", report)
            self.assertFalse((root / "bundle.zip").exists())

    def test_source_change_blocks_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); kb = root / "kb"; kb.mkdir()
            source = self.concept(kb)
            real_signature = MODULE._signature
            calls = {"count": 0}
            def mutate(path):
                calls["count"] += 1
                if calls["count"] == 2:
                    source.write_text("---\ntype: Changed\n---\n", encoding="utf-8")
                return real_signature(path)
            with patch.object(MODULE, "_signature", side_effect=mutate):
                report, valid = write_published_bundle(root, "kb", "bundle.zip")
            self.assertFalse(valid)
            self.assertIn("file changed while being read", report)
            self.assertFalse((root / "bundle.zip").exists())

    def test_symlinked_source_fails_closed_when_available(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory); target = Path(outside) / "outside.md"
            target.write_text("---\ntype: External\n---\n", encoding="utf-8")
            try:
                (root / "linked.md").symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")
            data, report, valid = build_published_bundle(root)
            self.assertFalse(valid); self.assertEqual(data, b"")
            self.assertIn("symlinked file is not allowed", report)
            self.assertNotIn(str(target), report)

    def test_race_created_output_is_preserved_and_staging_is_cleaned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); kb = root / "kb"; kb.mkdir(); self.concept(kb)
            real_link = os.link
            def race_link(source, destination):
                Path(destination).write_text("foreign", encoding="utf-8")
                return real_link(source, destination)
            with patch.object(MODULE.os, "link", side_effect=race_link):
                report, valid = write_published_bundle(root, "kb", "bundle.zip")
            self.assertFalse(valid)
            self.assertIn("cannot be published exclusively", report)
            self.assertEqual((root / "bundle.zip").read_text(encoding="utf-8"), "foreign")
            self.assertEqual(list(root.glob(".kb-bootstrap-bundle-*.tmp")), [])

    def test_excluded_layers_do_not_apply_reserved_spelling_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.concept(root)
            write(root, "raw/INDEX.MD", "private\n")
            write(root, "Lessons/Log.Md", "private\n")
            data, report, valid = build_published_bundle(root)
            self.assertTrue(valid)
            self.assertIn("RESULT: OK", report)
            with zipfile.ZipFile(__import__("io").BytesIO(data)) as archive:
                self.assertEqual(archive.namelist(), ["concept.md"])
