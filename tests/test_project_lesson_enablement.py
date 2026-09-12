import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.cli import main
from kb_bootstrap.project_lesson_enablement import ARTIFACTS, enable_project_lessons
from kb_bootstrap.project_lesson_registry import validate_project_registry


def initialized_repository(root: Path) -> None:
    files = {
        "qmd.json": '{"custom": true}\n',
        "qmd/collections/wiki.yaml": "name: custom-wiki\n",
        "qmd/collections/raw.yaml": "name: custom-raw\n",
        ".agents/skills/kb-lookup/SKILL.md": "custom lookup instructions\n",
        ".agents/skills/qmd-operator/SKILL.md": "custom qmd instructions\n",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ProjectLessonEnablementTests(unittest.TestCase):
    def setUp(self):
        self.package_dir = Path(__file__).parents[1] / "kb_bootstrap"

    def test_enables_only_project_lesson_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialized_repository(root)
            before = {path: digest(root / path) for path in (
                "qmd.json",
                "qmd/collections/wiki.yaml",
                "qmd/collections/raw.yaml",
                ".agents/skills/kb-lookup/SKILL.md",
                ".agents/skills/qmd-operator/SKILL.md",
            )}

            report, valid = enable_project_lessons(root, self.package_dir)

            self.assertTrue(valid)
            self.assertIn("project lessons: enabled", report)
            self.assertEqual(
                {
                    path.relative_to(root).as_posix()
                    for path in root.rglob("*")
                    if path.is_file()
                }
                - set(before),
                set(ARTIFACTS),
            )
            self.assertEqual(before, {path: digest(root / path) for path in before})
            errors, summary = validate_project_registry(root / "kb/lessons", root)
            self.assertEqual(errors, [])
            self.assertEqual(summary["files"], 0)

    def test_complete_contract_is_idempotent_no_op(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialized_repository(root)
            first, first_valid = enable_project_lessons(root, self.package_dir)
            snapshot = {relative: (root / relative).read_bytes() for relative in ARTIFACTS}

            second, second_valid = enable_project_lessons(root, self.package_dir)
            third, third_valid = enable_project_lessons(root, self.package_dir)

            self.assertTrue(first_valid and second_valid and third_valid)
            self.assertIn("project lessons: enabled", first)
            self.assertEqual(second, third)
            self.assertIn("project lessons: already enabled", second)
            self.assertEqual(snapshot, {relative: (root / relative).read_bytes() for relative in ARTIFACTS})

    def test_complete_custom_contract_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialized_repository(root)
            enable_project_lessons(root, self.package_dir)
            stores = root / "lesson-stores.json"
            data = json.loads(stores.read_text(encoding="utf-8"))
            data["shared"] = {"path": "configured.json", "read_only": True}
            stores.write_text(json.dumps(data, indent=2), encoding="utf-8")
            skill = root / ".agents/skills/kb-capture/SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\nLocal note.\n", encoding="utf-8")
            lesson = root / "kb/lessons/PROJECT-0001-example.md"
            lesson.write_text("---\nid: PROJECT-0001\n---\n\n# Example\n", encoding="utf-8")
            index = root / "kb/lessons/index.yaml"
            index.write_text(
                "version: 1\nscope: project\nid_prefix: PROJECT-\nlessons:\n"
                "  - id: PROJECT-0001\n    path: kb/lessons/PROJECT-0001-example.md\n",
                encoding="utf-8",
            )
            snapshot = {path: path.read_bytes() for path in (stores, skill, lesson, index)}

            report, valid = enable_project_lessons(root, self.package_dir)

            self.assertTrue(valid)
            self.assertIn("already enabled", report)
            self.assertEqual(snapshot, {path: path.read_bytes() for path in snapshot})

    def test_partial_contract_blocks_without_writing(self):
        for existing in ARTIFACTS:
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                initialized_repository(root)
                path = root / existing
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("existing", encoding="utf-8")

                report, valid = enable_project_lessons(root, self.package_dir)

                self.assertFalse(valid)
                self.assertIn("partial or conflicting", report)
                self.assertEqual(path.read_text(encoding="utf-8"), "existing")
                self.assertEqual([item for item in ARTIFACTS if (root / item).exists()], [existing])

    def test_malformed_complete_contract_blocks_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialized_repository(root)
            enable_project_lessons(root, self.package_dir)
            stores = root / "lesson-stores.json"
            stores.write_text('{"capture_store":"shared"}', encoding="utf-8")
            snapshot = {relative: (root / relative).read_bytes() for relative in ARTIFACTS}

            report, valid = enable_project_lessons(root, self.package_dir)

            self.assertFalse(valid)
            self.assertIn("capture_store must be local", report)
            self.assertEqual(snapshot, {relative: (root / relative).read_bytes() for relative in ARTIFACTS})

    def test_malformed_shared_store_blocks(self):
        for shared in ({"read_only": True, "path": 123}, {"read_only": True, "path": "../shared.json"}):
            with self.subTest(shared=shared), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                initialized_repository(root)
                enable_project_lessons(root, self.package_dir)
                stores = root / "lesson-stores.json"
                data = json.loads(stores.read_text(encoding="utf-8"))
                data["shared"] = shared
                stores.write_text(json.dumps(data), encoding="utf-8")

                report, valid = enable_project_lessons(root, self.package_dir)

                self.assertFalse(valid)
                self.assertIn("lesson routing shared path", report)

    def test_writable_shared_store_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialized_repository(root)
            enable_project_lessons(root, self.package_dir)
            stores = root / "lesson-stores.json"
            data = json.loads(stores.read_text(encoding="utf-8"))
            data["shared"] = {"path": "shared.json", "read_only": False}
            stores.write_text(json.dumps(data), encoding="utf-8")

            report, valid = enable_project_lessons(root, self.package_dir)

            self.assertFalse(valid)
            self.assertIn("shared store must be explicitly read-only", report)

    def test_missing_initialized_marker_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialized_repository(root)
            (root / "qmd.json").unlink()

            report, valid = enable_project_lessons(root, self.package_dir)

            self.assertFalse(valid)
            self.assertIn("initialized marker is unavailable: qmd.json", report)
            self.assertFalse(any((root / path).exists() for path in ARTIFACTS))

    def test_symlinked_contract_path_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialized_repository(root)
            target = root / "external.json"
            target.write_text("{}", encoding="utf-8")
            link = root / "lesson-stores.json"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")

            report, valid = enable_project_lessons(root, self.package_dir)

            self.assertFalse(valid)
            self.assertIn("artifact path is unsafe: lesson-stores.json", report)
            self.assertEqual(target.read_text(encoding="utf-8"), "{}")

    def test_symlinked_parent_directory_blocks_without_external_write(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external_directory:
            root = Path(directory)
            external = Path(external_directory)
            initialized_repository(root)
            agents = root / ".agents"
            for child in sorted(agents.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            agents.rmdir()
            try:
                agents.symlink_to(external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlink creation is unavailable")

            report, valid = enable_project_lessons(root, self.package_dir)

            self.assertFalse(valid)
            self.assertIn("initialized marker is unavailable", report)
            self.assertEqual(list(external.rglob("*")), [])

    def test_atomic_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialized_repository(root)
            real_link = os.link
            calls = {"count": 0}

            def fail_second(source, destination):
                calls["count"] += 1
                if calls["count"] == 2:
                    raise OSError("injected")
                return real_link(source, destination)

            with patch("kb_bootstrap.project_lesson_enablement.os.link", side_effect=fail_second):
                report, valid = enable_project_lessons(root, self.package_dir)

            self.assertFalse(valid)
            self.assertIn("could not be installed", report)
            self.assertFalse(any((root / path).exists() for path in ARTIFACTS))
            self.assertEqual(list(root.rglob(".kb-bootstrap-enable-*.tmp")), [])

    def test_unsupported_exclusive_install_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialized_repository(root)
            with patch("kb_bootstrap.project_lesson_enablement.os.link", side_effect=OSError("unsupported")):
                report, valid = enable_project_lessons(root, self.package_dir)

            self.assertFalse(valid)
            self.assertIn("could not be installed", report)
            self.assertFalse(any((root / path).exists() for path in ARTIFACTS))
            self.assertEqual(list(root.rglob(".kb-bootstrap-enable-*.tmp")), [])

    def test_race_replacement_is_not_deleted_during_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialized_repository(root)
            real_link = os.link
            calls = {"count": 0}
            replaced = root / "kb/lessons/SCHEMA.md"

            def replace_first_then_fail(source, destination):
                calls["count"] += 1
                result = real_link(source, destination)
                if calls["count"] == 1:
                    destination = Path(destination)
                    destination.unlink()
                    destination.write_text("foreign replacement", encoding="utf-8")
                elif calls["count"] == 2:
                    raise OSError("injected")
                return result

            with patch("kb_bootstrap.project_lesson_enablement.os.link", side_effect=replace_first_then_fail):
                report, valid = enable_project_lessons(root, self.package_dir)

            self.assertFalse(valid)
            self.assertIn("cleanup is incomplete", report)
            self.assertEqual(replaced.read_text(encoding="utf-8"), "foreign replacement")

    def test_race_created_destination_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialized_repository(root)
            real_link = os.link
            calls = {"count": 0}
            raced = root / "lesson-stores.json"

            def create_destination_before_third(source, destination):
                calls["count"] += 1
                if calls["count"] == 3:
                    raced.write_text("race-owned", encoding="utf-8")
                return real_link(source, destination)

            with patch("kb_bootstrap.project_lesson_enablement.os.link", side_effect=create_destination_before_third):
                report, valid = enable_project_lessons(root, self.package_dir)

            self.assertFalse(valid)
            self.assertIn("could not be installed", report)
            self.assertEqual(raced.read_text(encoding="utf-8"), "race-owned")
            self.assertFalse((root / "kb/lessons/SCHEMA.md").exists())
            self.assertFalse((root / "kb/lessons/index.yaml").exists())
            self.assertFalse((root / ".agents/skills/kb-capture/SKILL.md").exists())

    def test_receipt_is_sanitized(self):
        with tempfile.TemporaryDirectory(prefix="private-target-") as directory:
            root = Path(directory)
            initialized_repository(root)

            report, valid = enable_project_lessons(root, self.package_dir)

            self.assertTrue(valid)
            self.assertNotIn(str(root), report)
            self.assertNotIn("private-target-", report)
            for relative in ARTIFACTS:
                self.assertIn(f"artifact: {relative}", report)

    def test_cli_enablement_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialized_repository(root)
            with patch("sys.argv", [
                "kb-bootstrap", "enable-project-lessons", "--target", str(root)
            ]):
                result = main()

            self.assertEqual(result, 0)
            self.assertTrue((root / "lesson-stores.json").is_file())


if __name__ == "__main__":
    unittest.main()
