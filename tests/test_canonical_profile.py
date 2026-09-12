import datetime
import tempfile
import unittest
from pathlib import Path

import yaml

from kb_bootstrap.canonical_profile import validate_canonical_profile


class CanonicalProfileTests(unittest.TestCase):
    def test_profile_loader_does_not_mutate_global_safe_loader(self):
        parsed = yaml.safe_load("flag: true\ncount: 4\nwhen: 2026-09-12\n")

        self.assertIs(parsed["flag"], True)
        self.assertEqual(parsed["count"], 4)
        self.assertEqual(parsed["when"], datetime.date(2026, 9, 12))

    def write(self, root: Path, relative: str, content: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_valid_minimal_and_unknown_metadata_pass_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concept = self.write(
                root,
                "architecture.md",
                "---\ntype: Custom Architecture\nowner_team: platform\n---\n\n# Architecture\n",
            )
            original = concept.read_bytes()

            first, first_valid = validate_canonical_profile(root)
            second, second_valid = validate_canonical_profile(root)

            self.assertTrue(first_valid and second_valid)
            self.assertEqual(first, second)
            self.assertIn("Concept files: 1", first)
            self.assertIn("unknown types and additional metadata are accepted", first)
            self.assertEqual(concept.read_bytes(), original)

    def test_missing_empty_or_non_string_type_fails(self):
        fixtures = (
            "---\ntitle: Missing\n---\n",
            "---\ntype: '   '\n---\n",
            "---\ntype: [Concept]\n---\n",
        )
        for content in fixtures:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.write(root, "invalid.md", content)

                report, valid = validate_canonical_profile(root)

                self.assertFalse(valid)
                self.assertIn("type must be a non-empty string", report)

    def test_malformed_frontmatter_fails_deterministically(self):
        fixtures = (
            "# No frontmatter\n",
            "---\ntype: Concept\n---oops\n",
            "---\ntype: [broken\n---\n",
            "---\n- type\n---\n",
        )
        for content in fixtures:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.write(root, "invalid.md", content)

                first, first_valid = validate_canonical_profile(root)
                second, second_valid = validate_canonical_profile(root)

                self.assertFalse(first_valid or second_valid)
                self.assertEqual(first, second)
                self.assertIn("invalid.md", first)

    def test_yaml_scalars_remain_strings_for_profile_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concept = self.write(
                root,
                "scalars.md",
                "---\ntype: Concept\ntitle: 2026-09-12\ndescription: true\ntags: [true, no, 2026-09-12, 42]\nstatus: stable\n---\n",
            )
            original = concept.read_bytes()

            report, valid = validate_canonical_profile(root)

            self.assertTrue(valid)
            self.assertIn("ERRORS: 0", report)
            self.assertEqual(concept.read_bytes(), original)

    def test_generated_optional_fields_are_validated(self):
        invalid = {
            "title": "---\ntype: Concept\ntitle: [wrong]\n---\n",
            "description": "---\ntype: Concept\ndescription: [wrong]\n---\n",
            "tags": "---\ntype: Concept\ntags: [valid, [wrong]]\n---\n",
            "status-active": "---\ntype: Concept\nstatus: active\n---\n",
            "status-list": "---\ntype: Concept\nstatus: [stable]\n---\n",
            "status-map": "---\ntype: Concept\nstatus: {value: stable}\n---\n",
            "title-null": "---\ntype: Concept\ntitle: null\n---\n",
            "description-null": "---\ntype: Concept\ndescription: null\n---\n",
            "tags-null": "---\ntype: Concept\ntags: null\n---\n",
            "status-null": "---\ntype: Concept\nstatus: null\n---\n",
            "status-number": "---\ntype: Concept\nstatus: 1\n---\n",
        }
        for field, content in invalid.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.write(root, "invalid.md", content)

                report, valid = validate_canonical_profile(root)

                self.assertFalse(valid)
                self.assertIn(field.split("-", 1)[0], report)

    def test_reserved_raw_and_lesson_files_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "index.md", "# Index without frontmatter\n")
            self.write(root, "log.md", "# Log without frontmatter\n")
            self.write(root, "raw/source.md", "# Raw without frontmatter\n")
            self.write(root, "Raw/source.md", "# Raw with different case\n")
            self.write(root, "lessons/PROJECT-0001-example.md", "# Separate lesson\n")
            self.write(root, "Lessons/PROJECT-0002-example.md", "# Different case lesson\n")
            self.write(root, "nested/index.md", "# Nested reserved index\n")
            self.write(root, "nested/log.md", "# Nested reserved log\n")
            self.write(root, "nested/INDEX.MD", "# Case-insensitive reserved index\n")
            self.write(root, "nested/Log.Md", "# Case-insensitive reserved log\n")
            self.write(root, "valid.md", "---\ntype: Concept\n---\n")

            report, valid = validate_canonical_profile(root)

            self.assertTrue(valid)
            self.assertIn("Concept files: 1", report)
            self.assertIn("Reserved/index files: excluded", report)
            self.assertIn("Raw and lesson directories: excluded", report)

    def test_symlinked_excluded_directory_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside_directory:
            root = Path(directory)
            outside = Path(outside_directory)
            linked_raw = root / "raw"
            try:
                linked_raw.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlink creation is unavailable")

            report, valid = validate_canonical_profile(root)

            self.assertFalse(valid)
            self.assertIn("raw: symlinked directory is not allowed", report)
            self.assertNotIn(str(outside), report)

    def test_symlinked_file_directory_and_root_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside_directory:
            root = Path(directory)
            outside = Path(outside_directory)
            outside_file = outside / "outside.md"
            outside_file.write_text("---\ntype: External\n---\n", encoding="utf-8")
            linked_file = root / "linked.md"
            linked_directory = root / "linked-dir"
            linked_root = root / "linked-root"
            try:
                linked_file.symlink_to(outside_file)
                linked_directory.symlink_to(outside, target_is_directory=True)
                linked_root.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")

            report, valid = validate_canonical_profile(root)
            root_report, root_valid = validate_canonical_profile(linked_root)

            self.assertFalse(valid)
            self.assertIn("linked.md: symlinked file is not allowed", report)
            self.assertIn("linked-dir: symlinked directory is not allowed", report)
            self.assertNotIn(str(outside), report)
            self.assertFalse(root_valid)
            self.assertIn("canonical root traverses a symlink", root_report)
            self.assertNotIn(str(outside), root_report)

    def test_unavailable_root_fails_without_exposing_absolute_path(self):
        with tempfile.TemporaryDirectory(prefix="private-profile-") as directory:
            root = Path(directory) / "missing"

            report, valid = validate_canonical_profile(root)

            self.assertFalse(valid)
            self.assertIn("canonical root is unavailable", report)
            self.assertNotIn(str(root), report)
            self.assertNotIn("private-profile-", report)


if __name__ == "__main__":
    unittest.main()
