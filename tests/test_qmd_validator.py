import tempfile
import unittest
from pathlib import Path

from kb_bootstrap.qmd_validator import validate_qmd_collections


class QmdValidatorTests(unittest.TestCase):
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
