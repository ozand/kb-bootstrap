import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from kb_bootstrap.cli import main
from kb_bootstrap.project_lesson_registry import validate_project_registry


def write_project_registry(root: Path, entries=None):
    lessons = root / "kb" / "lessons"
    lessons.mkdir(parents=True, exist_ok=True)
    (lessons / "SCHEMA.md").write_text("# Project-local lesson schema\n", encoding="utf-8")
    data = {
        "version": 1,
        "scope": "project",
        "id_prefix": "PROJECT-",
        "lessons": entries or [],
    }
    (lessons / "index.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False), encoding="utf-8"
    )
    return lessons


def write_lesson(root: Path, lesson_id="PROJECT-0001", filename=None, frontmatter_id=None):
    lessons = root / "kb" / "lessons"
    lessons.mkdir(parents=True, exist_ok=True)
    filename = filename or f"{lesson_id}-example.md"
    frontmatter_id = frontmatter_id or lesson_id
    path = lessons / filename
    path.write_text(
        f"---\nid: {frontmatter_id}\ntitle: Example\n---\n\n# Example\n",
        encoding="utf-8",
    )
    return path


class ProjectLessonRegistryTests(unittest.TestCase):
    def test_valid_project_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lesson_file = write_lesson(root)
            lessons = write_project_registry(
                root,
                [{"id": "PROJECT-0001", "path": "kb/lessons/" + lesson_file.name}],
            )

            errors, summary = validate_project_registry(lessons, root)

            self.assertEqual(errors, [])
            self.assertEqual(summary["files"], 1)
            self.assertEqual(summary["entries"], 1)

    def test_id_prefix_and_id_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lesson_file = write_lesson(root, lesson_id="OTHER-0001")
            lessons = write_project_registry(
                root,
                [{"id": "OTHER-0001", "path": "kb/lessons/" + lesson_file.name}],
            )

            errors, _ = validate_project_registry(lessons, root)

            self.assertTrue(any("invalid lesson ID" in error for error in errors))

    def test_path_filename_frontmatter_consistency(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lesson_file = write_lesson(
                root,
                lesson_id="PROJECT-0001",
                filename="PROJECT-0002-example.md",
                frontmatter_id="PROJECT-0001",
            )
            lessons = write_project_registry(
                root,
                [{"id": "PROJECT-0001", "path": "kb/lessons/" + lesson_file.name}],
            )

            errors, _ = validate_project_registry(lessons, root)

            self.assertIn(
                "project-local index ID/path mismatch: PROJECT-0001", errors
            )
            self.assertIn(
                "project-local lesson PROJECT-0002 filename/frontmatter ID mismatch",
                errors,
            )

    def test_malformed_frontmatter_closing_delimiter_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lesson_file = root / "kb" / "lessons" / "PROJECT-0001-example.md"
            lesson_file.parent.mkdir(parents=True)
            lesson_file.write_text(
                "---\nid: PROJECT-0001\n---oops\n\n# Malformed\n",
                encoding="utf-8",
            )
            lessons = write_project_registry(
                root,
                [{"id": "PROJECT-0001", "path": "kb/lessons/" + lesson_file.name}],
            )

            errors, _ = validate_project_registry(lessons, root)

            self.assertIn(
                "project-local lesson PROJECT-0001 filename/frontmatter ID mismatch",
                errors,
            )

    def test_schema_file_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lessons = write_project_registry(root)

            errors, summary = validate_project_registry(lessons, root)

            self.assertEqual(errors, [])
            self.assertEqual(summary["files"], 0)

    def test_path_outside_lessons_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lessons = write_project_registry(
                root,
                [{"id": "PROJECT-0001", "path": "docs/PROJECT-0001-example.md"}],
            )

            errors, _ = validate_project_registry(lessons, root)

            self.assertIn(
                "project-local index path is outside lessons directory: docs/PROJECT-0001-example.md",
                errors,
            )

    def test_custom_lessons_directory_is_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lessons = root / "knowledge" / "lessons"
            lessons.mkdir(parents=True)
            (lessons / "SCHEMA.md").write_text("# Schema\n", encoding="utf-8")
            lesson_file = lessons / "PROJECT-0001-example.md"
            lesson_file.write_text("---\nid: PROJECT-0001\n---\n", encoding="utf-8")
            (lessons / "index.yaml").write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "scope": "project",
                        "id_prefix": "PROJECT-",
                        "lessons": [
                            {"id": "PROJECT-0001", "path": "knowledge/lessons/PROJECT-0001-example.md"}
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            errors, summary = validate_project_registry(lessons, root)

            self.assertEqual(errors, [])
            self.assertEqual(summary["files"], 1)

    def test_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lessons = write_project_registry(
                root,
                [{"id": "PROJECT-0001", "path": "../outside.md"}],
            )

            errors, _ = validate_project_registry(lessons, root)

            self.assertIn(
                "project-local index path is outside lessons directory: ../outside.md",
                errors,
            )

    def test_symlink_lesson_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lessons = write_project_registry(root)
            target = root / "PROJECT-0001-target.md"
            target.write_text("---\nid: PROJECT-0001\n---\n", encoding="utf-8")
            link = lessons / "PROJECT-0001-example.md"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")
            (lessons / "index.yaml").write_text(
                yaml.safe_dump(
                    {
                        "version": 1,
                        "scope": "project",
                        "id_prefix": "PROJECT-",
                        "lessons": [
                            {"id": "PROJECT-0001", "path": "kb/lessons/PROJECT-0001-example.md"}
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            errors, _ = validate_project_registry(lessons, root)

            self.assertTrue(any("traverses a symlink" in error for error in errors))

    def test_symlink_contract_file_is_rejected(self):
        for name in ("index.yaml", "SCHEMA.md"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                lessons = write_project_registry(root)
                link = lessons / name
                link.unlink()
                target = root / f"external-{name}"
                if name == "index.yaml":
                    target.write_text(
                        yaml.safe_dump(
                            {
                                "version": 1,
                                "scope": "project",
                                "id_prefix": "PROJECT-",
                                "lessons": [],
                            },
                            sort_keys=False,
                        ),
                        encoding="utf-8",
                    )
                else:
                    target.write_text("# External schema\n", encoding="utf-8")
                try:
                    link.symlink_to(target)
                except (OSError, NotImplementedError):
                    self.skipTest("symlink creation is unavailable")

                errors, _ = validate_project_registry(lessons, root)

                self.assertIn(f"project-local {name} traverses a symlink", errors)

    def test_symlinked_lessons_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real-lessons"
            real.mkdir()
            link = root / "linked-lessons"
            try:
                link.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlink creation is unavailable")

            errors, _ = validate_project_registry(link, root)

            self.assertEqual(
                errors,
                ["project-local lessons directory traverses a symlink"],
            )

    def test_cli_help_names_project_local_schema(self):
        with patch("sys.argv", ["kb-bootstrap", "validate-project-lessons", "--help"]):
            with self.assertRaises(SystemExit) as raised:
                main()
            self.assertEqual(raised.exception.code, 0)

    def test_cli_validates_project_local_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lesson_file = write_lesson(root)
            write_project_registry(
                root,
                [{"id": "PROJECT-0001", "path": "kb/lessons/" + lesson_file.name}],
            )

            with patch("sys.argv", [
                "kb-bootstrap",
                "validate-project-lessons",
                "--root",
                str(root / "kb" / "lessons"),
                "--project-root",
                str(root),
            ]):
                self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
