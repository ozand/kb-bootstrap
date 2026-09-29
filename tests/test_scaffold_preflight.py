"""Synthetic checks for the non-CLI scaffold preflight prototype."""

import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.scaffold_preflight import (
    GENERATED_QMD_PATHS, _descriptor_support,
    build_managed_file_map, inspect_managed_files,
)

CAPABLE = _descriptor_support()


def qmd_payloads():
    return {name: b"synthetic qmd\n" for name in GENERATED_QMD_PATHS}


def fixture_package(root, research=True):
    skills = root / "templates/skills"
    for name in ("kb-wiki-builder", "qmd-operator", "kb-lookup"):
        target = skills / name / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"synthetic skill\n")
    if research:
        for name in ("SKILL.md", "scripts/check.py", "references/info.md",
                     "assets/brief.md", "evals/check.json", "__pycache__/ignore.pyc"):
            target = skills / "market-research" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"synthetic research\n")
    return root


def install_fixture(root, managed):
    for name, content in managed.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and not p.is_symlink()}


def statuses(root, managed, limit=10000):
    return {r.path: r.status for r in inspect_managed_files(root, managed, size_limit=limit)}


def make_symlink(test, link, destination):
    try:
        link.symlink_to(destination)
    except (OSError, NotImplementedError):
        test.skipTest("symlink creation unavailable")


class SyntheticInventoryTests(unittest.TestCase):
    def test_complete_inventory_and_exclusions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture_package(Path(tmp))
            managed = build_managed_file_map(root, qmd_payloads())
            self.assertEqual(len(managed), 11)
            self.assertFalse(any("__pycache__" in name for name in managed))
            self.assertEqual(list(managed), sorted(managed))

    def test_missing_empty_non_directory_and_incomplete_research(self):
        for mode in ("missing", "empty", "file", "incomplete"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = fixture_package(Path(tmp), research=False)
                market = root / "templates/skills/market-research"
                if mode == "file":
                    market.write_bytes(b"not a directory")
                elif mode != "missing":
                    market.mkdir()
                    if mode == "incomplete":
                        (market / "only-script.py").write_bytes(b"pass\n")
                with self.assertRaises(ValueError):
                    build_managed_file_map(root, qmd_payloads())

    def test_inventory_errors_are_sanitized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture_package(Path(tmp))
            with patch.object(Path, "read_bytes", side_effect=OSError("/synthetic-private-root/file")):
                with self.assertRaises(ValueError) as caught:
                    build_managed_file_map(root, qmd_payloads())
            self.assertNotIn("synthetic-private", str(caught.exception))
            with self.assertRaises(ValueError):
                build_managed_file_map(root, {"qmd.json": b"partial"})

    def test_inventory_enumeration_failure_is_not_silently_omitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture_package(Path(tmp))
            market = root / "templates/skills/market-research"
            locked = market / "locked"
            locked.mkdir()
            (locked / "hidden.md").write_bytes(b"must not disappear\n")
            real_scandir = os.scandir

            def failing_scandir(path):
                if Path(path) == locked:
                    raise PermissionError("/synthetic-private-root/locked")
                return real_scandir(path)

            with patch("tools.scaffold_preflight.os.scandir", side_effect=failing_scandir):
                with self.assertRaises(ValueError) as caught:
                    build_managed_file_map(root, qmd_payloads())
            self.assertEqual(str(caught.exception), "trusted inventory is unavailable")
            self.assertNotIn("synthetic-private", str(caught.exception))

    def test_unsafe_names_do_not_leak_values(self):
        for name in (".", "/synthetic-private-root/file", "../escape", "a/../b", "a//b", "./a", "a\\b", "nul\0value"):
            with self.subTest(name=name), self.assertRaises(ValueError) as caught:
                inspect_managed_files("ignored", {name: b"x"}, size_limit=1)
            self.assertEqual(str(caught.exception), "invalid managed path")

    def test_unsupported_platform_is_unavailable(self):
        with patch("tools.scaffold_preflight._descriptor_support", return_value=False), patch(
            "tools.scaffold_preflight.os.open", side_effect=AssertionError("must not open")
        ):
            self.assertEqual(statuses("ignored", {"a": b"x"}), {"a": "unavailable"})


@unittest.skipUnless(CAPABLE, "descriptor-relative no-follow inspection unavailable")
class SyntheticInspectionTests(unittest.TestCase):
    def test_all_classes_and_unrelated_files_preserved(self):
        with tempfile.TemporaryDirectory() as pkg, tempfile.TemporaryDirectory() as tmp:
            managed = build_managed_file_map(fixture_package(Path(pkg)), qmd_payloads())
            root = Path(tmp)
            install_fixture(root, managed)
            self.assertEqual(set(statuses(root, managed).values()), {"matching"})
            for name in managed:
                (root / name).write_bytes(b"edited\n")
            extra = root / ".agents/skills/market-research/consumer.txt"
            extra.write_bytes(b"keep")
            before = snapshot(root)
            self.assertEqual(set(statuses(root, managed).values()), {"content-differs"})
            self.assertEqual(snapshot(root), before)
            self.assertNotIn(extra.relative_to(root).as_posix(), statuses(root, managed))

    def test_missing_and_partial_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "absent"
            managed = {"a/file": b"a", "b/file": b"b"}
            self.assertEqual(set(statuses(root, managed).values()), {"missing"})
            self.assertFalse(root.exists())
            install_fixture(root, {"a/file": b"a"})
            self.assertEqual(statuses(root, managed), {"a/file": "matching", "b/file": "missing"})

    def test_target_ancestor_symlink_is_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install_fixture(root / "real/kb", {"file": b"x"})
            alias = root / "alias"
            make_symlink(self, alias, root / "real")
            with patch("tools.scaffold_preflight.os.read", side_effect=AssertionError("must not read")):
                self.assertEqual(statuses(alias / "kb", {"file": b"x"}), {"file": "unsafe"})

    def test_relative_target_and_missing_relative_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install_fixture(root / "kb", {"file": b"x"})
            with patch.object(Path, "cwd", return_value=root):
                self.assertEqual(statuses(Path("kb"), {"file": b"x"}), {"file": "matching"})
                self.assertEqual(statuses(Path("absent"), {"file": b"x"}), {"file": "missing"})
            self.assertFalse((root / "absent").exists())

    def test_file_symlink_and_size_limit_prevent_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "large").write_bytes(b"x" * 20)
            make_symlink(self, root / "link", root / "large")
            with patch("tools.scaffold_preflight.os.read", side_effect=AssertionError("must not read")):
                self.assertEqual(statuses(root, {"large": b"x", "link": b"x"}, 10),
                                 {"large": "unavailable", "link": "unsafe"})

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO unavailable")
    def test_fifo_is_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            os.mkfifo(root / "fifo")
            self.assertEqual(statuses(root, {"fifo": b""}), {"fifo": "unsafe"})

    def test_no_writes_and_deterministic_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install_fixture(root, {"z": b"z", "a": b"a"})
            before = snapshot(root)
            with patch("builtins.open", side_effect=AssertionError("unexpected file API")), patch.object(
                Path, "write_bytes", side_effect=AssertionError("write attempted")
            ), patch("tools.scaffold_preflight.os.write", side_effect=AssertionError("write attempted")):
                a = inspect_managed_files(root, {"z": b"z", "a": b"a"}, size_limit=1)
                b = inspect_managed_files(root, {"a": b"a", "z": b"z"}, size_limit=1)
            self.assertEqual(a, b)
            self.assertEqual([row.path for row in a], ["a", "z"])
            self.assertEqual(snapshot(root), before)


class InstalledInventoryTests(unittest.TestCase):
    def test_actual_packaged_inventory_is_complete(self):
        package = Path(__file__).resolve().parents[1] / "kb_bootstrap"
        managed = build_managed_file_map(package, qmd_payloads())
        market = package / "templates/skills/market-research"
        entries = {".agents/skills/market-research/" + p.relative_to(market).as_posix()
                   for p in market.rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
        self.assertEqual({name for name in managed if "/market-research/" in name}, entries)
        self.assertEqual(len(managed), len(entries) + 6)


if __name__ == "__main__":
    unittest.main()
