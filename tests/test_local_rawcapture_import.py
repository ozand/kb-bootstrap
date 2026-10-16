import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path("kb_bootstrap/templates/skills/market-research/scripts/import_local_capture.py").resolve()
SPEC = importlib.util.spec_from_file_location("import_local_capture", SCRIPT)
import_local_capture = importlib.util.module_from_spec(SPEC)
with patch("sys.dont_write_bytecode", True):
    SPEC.loader.exec_module(import_local_capture)
ImportErrorResult = import_local_capture.ImportErrorResult
import_capture = import_local_capture.import_capture


class LocalRawCaptureImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input_root = self.root / "inputs"
        self.input_root.mkdir()
        self.study = self.root / "kb/research/2026-10-16_demo"
        (self.study / "raw/img").mkdir(parents=True)
        self.source = self.input_root / "001-demo.md"
        self.raw = (
            "---\n"
            "type: RawCapture\n"
            'title: "Synthetic page"\n'
            'url: "https://example.test/page"\n'
            'captured_at: "2026-10-16T10:00:00+00:00"\n'
            'captured_by: "test"\n'
            'entity: ""\n'
            "fidelity: full\n"
            "tags: [saas, meeting-notes]\n"
            "---\n\n# Synthetic page\n\nLocal text.\n"
        ).encode("utf-8")
        self.source.write_bytes(self.raw)

    def run_import(self, dest="001-local.md"):
        return import_capture(self.study, self.input_root, "001-demo.md", dest)

    def test_script_cli_reports_import_and_blocked_collision(self):
        command = [sys.executable, str(SCRIPT), str(self.study),
                   "--input-root", str(self.input_root), "--input", "001-demo.md",
                   "--destination", "015-cli.md"]
        success = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertIn("IMPORTED: raw/015-cli.md", success.stdout)
        imported = self.study / "raw/015-cli.md"
        self.assertEqual(imported.read_bytes(), self.raw)
        blocked = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("BLOCKED: destination already exists", blocked.stdout)
        self.assertEqual(imported.read_bytes(), self.raw)

    def test_valid_capture_copied_byte_identically_without_identity_minting(self):
        status, relative = self.run_import()
        self.assertEqual((status, relative), ("IMPORTED", "raw/001-local.md"))
        imported = self.study / relative
        self.assertEqual(imported.read_bytes(), self.raw)
        self.assertFalse((self.study / relative.replace(".md", ".json")).exists())
        self.assertEqual(self.source.read_bytes(), self.raw)
        self.assertFalse((self.study / "raw/missing.md").exists())

    def test_wrong_raw_directory_name_is_rejected(self):
        study = self.root / "kb/research/2026-10-16_demo"
        wrong = study / "not-raw"
        (study / "raw").rename(wrong)
        with self.assertRaises(ImportErrorResult):
            import_capture(study, self.input_root, "001-demo.md", "001-local.md")

    def test_destination_name_and_existing_target_are_rejected(self):
        for name in ("1-local.md", "001-Upper.md", "001-two--words.md", "001-local.txt"):
            with self.subTest(name=name), self.assertRaises(ImportErrorResult):
                import_capture(self.study, self.input_root, "001-demo.md", name)
        target = self.study / "raw/001-local.md"
        target.write_bytes(b"prior")
        with self.assertRaises(ImportErrorResult) as caught:
            self.run_import()
        self.assertEqual(caught.exception.status, "BLOCKED")
        self.assertEqual(target.read_bytes(), b"prior")

    def test_destination_race_winner_is_preserved(self):
        original = import_local_capture._exclusive_copy
        def race(destination, data, study):
            with destination.open("xb") as stream:
                stream.write(b"racing winner")
            return original(destination, data, study)
        import_local_capture._exclusive_copy = race
        try:
            with self.assertRaises(ImportErrorResult) as caught:
                self.run_import("007-local.md")
        finally:
            import_local_capture._exclusive_copy = original
        self.assertEqual(caught.exception.status, "BLOCKED")
        self.assertEqual((self.study / "raw/007-local.md").read_bytes(), b"racing winner")

    def test_malformed_frontmatter_is_blocked_without_output(self):
        variants = (
            self.raw.replace(b"type: RawCapture", b"type: Other"),
            self.raw.replace(b"entity: \"\"", b"entity: \"\"\nextra: value"),
            self.raw.replace(b"tags: [saas, meeting-notes]", b"tags:\n  - saas"),
            self.raw.replace(b"captured_by: \"test\"", b"captured_by: |\n  test"),
            self.raw.replace(b"title: \"Synthetic page\"", b"title: \"first\"\ntitle: \"second\""),
            self.raw.replace(b"title: \"Synthetic page\"", b"title: 'single quotes'"),
            self.raw.replace(b"title: \"Synthetic page\"", b"title: \"multi\\nline\""),
            self.raw.replace(b"captured_at: \"2026-10-16T10:00:00+00:00\"", b"captured_at: tomorrow"),
            self.raw + b"\n---\nextra\n",
        )
        for raw in variants:
            with self.subTest(raw=raw[:40]):
                self.source.write_bytes(raw)
                with self.assertRaises(ImportErrorResult):
                    self.run_import("002-local.md")
                self.assertFalse((self.study / "raw/002-local.md").exists())

    def test_empty_quoted_required_fields_and_drive_unc_spellings_block(self):
        for field in ("title", "url", "captured_by", "captured_at"):
            line = next(line for line in self.raw.splitlines() if line.startswith(field.encode() + b": "))
            empty = self.raw.replace(line, field.encode() + b': ""')
            self.source.write_bytes(empty)
            with self.subTest(field=field), self.assertRaises(ImportErrorResult):
                self.run_import("013-local.md")
            self.assertFalse((self.study / "raw/013-local.md").exists())
        for spelling in (r"C:\capture.md", r"\\server\share.md"):
            with self.subTest(spelling=spelling), self.assertRaises(ImportErrorResult):
                import_capture(self.study, self.input_root, spelling, "014-local.md")
            self.assertFalse((self.study / "raw/014-local.md").exists())

    def test_unsafe_source_path_and_symlink_are_blocked(self):
        with self.assertRaises(ImportErrorResult):
            import_capture(self.study, self.input_root, "../001-demo.md", "005-local.md")
        outside = self.root / "outside.md"
        outside.write_bytes(self.raw)
        link = self.input_root / "002-link.md"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            return
        with self.assertRaises(ImportErrorResult):
            import_capture(self.study, self.input_root, "002-link.md", "005-local.md")
        self.assertFalse((self.study / "raw/005-local.md").exists())

    def test_malformed_utf8_and_size_limit_block_before_copy(self):
        self.source.write_bytes(b"\\xff")
        with self.assertRaises(ImportErrorResult):
            self.run_import("006-local.md")
        original_limit = import_local_capture.MAX_BYTES
        try:
            import_local_capture.MAX_BYTES = 16
            self.source.write_bytes(self.raw)
            with self.assertRaises(ImportErrorResult):
                self.run_import("006-local.md")
        finally:
            import_local_capture.MAX_BYTES = original_limit
        self.assertFalse((self.study / "raw/006-local.md").exists())

    def test_local_link_must_resolve_inside_destination_study(self):
        linked = self.raw.replace(b"Local text.", b"![image](img/present.png)")
        self.source.write_bytes(linked)
        with self.assertRaises(ImportErrorResult) as caught:
            self.run_import("003-local.md")
        self.assertEqual(caught.exception.status, "UNSUPPORTED")
        self.assertFalse((self.study / "raw/003-local.md").exists())
        (self.study / "raw/img/present.png").write_bytes(b"synthetic")
        self.assertEqual(self.run_import("003-local.md")[0], "IMPORTED")

    def test_link_target_classes(self):
        for index, target in enumerate(("C:/private.md", "\\\\\\\\server\\\\share.md", "../escape.md", "missing.md"), 8):
            with self.subTest(target=target):
                self.source.write_bytes(self.raw.replace(b"Local text.", f"[x]({target})".encode()))
                with self.assertRaises(ImportErrorResult):
                    self.run_import(f"{index:03d}-local.md")
                self.assertFalse((self.study / f"raw/{index:03d}-local.md").exists())
        for index, target in enumerate(("#section", "tag:example", "custom+scheme:value"), 12):
            with self.subTest(target=target):
                self.source.write_bytes(self.raw.replace(b"Local text.", f"[x]({target})".encode()))
                self.assertEqual(self.run_import(f"{index:03d}-local.md")[0], "IMPORTED")

    def test_raced_destination_is_not_renumbered(self):
        original_open = import_local_capture.os.open
        def race_target(path, flags, mode=0o777):
            if Path(path).name == "011-local.md":
                with Path(path).open("xb") as stream:
                    stream.write(b"winner")
            return original_open(path, flags, mode)
        import_local_capture.os.open = race_target
        try:
            with self.assertRaises(ImportErrorResult) as caught:
                self.run_import("011-local.md")
        finally:
            import_local_capture.os.open = original_open
        self.assertEqual(caught.exception.status, "BLOCKED")
        self.assertEqual((self.study / "raw/011-local.md").read_bytes(), b"winner")
        self.assertFalse((self.study / "raw/012-local.md").exists())

    def test_non_writable_destination_parent_blocks_without_partial_target(self):
        original_open = import_local_capture.os.open
        def fail_target(path, flags, mode=0o777):
            if Path(path).name == "010-local.md":
                raise OSError("synthetic destination open failure")
            return original_open(path, flags, mode)
        import_local_capture.os.open = fail_target
        try:
            with self.assertRaises(ImportErrorResult) as caught:
                self.run_import("010-local.md")
        finally:
            import_local_capture.os.open = original_open
        self.assertEqual(caught.exception.status, "BLOCKED")
        self.assertFalse((self.study / "raw/010-local.md").exists())

    def test_control_characters_in_link_targets_block_without_mutation(self):
        for codepoint in (0x7F, 0x80, 0x9F):
            with self.subTest(codepoint=codepoint):
                control = chr(codepoint)
                self.source.write_bytes(self.raw.replace(b"Local text.", f"[x](file{control}name)".encode("utf-8")))
                before = self.source.read_bytes()
                destination = self.study / f"raw/{codepoint:03d}-local.md"
                with self.assertRaises(ImportErrorResult) as caught:
                    import_capture(self.study, self.input_root, "001-demo.md", destination.name)
                self.assertEqual(caught.exception.status, "UNSUPPORTED")
                self.assertEqual(self.source.read_bytes(), before)
                self.assertFalse(destination.exists())

    def test_unsupported_markdown_links_and_external_urls_are_not_fetched(self):
        for body in (b"[ref][id]\n\n[id]: target.md\n", b"<img src=\"x\">", b"[x](../escape.md)"):
            self.source.write_bytes(self.raw.replace(b"Local text.", body))
            with self.subTest(body=body), self.assertRaises(ImportErrorResult):
                self.run_import("004-local.md")
        external = self.raw.replace(b"Local text.", b"[external](https://example.test/a)")
        self.source.write_bytes(external)
        self.assertEqual(self.run_import("004-local.md")[0], "IMPORTED")
