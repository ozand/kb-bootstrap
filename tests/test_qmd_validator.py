import tempfile
import unittest
from pathlib import Path

from kb_bootstrap.qmd_validator import validate_qmd_collections
from kb_bootstrap.qmd_names import is_valid_generated_collection_name, project_slug


class QmdValidatorTests(unittest.TestCase):
    def test_generated_collection_name_contract(self):
        for basename in ("demo", "Пример проекта", "équipe", "A B", "A@B", "!!!", "", "a" * 100):
            base = project_slug(basename)
            for suffix in ("-wiki", "-raw"):
                name = base + suffix
                self.assertTrue(is_valid_generated_collection_name(name), name)
                self.assertLessEqual(len(name), 64)
        # Existing owner-authored names keep the legacy validator grammar and length behavior.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            collections = root / "qmd/collections"
            collections.mkdir(parents=True)
            (root / "kb").mkdir()
            for filename, custom_name in (("wiki.yaml", "Owner.Custom.Name"), ("raw.yaml", "a" * 70)):
                (collections / filename).write_text(
                    f"name: {custom_name}\npaths:\n  - ../../kb/\n", encoding="utf-8"
                )
            _, is_valid = validate_qmd_collections(root)
            self.assertTrue(is_valid)

    def test_valid_dual_collections_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "kb/raw").mkdir(parents=True)
            collections = root / "qmd/collections"
            collections.mkdir(parents=True)
            (collections / "wiki.yaml").write_text(
                'name: demo-wiki\npaths:\n  - ../../kb/\nexclude:\n  - "raw/**"\n',
                encoding="utf-8",
            )
            (collections / "raw.yaml").write_text(
                "name: demo-raw\npaths:\n  - ../../kb/raw/\n",
                encoding="utf-8",
            )

            report, is_valid = validate_qmd_collections(root)

            self.assertTrue(is_valid)
            self.assertIn("Collections: 2", report)
            self.assertIn("ERRORS: 0", report)

    def test_glob_in_collection_path_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            collections = root / "qmd/collections"
            collections.mkdir(parents=True)
            (collections / "glob.yaml").write_text(
                "name: demo-raw\npaths:\n  - ../../kb/raw/**\n", encoding="utf-8"
            )

            report, is_valid = validate_qmd_collections(root)

            self.assertFalse(is_valid)
            self.assertIn("glob patterns are not supported", report)

    def test_invalid_name_and_empty_paths_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            collections = root / "qmd/collections"
            collections.mkdir(parents=True)
            (collections / "bad.yaml").write_text(
                "name: bad name\npaths:\n", encoding="utf-8"
            )

            report, is_valid = validate_qmd_collections(root)

            self.assertFalse(is_valid)
            self.assertIn("missing or invalid name", report)
            self.assertIn("paths must contain at least one entry", report)


if __name__ == "__main__":
    unittest.main()
