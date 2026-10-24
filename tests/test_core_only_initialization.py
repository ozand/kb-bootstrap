import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.cli import main


class CoreOnlyInitializationTests(unittest.TestCase):
    def invoke(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with patch("sys.argv", ["kb-bootstrap", *map(str, args)]), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main()
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def invoke_bytes(self, *args):
        class BinaryCapture:
            def __init__(self):
                self.buffer = io.BytesIO()
            def write(self, text):
                raise AssertionError("binary receipt must use the UTF-8 buffer")
            def flush(self):
                pass
        out, err = BinaryCapture(), BinaryCapture()
        with patch("sys.argv", ["kb-bootstrap", *map(str, args)]), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main()
            except SystemExit as exc:
                code = exc.code
        return code, out.buffer.getvalue(), err.buffer.getvalue()

    def test_core_only_single_has_exact_allowlist_and_local_core_works(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "new"
            code, out, err = self.invoke("--target", root, "--core-only")
            self.assertEqual((code, err), (0, ""))
            self.assertTrue(out.startswith("CORE_ONLY_CREATED\nLAYOUT=single\n"))
            expected = {
                ".agents/skills/kb-wiki-builder/SKILL.md", ".gitignore",
                "kb/raw/.gitkeep", "kb/research/.gitkeep", "kb/wiki/entities/.gitkeep",
                "kb/wiki/concepts/.gitkeep", "kb/wiki/reports/.gitkeep",
            }
            actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(actual, expected)
            self.assertIn("QMD=NOT_CONFIGURED\nSURF=NOT_CONFIGURED\n", out)
            concept = root / "kb/wiki/concepts/example.md"
            concept.write_text("---\ntype: Concept\n---\n# Example\n", encoding="utf-8")
            code, out, _ = self.invoke("validate-core", "--dir", root / "kb")
            self.assertEqual(code, 0, out)
            code, out, _ = self.invoke("read-local", "wiki/concepts/example.md", "--dir", root / "kb")
            self.assertEqual(code, 0, out)

    def test_umbrella_and_default_legacy_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "umbrella"
            code, out, err = self.invoke("--target", root, "--type", "umbrella", "--core-only")
            self.assertEqual(code, 0, err)
            self.assertTrue(out.startswith("CORE_ONLY_CREATED\nLAYOUT=umbrella\n"))
            self.assertEqual({p.name for p in (root / "kb").iterdir()}, {"raw", "research", "wiki", "apps", "systems", "architecture"})
            legacy = Path(temp) / "legacy"
            code, out, _ = self.invoke("--target", legacy)
            self.assertIsNone(code)
            self.assertTrue((legacy / "qmd.json").is_file())
            self.assertTrue((legacy / ".agents/skills/qmd-operator/SKILL.md").is_file())
            self.assertTrue((legacy / ".agents/skills/market-research/SKILL.md").is_file())

    def test_blocks_repeat_conflict_subcommand_and_preserves_existing_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "new"
            self.assertEqual(self.invoke("--target", root, "--core-only")[0], 0)
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            code, out, err = self.invoke("--target", root, "--core-only")
            self.assertEqual((code, out), (1, ""))
            self.assertIn("REASON=fresh_target_required", err)
            self.assertEqual(before, {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()})
            empty = Path(temp) / "empty"
            empty.mkdir()
            code, _, err = self.invoke("--target", empty, "--core-only", "--with-project-lessons")
            self.assertEqual(code, 1)
            self.assertIn("REASON=conflicting_flags", err)
            code, _, err = self.invoke("validate-core", "--core-only")
            self.assertEqual(code, 2)
            self.assertIn("initialization-only", err)
            self.assertEqual(list(empty.iterdir()), [])

    def test_target_value_matching_subcommand_is_not_parsed_as_command(self):
        for option in ("--target", "--target="):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "validate-core"
                args = (option, str(root)) if option == "--target" else (option + str(root),)
                code, out, err = self.invoke(*args, "--core-only")
                self.assertEqual((code, err), (0, ""))
                self.assertTrue(out.startswith("CORE_ONLY_CREATED"))
                self.assertTrue((root / "kb/wiki/concepts/.gitkeep").is_file())
            code, _, err = self.invoke("--core-only", "validate-core")
            self.assertEqual(code, 2)
            self.assertIn("initialization-only", err)

    def test_abbreviated_core_flag_with_subcommand_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "new"
            code, out, err = self.invoke("--core", "validate-core", "--dir", target)
            self.assertEqual(code, 2)
            self.assertEqual(out, "")
            self.assertIn("initialization-only", err)
            self.assertFalse(target.exists())

    def test_nested_missing_target_creates_ancestors(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "missing-parent" / "kb"
            code, out, err = self.invoke("--target", root, "--core-only")
            self.assertEqual((code, err), (0, ""))
            self.assertTrue(out.startswith("CORE_ONLY_CREATED\n"))
            self.assertTrue((root / "kb/wiki/concepts/.gitkeep").is_file())

    def test_nested_target_failure_reports_partial_without_outside_paths(self):
        original_mkdir = Path.mkdir
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "first" / "second" / "kb"
            created_ancestor = root.parents[1]
            def fail_second_ancestor(path, *args, **kwargs):
                if path == root.parent:
                    raise OSError("private nested target path")
                return original_mkdir(path, *args, **kwargs)
            with patch.object(Path, "mkdir", fail_second_ancestor):
                code, out, err = self.invoke("--target", root, "--core-only")
            self.assertEqual((code, out), (1, ""))
            self.assertEqual(err, "CORE_ONLY_PARTIAL\nLAYOUT=single\nREASON=io_error\nQMD=NOT_CONFIGURED\nSURF=NOT_CONFIGURED\n")
            self.assertTrue(created_ancestor.is_dir())
            self.assertFalse(root.exists())
            self.assertNotIn(temp, err)

    def test_core_only_receipts_are_lf_only_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "new"
            code, out, err = self.invoke_bytes("--target", root, "--core-only")
            self.assertEqual((code, err), (0, b""))
            self.assertIn(b"CORE_ONLY_CREATED\nLAYOUT=single\n", out)
            self.assertNotIn(b"\r", out)
            code, out, err = self.invoke_bytes("--target", root, "--core-only")
            self.assertEqual((code, out), (1, b""))
            self.assertEqual(err, b"CORE_ONLY_BLOCKED\nREASON=fresh_target_required\n")
            self.assertNotIn(b"\r", err)

    def test_partial_receipt_is_lf_only_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "partial"
            original = Path.open
            def fail_on_gitignore(path, *args, **kwargs):
                if path.name == ".gitignore":
                    raise OSError("private path")
                return original(path, *args, **kwargs)
            with patch.object(Path, "open", fail_on_gitignore):
                code, out, err = self.invoke_bytes("--target", root, "--core-only")
            self.assertEqual((code, out), (1, b""))
            self.assertTrue(err.startswith(b"CORE_ONLY_PARTIAL\nLAYOUT=single\n"))
            self.assertNotIn(b"\r", err)

    def test_pre_mutation_io_failures_are_blocked_on_stderr(self):
        original_mkdir = Path.mkdir
        for existing_target, failure_path in ((False, "new"), (True, ".agents")):
            with self.subTest(existing_target=existing_target), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "new"
                if existing_target:
                    root.mkdir()
                before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}

                def fail_mkdir(path, *args, **kwargs):
                    if path.name == failure_path:
                        raise OSError(f"private path {path}")
                    return original_mkdir(path, *args, **kwargs)

                with patch.object(Path, "mkdir", fail_mkdir):
                    code, out, err = self.invoke("--target", root, "--core-only")
                self.assertEqual((code, out), (1, ""))
                self.assertEqual(err, "CORE_ONLY_BLOCKED\nREASON=io_error\n")
                self.assertNotIn(temp, err)
                self.assertEqual(before, {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()})
                if existing_target:
                    self.assertEqual(list(root.iterdir()), [])
                else:
                    self.assertFalse(root.exists())

    def test_partial_failure_keeps_created_prefix_and_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "partial"
            original = Path.open
            def fail_on_gitignore(path, *args, **kwargs):
                if path.name == ".gitignore":
                    raise OSError("private absolute path must not leak")
                return original(path, *args, **kwargs)
            with patch.object(Path, "open", fail_on_gitignore):
                code, out, err = self.invoke("--target", root, "--core-only")
            self.assertEqual((code, out), (1, ""))
            self.assertIn("CORE_ONLY_PARTIAL\nLAYOUT=single\nCREATED=.agents/skills/kb-wiki-builder/SKILL.md\nREASON=io_error", err)
            self.assertTrue((root / ".agents/skills/kb-wiki-builder/SKILL.md").is_file())
            self.assertNotIn(temp, err)


if __name__ == "__main__":
    unittest.main()
