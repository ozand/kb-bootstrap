import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.cli import main


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        with patch.object(sys, "argv", ["kb-bootstrap", *args]):
            return main()

    def test_single_generates_dual_collections_and_anchored_ignores(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            self.assertIsNone(self.run_cli("--target", directory, "--type", "single"))

            config = json.loads((root / "qmd.json").read_text(encoding="utf-8"))
            self.assertEqual(
                config["workspace"]["collections_dir"], "./qmd/collections"
            )
            self.assertTrue((root / "qmd/collections/wiki.yaml").is_file())
            self.assertTrue((root / "qmd/collections/raw.yaml").is_file())
            self.assertFalse((root / "qmd/collections/default.yaml").exists())

            wiki = (root / "qmd/collections/wiki.yaml").read_text(encoding="utf-8")
            raw = (root / "qmd/collections/raw.yaml").read_text(encoding="utf-8")
            self.assertIn("-wiki", wiki)
            self.assertIn('"raw/**"', wiki)
            self.assertIn("../../kb/raw/", raw)

            gitignore = (root / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("/models/", gitignore)
            self.assertIn("/kb/raw/**/*.bin", gitignore)
            self.assertNotIn("kb/raw/**/*.md", gitignore)
            self.assertNotIn("kb/models/", gitignore)

            self.run_cli("--target", directory, "--type", "single")
            updated_gitignore = (root / ".gitignore").read_text(encoding="utf-8")
            self.assertEqual(updated_gitignore.count("# kb-bootstrap generated artifacts"), 1)

    def test_umbrella_generates_dual_collections_with_existing_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            self.run_cli("--target", directory, "--type", "umbrella")

            self.assertTrue((root / "kb/raw").is_dir())
            self.assertTrue((root / "qmd/collections/wiki.yaml").is_file())
            self.assertTrue((root / "qmd/collections/raw.yaml").is_file())
            self.assertTrue((root / "qmd.json").is_file())

    def test_validate_combines_graph_and_qmd_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_cli("--target", directory, "--type", "single")
            (root / "kb/index.md").write_text("# Index\n", encoding="utf-8")

            result = self.run_cli(
                "validate",
                "--dir",
                str(root / "kb"),
                "--project-root",
                directory,
            )

            self.assertEqual(result, 0)

    def test_validate_fails_when_collection_path_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_cli("--target", directory, "--type", "single")
            (root / "kb/index.md").write_text("# Index\n", encoding="utf-8")
            (root / "qmd/collections/raw.yaml").write_text(
                "name: project-raw\npaths:\n  - ../../missing/\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "validate",
                "--dir",
                str(root / "kb"),
                "--project-root",
                directory,
            )

            self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
