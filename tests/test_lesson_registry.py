import tempfile
import unittest
from pathlib import Path

import yaml

from kb_bootstrap.lesson_registry import next_id, validate_registry


def lesson(path: Path, lesson_id: str, filename_id: str = None):
    filename_id = filename_id or lesson_id
    file = path / "lessons" / f"{filename_id}-example.md"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(f"---\nid: {lesson_id}\ntitle: Example\n---\n\n# Example\n", encoding="utf-8")
    return file


def write_index(path: Path, entries, count=None):
    data = {"version": 1, "count": len(entries) if count is None else count, "lessons": entries}
    (path / "index.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


class LessonRegistryTests(unittest.TestCase):
    def test_valid_registry_and_next_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = lesson(root, "KB-0001")
            write_index(root, [{"id": "KB-0001", "file": f"lessons/{file.name}"}])

            errors, summary = validate_registry(root)
            allocated, allocation_errors = next_id(root)

            self.assertEqual(errors, [])
            self.assertEqual(summary["files"], 1)
            self.assertEqual(allocated, "KB-0002")
            self.assertEqual(allocation_errors, [])

    def test_duplicate_id_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = lesson(root, "KB-0001")
            write_index(
                root,
                [
                    {"id": "KB-0001", "file": f"lessons/{file.name}"},
                    {"id": "KB-0001", "file": "lessons/KB-0001-other.md"},
                ],
            )
            errors, _ = validate_registry(root)
            self.assertIn("duplicate lesson ID: KB-0001", errors)

    def test_duplicate_malformed_file_reference_blocks_without_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lessons").mkdir(parents=True)
            write_index(
                root,
                [
                    {"id": "KB-0001", "file": "lessons/invalid.md"},
                    {"id": "KB-0002", "file": "lessons/invalid.md"},
                ],
            )
            errors, _ = validate_registry(root)
            self.assertIn("duplicate lesson file entry for ID: unknown", errors)

    def test_filename_frontmatter_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = lesson(root, "KB-0002", filename_id="KB-0001")
            write_index(root, [{"id": "KB-0001", "file": f"lessons/{file.name}"}])
            errors, _ = validate_registry(root)
            self.assertIn("lesson KB-0001 filename/frontmatter ID mismatch", errors)

    def test_missing_and_extra_index_entries_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lesson(root, "KB-0001")
            write_index(root, [{"id": "KB-0002", "file": "lessons/KB-0002-missing.md"}])
            errors, _ = validate_registry(root)
            self.assertIn("lesson missing from index: KB-0001", errors)
            self.assertIn("index references missing lesson: KB-0002", errors)

    def test_crossed_index_id_file_pairs_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = lesson(root, "KB-0001")
            second = lesson(root, "KB-0002")
            write_index(
                root,
                [
                    {"id": "KB-0001", "file": f"lessons/{second.name}"},
                    {"id": "KB-0002", "file": f"lessons/{first.name}"},
                ],
            )
            errors, _ = validate_registry(root)
            self.assertIn("index ID/file mismatch: KB-0001", errors)
            self.assertIn("index ID/file mismatch: KB-0002", errors)

    def test_count_drift_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = lesson(root, "KB-0001")
            write_index(root, [{"id": "KB-0001", "file": f"lessons/{file.name}"}], count=2)
            errors, _ = validate_registry(root)
            self.assertTrue(any(error.startswith("index count drift:") for error in errors))

    def test_allocation_fails_closed_on_ambiguous_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = lesson(root, "KB-0001")
            write_index(
                root,
                [
                    {"id": "KB-0001", "file": f"lessons/{file.name}"},
                    {"id": "KB-0001", "file": "lessons/KB-0001-other.md"},
                ],
            )
            allocated, errors = next_id(root)
            self.assertIsNone(allocated)
            self.assertIn("duplicate lesson ID: KB-0001", errors)


if __name__ == "__main__":
    unittest.main()
