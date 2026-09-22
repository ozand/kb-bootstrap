import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kb_bootstrap.raw_manifest as module


class RawManifestTests(unittest.TestCase):
    def setup_corpus(self, root):
        corpus = root / "kb" / "raw"
        corpus.mkdir(parents=True)
        return corpus

    def test_empty_and_mixed_file_bytes_are_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); corpus = self.setup_corpus(root)
            (corpus / "empty").write_bytes(b"")
            (corpus / ".hidden").write_bytes(b"\x00\xff")
            (corpus / "nested").mkdir(); (corpus / "nested" / "note.md").write_bytes(b"# note\n")
            before = {p.relative_to(corpus).as_posix(): p.read_bytes() for p in corpus.rglob("*") if p.is_file()}
            first, ok = module.write_raw_manifest(root, "kb/raw", "first.json")
            second, again = module.write_raw_manifest(root, "kb/raw", "second.json")
            self.assertTrue(ok and again)
            self.assertEqual((root / "first.json").read_bytes(), (root / "second.json").read_bytes())
            manifest = json.loads((root / "first.json").read_text(encoding="utf-8"))
            self.assertEqual([x["path"] for x in manifest["files"]], sorted(before))
            self.assertEqual(manifest["files"][0]["sha256"], hashlib.sha256(b"\x00\xff").hexdigest())
            self.assertEqual(before, {p.relative_to(corpus).as_posix(): p.read_bytes() for p in corpus.rglob("*") if p.is_file()})
            self.assertIn("new: 3", first)

    def test_four_comparison_categories_and_removed_not_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); corpus = self.setup_corpus(root)
            for name in ("same", "changed", "removed"):
                (corpus / name).write_bytes(name.encode())
            _, ok = module.write_raw_manifest(root, "kb/raw", "old.json")
            self.assertTrue(ok)
            (corpus / "changed").write_bytes(b"updated")
            (corpus / "removed").unlink()
            (corpus / "added").write_bytes(b"new")
            report, valid = module.write_raw_manifest(root, "kb/raw", "new.json", "old.json")
            self.assertTrue(valid)
            for line in ("new: 1", "changed: 1", "unchanged: 1", "removed: 1", "removed: removed"):
                self.assertIn(line, report)
            self.assertEqual([x["path"] for x in json.loads((root / "new.json").read_text())["files"]], ["added", "changed", "same"])

    def test_unsafe_prior_and_output_paths_block_without_source_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); corpus = self.setup_corpus(root)
            (corpus / "safe").write_bytes(b"source")
            for output in ("../escape.json", "kb/raw/output.json", "CON.json", "trailing./x.json"):
                with self.subTest(output=output):
                    report, valid = module.write_raw_manifest(root, "kb/raw", output)
                    self.assertFalse(valid)
                    self.assertIn("RESULT: BLOCKED", report)
            for payload in (b"{}", b'{"schema": 1, "schema": 2}', b"not-json"):
                (root / "prior.json").write_bytes(payload)
                report, valid = module.write_raw_manifest(root, "kb/raw", "next.json", "prior.json")
                self.assertFalse(valid)
                self.assertFalse((root / "next.json").exists())
            self.assertEqual((corpus / "safe").read_bytes(), b"source")

    def test_symlinks_and_unsupported_hard_links_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory); corpus = self.setup_corpus(root)
            (corpus / "safe").write_bytes(b"safe")
            try:
                (corpus / "linked").symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            report, valid = module.write_raw_manifest(root, "kb/raw", "out.json")
            self.assertFalse(valid); self.assertIn("symlink", report)
            self.assertNotIn(str(outside), report)
            self.assertFalse((root / "out.json").exists())
            (corpus / "linked").unlink()
            with patch.object(module.os, "link", side_effect=OSError("unsupported")):
                report, valid = module.write_raw_manifest(root, "kb/raw", "out.json")
            self.assertFalse(valid); self.assertFalse((root / "out.json").exists())
            self.assertEqual(list(root.glob(".kb-bootstrap-raw-*.tmp")), [])

    def test_race_created_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); corpus = self.setup_corpus(root)
            (corpus / "safe").write_bytes(b"safe")
            actual_link = os.link
            def race(source, target):
                Path(target).write_bytes(b"foreign")
                return actual_link(source, target)
            with patch.object(module.os, "link", side_effect=race):
                report, valid = module.write_raw_manifest(root, "kb/raw", "out.json")
            self.assertFalse(valid)
            self.assertEqual((root / "out.json").read_bytes(), b"foreign")
            self.assertEqual(list(root.glob(".kb-bootstrap-raw-*.tmp")), [])

    def test_cli_stdout_and_exit_codes(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.setup_corpus(root)
            command = [sys.executable, "-m", "kb_bootstrap.cli", "raw-manifest",
                       "--project-root", str(root), "--dir", "kb/raw", "--output", "out.json"]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0)
            self.assertEqual(first.stderr, "")
            self.assertTrue(first.stdout.startswith("=== Raw Manifest ===\nnew: 0\nchanged: 0\nunchanged: 0\nremoved: 0\n"))
            self.assertTrue(first.stdout.endswith("RESULT: OK\noutput: created\n"))
            blocked = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(blocked.returncode, 1)
            self.assertEqual(blocked.stderr, "")
            self.assertIn("ERROR: output already exists\nRESULT: BLOCKED", blocked.stdout)
            self.assertNotIn("output: created", blocked.stdout)

    def test_replacement_between_stat_and_open_blocks_before_read(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory); corpus = self.setup_corpus(root)
            source = corpus / "source"
            source.write_bytes(b"inside")
            external = Path(outside) / "private"
            external.write_bytes(b"outside")
            actual_open = module.os.open
            def swap(path, flags, *args, **kwargs):
                if Path(path) == source:
                    source.unlink()
                    source.symlink_to(external)
                return actual_open(path, flags, *args, **kwargs)
            try:
                with patch.object(module.os, "open", side_effect=swap):
                    report, valid = module.write_raw_manifest(root, "kb/raw", "out.json")
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            self.assertFalse(valid)
            self.assertIn("RESULT: BLOCKED", report)
            self.assertNotIn(str(external), report)
            self.assertFalse((root / "out.json").exists())

    def test_previous_replacement_between_stat_and_open_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); corpus = self.setup_corpus(root)
            (corpus / "source").write_bytes(b"inside")
            _, valid = module.write_raw_manifest(root, "kb/raw", "prior.json")
            self.assertTrue(valid)
            prior = root / "prior.json"
            actual_open = module.os.open
            def replace(path, flags, *args, **kwargs):
                if Path(path) == prior:
                    prior.write_bytes(prior.read_bytes().replace(b"inside", b"inside"))
                    # Force a distinct inode with otherwise valid, same-sized JSON.
                    moved = root / "old-prior"
                    prior.rename(moved)
                    prior.write_bytes(moved.read_bytes())
                return actual_open(path, flags, *args, **kwargs)
            with patch.object(module.os, "open", side_effect=replace):
                report, valid = module.write_raw_manifest(root, "kb/raw", "next.json", "prior.json")
            self.assertFalse(valid)
            self.assertIn("RESULT: BLOCKED", report)
            self.assertFalse((root / "next.json").exists())

    def test_portable_names_and_case_collisions_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); corpus = self.setup_corpus(root)
            for name in ("CON.txt", "bad?.md", "trailing."):
                with self.subTest(name=name):
                    path = corpus / name
                    try:
                        path.write_bytes(b"content")
                    except OSError:
                        continue  # Unsupported names cannot be constructed on this host.
                    if name not in [entry.name for entry in corpus.iterdir()]:
                        path.unlink()
                        continue  # The filesystem normalized this name before scanning.
                    report, valid = module.write_raw_manifest(root, "kb/raw", "out.json")
                    self.assertFalse(valid)
                    self.assertIn("ERROR: corpus path is unsafe or colliding", report)
                    self.assertFalse((root / "out.json").exists())
                    path.unlink()
            try:
                (corpus / "Alias").write_bytes(b"one")
                (corpus / "alias").write_bytes(b"two")
            except OSError:
                self.skipTest("case-distinct names unavailable on this filesystem")
            if len(list(corpus.iterdir())) == 2:
                report, valid = module.write_raw_manifest(root, "kb/raw", "out.json")
                self.assertFalse(valid)
                self.assertIn("colliding", report)

    def test_previous_inside_corpus_and_incompatible_schema_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); corpus = self.setup_corpus(root)
            (corpus / "capture").write_bytes(b"example")
            _, valid = module.write_raw_manifest(root, "kb/raw", "prior.json")
            self.assertTrue(valid)
            (corpus / "prior.json").write_bytes((root / "prior.json").read_bytes())
            report, valid = module.write_raw_manifest(root, "kb/raw", "next.json", "kb/raw/prior.json")
            self.assertFalse(valid)
            self.assertIn("previous must be outside corpus", report)
            (corpus / "prior.json").unlink()
            prior = json.loads((root / "prior.json").read_text(encoding="utf-8"))
            prior["corpus"] = "other/raw"
            (root / "wrong.json").write_text(json.dumps(prior), encoding="utf-8")
            report, valid = module.write_raw_manifest(root, "kb/raw", "next.json", "wrong.json")
            self.assertFalse(valid)
            self.assertIn("previous manifest is incompatible", report)
            self.assertFalse((root / "next.json").exists())

    def test_surrogate_filename_fails_closed_where_supported(self):
        if os.name != "posix":
            self.skipTest("undecodable byte filenames are POSIX-specific")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); corpus = self.setup_corpus(root)
            raw_name = os.fsencode(str(corpus)) + b"/bad-\xff"
            with open(raw_name, "wb") as stream:
                stream.write(b"content")
            report, valid = module.write_raw_manifest(root, "kb/raw", "out.json")
            self.assertFalse(valid)
            self.assertIn("RESULT: BLOCKED", report)
            self.assertFalse((root / "out.json").exists())
