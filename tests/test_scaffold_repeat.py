"""ADR-016 scaffold preflight regressions using synthetic targets."""
import contextlib
import hashlib
import json
import os
import subprocess
import tempfile
import sys
import unittest
from pathlib import Path
import shutil
from unittest.mock import patch

from kb_bootstrap.cli import main
from kb_bootstrap.scaffold_repeat import preflight, qmd_payloads, _inventory_files
from kb_bootstrap.qmd_names import project_slug


class ScaffoldRepeatTests(unittest.TestCase):
    def test_project_slug_portable_name_matrix(self):
        cases = {
            "demo": "demo",
            "sample_project-2": "sample_project-2",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(project_slug(source), expected)

        lossy = ["A B", "A@B", "A", "équipe", "!!!", "", "a" * 60, "_foo"]
        names = [project_slug(name) for name in lossy]
        self.assertNotEqual(names[0], names[1])
        self.assertNotEqual(names[0], project_slug("a-b"))
        self.assertNotEqual(project_slug("_foo"), project_slug("foo"))
        self.assertNotEqual(project_slug("foo-"), project_slug("foo"))
        self.assertEqual(project_slug("!!!").split("-")[0], "p")
        expected = hashlib.sha256("A B".encode("utf-8")).hexdigest()[:12]
        self.assertEqual(project_slug("A B"), f"a-b-{expected}")
        self.assertTrue(all(0 < len(name) <= 59 for name in names))
        self.assertTrue(all(name.isascii() and name[0].isalnum() for name in names))
        self.assertLessEqual(len(project_slug("z" * 1000)), 59)
        self.assertEqual(project_slug("a" * 60), project_slug("a" * 60))

    def test_qmd_generated_names_are_bounded_for_lossy_names(self):
        for basename in ("Пример проекта", "A B", "A@B", "!!!", "a" * 60):
            with self.subTest(basename=basename):
                payloads = qmd_payloads("single", project_slug(basename))
                for relative in ("qmd/collections/wiki.yaml", "qmd/collections/raw.yaml"):
                    line = next(line for line in payloads[relative].decode().splitlines() if line.startswith("name: "))
                    generated = line.split(": ", 1)[1]
                    self.assertLessEqual(len(generated), 64)
                    self.assertTrue(generated.isascii())

    def test_legacy_repeat_with_old_lossy_name_blocks_without_rewrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "consumer"
            self.assertIsNone(self.run_cli("--target", str(root)))
            wiki = root / "qmd/collections/wiki.yaml"
            wiki.write_text(wiki.read_text(encoding="utf-8").replace("consumer-wiki", "a-b-wiki"), encoding="utf-8")
            old_state = self.snapshot(root)
            self.assertEqual(self.run_cli("--target", str(root)), 1)
            self.assertEqual(old_state, self.snapshot(root))

    def test_fresh_generated_names_validate_and_repeats_are_noops(self):
        for basename in ("Simple_Project", "Пример проекта", "équipe", "A B", "A@B", "!!!", "a" * 60):
            with self.subTest(basename=basename), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / basename
                self.assertIsNone(self.run_cli("--target", str(target)))
                _, valid = __import__("kb_bootstrap.qmd_validator", fromlist=["validate_qmd_collections"]).validate_qmd_collections(target)
                self.assertTrue(valid, basename)
                before = self.snapshot(target)
                self.assertEqual(self.run_cli("--target", str(target)), 0)
                self.assertEqual(before, self.snapshot(target))

    def setUp(self):
        self.package = Path(__file__).parents[1] / "kb_bootstrap"

    def run_cli(self, *args):
        with patch("sys.argv", ["kb-bootstrap", *args]):
            return main()

    def snapshot(self, root):
        return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob("*") if p.is_file() and not p.is_symlink()}

    def test_qmd_payload_matches_text_writer_bytes(self):
        expected = qmd_payloads("single", "sample")
        config = """{\n  \"version\": \"1.0\",\n  \"workspace\": {\n    \"name\": \"sample_kb\",\n    \"collections_dir\": \"./qmd/collections\",\n    \"db_path\": \".qmd/vector.db\"\n  },\n  \"models\": {\n    \"embedding\": \"text-embedding-3-small\"\n  }\n}"""
        wiki = "name: sample-wiki\npaths:\n  - ../../kb/\nexclude:\n  - \"raw/**\"\n  - \"research/**\"\n  - \"**/.DS_Store\"\n"
        raw = "name: sample-raw\npaths:\n  - ../../kb/raw/\n  - ../../kb/research/\nexclude:\n  - \"**/.DS_Store\"\n"
        eol = os.linesep.encode()
        self.assertEqual(expected["qmd.json"], config.replace("\n", os.linesep).encode())
        self.assertEqual(expected["qmd/collections/wiki.yaml"], wiki.replace("\n", os.linesep).encode())
        self.assertEqual(expected["qmd/collections/raw.yaml"], raw.replace("\n", os.linesep).encode())

    def test_inventory_uses_all_packaged_files(self):
        mapping = _inventory_files(self.package)
        market = self.package / "templates/skills/market-research"
        actual = {".agents/skills/market-research/" + p.relative_to(market).as_posix()
                  for p in market.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                  and not p.name.endswith(".pyc")}
        self.assertEqual({p for p in mapping if "/market-research/" in p}, actual)

    def test_first_init_then_repeat_is_zero_write_noop_both_layouts(self):
        for layout in ("single", "umbrella"):
            with self.subTest(layout=layout), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "consumer"
                self.assertIsNone(self.run_cli("--target", str(root), "--type", layout))
                before = self.snapshot(root)
                mtimes = {p.relative_to(root).as_posix(): p.stat().st_mtime_ns
                          for p in root.rglob("*") if p.is_file()}
                self.assertEqual(self.run_cli("--target", str(root), "--type", layout), 0)
                self.assertEqual(before, self.snapshot(root))
                self.assertEqual(mtimes, {p.relative_to(root).as_posix(): p.stat().st_mtime_ns
                                          for p in root.rglob("*") if p.is_file()})

    def test_matching_repeat_does_not_rewrite_gitignore_or_touch_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "consumer"
            self.assertIsNone(self.run_cli("--target", str(root)))
            ignore = root / ".gitignore"
            ignore.write_text("# custom\r\n# kb-bootstrap generated artifacts\r\n/keep\r\n", encoding="utf-8")
            before_bytes = self.snapshot(root)
            before_times = {p.relative_to(root).as_posix(): p.stat().st_mtime_ns
                            for p in root.rglob("*") if p.is_file()}
            self.assertEqual(self.run_cli("--target", str(root)), 0)
            self.assertEqual(before_bytes, self.snapshot(root))
            self.assertEqual(before_times, {p.relative_to(root).as_posix(): p.stat().st_mtime_ns
                                            for p in root.rglob("*") if p.is_file()})

    def test_conflict_blocks_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "consumer"
            self.assertIsNone(self.run_cli("--target", str(root)))
            before = self.snapshot(root)
            qmd = root / "qmd.json"
            qmd.write_text('{"models":{"embedding":"custom"}}\n', encoding="utf-8")
            conflicted = self.snapshot(root)
            result = self.run_cli("--target", str(root))
            self.assertEqual(result, 1)
            self.assertEqual(conflicted, self.snapshot(root))
            self.assertNotEqual(before, conflicted)

    def test_repeated_optin_without_lessons_blocks_but_explicit_enable_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "consumer"
            self.assertIsNone(self.run_cli("--target", str(root)))
            before = self.snapshot(root)
            result = self.run_cli("--target", str(root), "--with-project-lessons")
            self.assertEqual(result, 1)
            self.assertEqual(before, self.snapshot(root))
            self.assertEqual(self.run_cli("enable-project-lessons", "--target", str(root)), 0)
            lesson_before = {name: (root / name).read_bytes() for name in (
                "kb/lessons/SCHEMA.md", "kb/lessons/index.yaml", "lesson-stores.json",
                ".agents/skills/kb-capture/SKILL.md")}
            self.assertEqual(self.run_cli("--target", str(root), "--with-project-lessons"), 0)
            self.assertEqual(lesson_before, {n: (root / n).read_bytes() for n in lesson_before})

    def test_partial_lesson_contract_blocks_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "consumer"
            self.assertIsNone(self.run_cli("--target", str(root)))
            (root / "lesson-stores.json").write_text("{}", encoding="utf-8")
            before = self.snapshot(root)
            self.assertEqual(self.run_cli("--target", str(root)), 1)
            self.assertEqual(before, self.snapshot(root))

    def test_optin_absent_lesson_contract_on_fresh_init_is_installed_after_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "fresh"
            self.assertIsNone(self.run_cli("--target", str(root), "--with-project-lessons"))
            self.assertTrue((root / "lesson-stores.json").is_file())
            self.assertTrue((root / "kb/lessons/index.yaml").is_file())

    def test_complete_populated_lessons_survive_flag_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "consumer"
            self.assertIsNone(self.run_cli("--target", str(root), "--with-project-lessons"))
            index = root / "kb/lessons/index.yaml"
            lesson = root / "kb/lessons/PROJECT-0001-example.md"
            lesson.write_text("---\nid: PROJECT-0001\n---\n# Example\n", encoding="utf-8")
            index.write_text("version: 1\nscope: project\nid_prefix: PROJECT-\nlessons:\n  - id: PROJECT-0001\n    path: kb/lessons/PROJECT-0001-example.md\n", encoding="utf-8")
            stores = root / "lesson-stores.json"
            data = json.loads(stores.read_text(encoding="utf-8"))
            data["shared"] = {"path": "shared", "read_only": True}
            stores.write_text(json.dumps(data), encoding="utf-8")
            preserved = {name: (root / name).read_bytes() for name in (
                "kb/lessons/SCHEMA.md", "kb/lessons/index.yaml", "lesson-stores.json",
                ".agents/skills/kb-capture/SKILL.md")}
            self.assertEqual(self.run_cli("--target", str(root)), 0)
            self.assertEqual(preserved, {name: (root / name).read_bytes() for name in preserved})

    def test_noop_invokes_no_initializer_mutation_primitives(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "consumer"
            self.assertIsNone(self.run_cli("--target", str(root)))
            with patch("kb_bootstrap.cli.create_dirs", side_effect=AssertionError("mkdir")), \
                 patch("kb_bootstrap.cli.append_gitignore_rules", side_effect=AssertionError("gitignore")), \
                 patch("kb_bootstrap.cli.shutil.copy2", side_effect=AssertionError("copy2")), \
                 patch("kb_bootstrap.cli.shutil.copytree", side_effect=AssertionError("copytree")), \
                 patch("kb_bootstrap.cli.enable_project_lessons", side_effect=AssertionError("lesson write")), \
                 patch("pathlib.Path.touch", side_effect=AssertionError("touch")):
                self.assertEqual(self.run_cli("--target", str(root)), 0)

    def test_cli_subprocess_single_and_umbrella_success_and_repeat(self):
        for layout in ("single", "umbrella"):
            with self.subTest(layout=layout), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / "consumer"
                command = [sys.executable, "-m", "kb_bootstrap.cli", "--target", str(target), "--type", layout]
                first = subprocess.run(command, capture_output=True, text=True, timeout=30)
                self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
                snapshot = self.snapshot(target)
                second = subprocess.run(command, capture_output=True, text=True, timeout=30)
                self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
                self.assertIn("OK (NO-OP)", second.stdout)
                self.assertEqual(snapshot, self.snapshot(target))

    def test_first_init_lesson_installer_failure_is_reported_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "fresh"
            with patch("kb_bootstrap.cli.enable_project_lessons", side_effect=OSError("private path")):
                self.assertEqual(self.run_cli("--target", str(root), "--with-project-lessons"), 1)
            self.assertTrue(root.is_dir())

    def test_every_fixed_file_conflict_blocks_without_mutation(self):
        for relative in ("qmd.json", "qmd/collections/wiki.yaml", "qmd/collections/raw.yaml"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "consumer"
                self.assertIsNone(self.run_cli("--target", str(root)))
                target = root / relative
                target.write_bytes(target.read_bytes() + b"user edit\\n")
                before = self.snapshot(root)
                self.assertEqual(self.run_cli("--target", str(root)), 1)
                self.assertEqual(before, self.snapshot(root))

    def test_every_managed_file_conflict_blocks_without_any_writes(self):
        managed = {**_inventory_files(self.package), **qmd_payloads("single", "consumer")}
        for relative in managed:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "consumer"
                self.assertIsNone(self.run_cli("--target", str(root)))
                path = root / relative
                path.write_bytes(path.read_bytes() + b"consumer edit\\n")
                before = self.snapshot(root)
                with patch("kb_bootstrap.cli.create_dirs", side_effect=AssertionError("mkdir")), \
                     patch("kb_bootstrap.cli.append_gitignore_rules", side_effect=AssertionError("gitignore")), \
                     patch("kb_bootstrap.cli.shutil.copy2", side_effect=AssertionError("copy2")), \
                     patch("kb_bootstrap.cli.shutil.copytree", side_effect=AssertionError("copytree")), \
                     patch("pathlib.Path.touch", side_effect=AssertionError("touch")):
                    self.assertEqual(self.run_cli("--target", str(root)), 1)
                self.assertEqual(before, self.snapshot(root))

    def test_absent_ancillary_state_blocks_and_unrelated_files_survive_noop(self):
        for relative in ("kb/raw/.gitkeep", "kb/research/.gitkeep", "qmd/collections/wiki.yaml"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "consumer"
                self.assertIsNone(self.run_cli("--target", str(root)))
                path = root / relative
                path.unlink()
                before = self.snapshot(root)
                self.assertEqual(self.run_cli("--target", str(root)), 1)
                self.assertEqual(before, self.snapshot(root))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "consumer"
            self.assertIsNone(self.run_cli("--target", str(root)))
            (root / "AGENTS.md").write_text("consumer instructions\\n", encoding="utf-8")
            extra_skill = root / ".agents/skills/custom/SKILL.md"
            extra_skill.parent.mkdir()
            extra_skill.write_text("custom skill\\n", encoding="utf-8")
            source = self.package / "templates/skills/market-research/SKILL.md"
            nested = root / ".agents/skills/market-research/custom-extra.md"
            nested.write_bytes(source.read_bytes())
            before = self.snapshot(root)
            self.assertEqual(self.run_cli("--target", str(root)), 0)
            self.assertEqual(before, self.snapshot(root))

    def test_reparse_lesson_artifact_blocks_before_registry_read(self):
        from kb_bootstrap.project_lesson_enablement import inspect_project_lessons
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "consumer"
            self.assertIsNone(self.run_cli("--target", str(root), "--with-project-lessons"))
            module = __import__("kb_bootstrap.project_lesson_enablement", fromlist=["os"])
            real_lstat = module.os.lstat
            def reparse_lstat(path):
                details = real_lstat(path)
                if Path(path) == root / "kb/lessons":
                    from types import SimpleNamespace
                    details = SimpleNamespace(**{name: getattr(details, name) for name in dir(details)
                                                 if name.startswith("st_")})
                    details.st_file_attributes = 0x400
                return details
            with patch.object(module.os, "lstat", side_effect=reparse_lstat), \
                 patch("kb_bootstrap.project_lesson_enablement.validate_project_registry", side_effect=AssertionError("must not read")):
                state, _ = inspect_project_lessons(root, self.package, require_initialized=False)
            self.assertEqual(state, "blocked")

    def test_lesson_diagnostic_does_not_echo_malicious_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "consumer"
            self.assertIsNone(self.run_cli("--target", str(root), "--with-project-lessons"))
            secret = "PRIVATE-ID-DO-NOT-LEAK"
            index = root / "kb/lessons/index.yaml"
            index.write_text(f"version: 1\nscope: project\nid_prefix: PROJECT-\nlessons:\n  - id: {secret}\n    path: kb/lessons/PROJECT-0001-example.md\n", encoding="utf-8")
            with patch("sys.stdout", new_callable=__import__("io").StringIO) as output:
                self.assertEqual(self.run_cli("--target", str(root)), 1)
            self.assertNotIn(secret, output.getvalue())

    def test_first_init_copy_failure_is_sanitized_and_preserves_unrelated_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "consumer"
            root.mkdir()
            unrelated = root / "notes.txt"
            unrelated.write_bytes(b"consumer-owned\\n")
            with patch("kb_bootstrap.cli.shutil.copy2", side_effect=OSError("private path")):
                self.assertEqual(self.run_cli("--target", str(root)), 1)
            self.assertEqual(unrelated.read_bytes(), b"consumer-owned\\n")

    @contextlib.contextmanager
    def _junction_fixture(self):
        if os.name != "nt":
            self.skipTest("Windows junction behavior is Windows-only")
        base = Path(tempfile.mkdtemp(prefix="kb-bootstrap-junction-test-"))
        aliases = []
        try:
            yield base, aliases
        finally:
            unresolved = []
            for alias in aliases:
                try:
                    details = os.lstat(alias)
                except FileNotFoundError:
                    continue
                except OSError:
                    unresolved.append(alias)
                    continue
                if not (getattr(details, "st_file_attributes", 0) & 0x400):
                    unresolved.append(alias)
                    continue
                try:
                    os.rmdir(alias)  # Remove this junction only; never follow it.
                    if os.path.lexists(alias):
                        unresolved.append(alias)
                except OSError:
                    unresolved.append(alias)
            if unresolved:
                raise RuntimeError("junction cleanup could not prove aliases absent; owned temp tree preserved")
            shutil.rmtree(base)

    def _make_junction(self, link, target, aliases):
        aliases.append(link)  # Register before invoking mklink, including partial-failure cases.
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode:
            self.fail("mklink /J failed for invocation-owned temporary paths")
        details = os.lstat(link)
        if not (getattr(details, "st_file_attributes", 0) & 0x400):
            self.fail("mklink /J did not expose FILE_ATTRIBUTE_REPARSE_POINT")

    def test_junction_cleanup_failure_preserves_owned_tree(self):
        fixture = self._junction_fixture()
        base, aliases = fixture.__enter__()
        alias = base / "alias"
        alias.mkdir()
        aliases.append(alias)
        with patch("shutil.rmtree") as remove_tree:
            with patch("os.lstat", side_effect=PermissionError("injected")):
                with self.assertRaisesRegex(RuntimeError, "tree preserved"):
                    fixture.__exit__(None, None, None)
            remove_tree.assert_not_called()
            self.assertTrue(base.is_dir())
            self.assertTrue(alias.is_dir())
            alias.rmdir()
            shutil.rmtree(base)

    def test_windows_junction_target_root_blocks_without_target_mutation(self):
        with self._junction_fixture() as (base, aliases):
            foreign = base / "foreign"
            foreign.mkdir()
            sentinel = foreign / "sentinel.txt"
            sentinel.write_bytes(b"owned target sentinel")
            alias = base / "target-link"
            self._make_junction(alias, foreign, aliases)
            before = sentinel.read_bytes()
            real_lstat = os.lstat
            def guarded_lstat(path):
                if str(path).startswith(str(alias) + os.sep):
                    raise AssertionError("attempted inspect through target junction")
                return real_lstat(path)
            with patch("kb_bootstrap.scaffold_repeat.os.lstat", side_effect=guarded_lstat):
                action, report = preflight(alias, self.package, "single")
            self.assertEqual(action, "blocked")
            self.assertIn("BLOCKED", report)
            self.assertEqual(sentinel.read_bytes(), before)

    def test_windows_junction_managed_ancestor_blocks_without_external_reads(self):
        with self._junction_fixture() as (base, aliases):
            root = base / "consumer"
            root.mkdir()
            foreign = base / "foreign-skills"
            foreign.mkdir()
            sentinel = foreign / "sentinel.txt"
            sentinel.write_bytes(b"owned target sentinel")
            alias = root / ".agents"
            self._make_junction(alias, foreign, aliases)
            before = sentinel.read_bytes()
            real_open = os.open
            def guarded_open(path, *args, **kwargs):
                if str(path).startswith(str(alias)):
                    raise AssertionError("attempted read through managed junction")
                return real_open(path, *args, **kwargs)
            with patch("kb_bootstrap.scaffold_repeat.os.open", side_effect=guarded_open):
                action, report = preflight(root, self.package, "single")
            self.assertEqual(action, "blocked")
            self.assertIn("BLOCKED", report)
            self.assertEqual(sentinel.read_bytes(), before)

    def test_windows_junction_delegated_lesson_directory_blocks(self):
        from kb_bootstrap.project_lesson_enablement import inspect_project_lessons
        with self._junction_fixture() as (base, aliases):
            root = base / "consumer"
            self.assertIsNone(self.run_cli("--target", str(root), "--with-project-lessons"))
            foreign = base / "foreign-lessons"
            foreign.mkdir()
            sentinel = foreign / "sentinel.txt"
            sentinel.write_bytes(b"owned target sentinel")
            alias = root / "kb/lessons"
            for artifact in (alias / "SCHEMA.md", alias / "index.yaml"):
                artifact.unlink()
            alias.rmdir()
            self._make_junction(alias, foreign, aliases)
            real_lstat = os.lstat
            def guarded_lstat(path):
                if str(path).startswith(str(alias) + os.sep):
                    raise AssertionError("attempted inspect through delegated junction")
                return real_lstat(path)
            with patch("kb_bootstrap.project_lesson_enablement.os.lstat", side_effect=guarded_lstat), \
                 patch("kb_bootstrap.project_lesson_enablement.validate_project_registry", side_effect=AssertionError("must not read delegated junction")):
                state, errors = inspect_project_lessons(root, self.package, require_initialized=False)
            self.assertEqual(state, "blocked")
            self.assertTrue(errors)
            self.assertEqual(sentinel.read_bytes(), b"owned target sentinel")

    def test_target_with_parent_escape_or_symlink_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(preflight(root / ".." / "escape", self.package, "single")[0], "blocked")
            target = root / "linked"
            try:
                target.symlink_to(root, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlink unavailable")
            self.assertEqual(preflight(target, self.package, "single")[0], "blocked")


if __name__ == "__main__":
    unittest.main()
