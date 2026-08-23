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
            self.assertTrue((root / "kb/raw/.gitkeep").is_file())
            self.assertEqual((root / "kb/raw/.gitkeep").read_text(encoding="utf-8"), "")

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
            self.assertTrue((root / "kb/raw/.gitkeep").is_file())
            self.assertTrue((root / "qmd/collections/wiki.yaml").is_file())
            self.assertTrue((root / "qmd/collections/raw.yaml").is_file())
            self.assertTrue((root / "qmd.json").is_file())

    def test_default_generation_does_not_create_project_lessons_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            self.run_cli("--target", directory, "--type", "single")

            self.assertFalse((root / "kb/lessons").exists())
            self.assertFalse((root / "lesson-stores.json").exists())
            self.assertFalse((root / ".agents/skills/kb-capture").exists())
            self.assertTrue((root / ".agents/skills/kb-lookup/SKILL.md").is_file())

    def test_opt_in_generation_creates_project_lessons_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            self.run_cli(
                "--target",
                directory,
                "--type",
                "single",
                "--with-project-lessons",
            )

            stores = json.loads((root / "lesson-stores.json").read_text(encoding="utf-8"))
            self.assertEqual(stores["capture_store"], "local")
            self.assertEqual(stores["local"]["path"], "kb/lessons")
            self.assertNotIn("shared", stores)
            self.assertTrue((root / "qmd/collections/wiki.yaml").is_file())
            self.assertTrue((root / "qmd/collections/raw.yaml").is_file())
            self.assertTrue((root / "kb/raw/.gitkeep").is_file())
            self.assertTrue((root / ".agents/skills/kb-capture/SKILL.md").is_file())

            index = (root / "kb/lessons/index.yaml").read_text(encoding="utf-8")
            schema = (root / "kb/lessons/SCHEMA.md").read_text(encoding="utf-8")
            self.assertIn("id_prefix: PROJECT-", index)
            self.assertIn("lessons: []", index)
            self.assertIn("PROJECT-0001", schema)

    def test_opt_in_rerun_preserves_existing_lesson_data_and_routing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            self.run_cli("--target", directory, "--with-project-lessons")
            index = root / "kb/lessons/index.yaml"
            stores = root / "lesson-stores.json"
            index.write_text("version: 1\nid_prefix: PROJECT-\nlessons:\n  - id: PROJECT-0001\n", encoding="utf-8")
            stores.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "capture_store": "local",
                        "local": {"path": "kb/lessons"},
                        "shared": {"path": "configured-shared", "read_only": True},
                    }
                ),
                encoding="utf-8",
            )

            self.run_cli("--target", directory, "--with-project-lessons")

            self.assertIn("PROJECT-0001", index.read_text(encoding="utf-8"))
            updated_stores = json.loads(stores.read_text(encoding="utf-8"))
            self.assertEqual(updated_stores["shared"]["path"], "configured-shared")
            self.assertTrue(updated_stores["shared"]["read_only"])

    def test_generated_lesson_skills_fail_closed_and_use_local_first_lookup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            self.run_cli("--target", directory, "--with-project-lessons")

            capture = (root / ".agents/skills/kb-capture/SKILL.md").read_text(
                encoding="utf-8"
            )
            lookup = (root / ".agents/skills/kb-lookup/SKILL.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("resolve exactly one configured store", capture)
            self.assertIn("Stop without writing", capture)
            self.assertIn("Never infer a workspace path", capture)
            self.assertIn("all three contract items exist", capture)
            self.assertIn("local lesson contract unavailable", capture)
            self.assertIn("search its `index.yaml` first", lookup)
            self.assertIn("search its `index.yaml` second", lookup)
            self.assertIn("no lesson stores configured", lookup)
            self.assertIn("does not imply that a local lesson store exists", lookup)
            self.assertIn("read_only", lookup)
            self.assertIn("Lookup never writes", lookup)
            self.assertNotIn("T:\\Code", capture)
            self.assertNotIn("T:\\Code", lookup)

    def test_search_command_defaults_to_canonical_mode(self):
        with patch(
            "kb_bootstrap.cli.search_qmd", return_value=("RESULT: OK", True)
        ) as search:
            result = self.run_cli(
                "search", "setup", "--project-root", ".", "--limit", "3"
            )

        self.assertEqual(result, 0)
        search.assert_called_once_with("setup", "canonical", Path("."), 3)

    def test_search_command_accepts_explicit_raw_mode(self):
        with patch(
            "kb_bootstrap.cli.search_qmd", return_value=("RESULT: OK", True)
        ) as search:
            result = self.run_cli(
                "search", "trace", "--mode", "raw", "--project-root", "."
            )

        self.assertEqual(result, 0)
        search.assert_called_once_with("trace", "raw", Path("."), 5)

    def test_lesson_cache_requires_explicit_lessons(self):
        with patch(
            "kb_bootstrap.cli.sync_cache", return_value=("RESULT: OK", True)
        ) as sync:
            result = self.run_cli(
                "lesson-cache",
                "--source", "source.json",
                "--cache", "cache.json",
                "--lesson", "KB-0001",
                "--prune",
            )

        self.assertEqual(result, 0)
        sync.assert_called_once_with(
            Path("source.json"), Path("cache.json"), ["KB-0001"], True
        )

    def test_lesson_cache_check_is_read_only(self):
        with patch(
            "kb_bootstrap.cli.check_cache", return_value=("RESULT: OK", True)
        ) as check:
            result = self.run_cli(
                "lesson-cache",
                "--source", "source.json",
                "--cache", "cache.json",
                "--lesson", "KB-0001",
                "--check",
            )

        self.assertEqual(result, 0)
        check.assert_called_once_with(
            Path("source.json"), Path("cache.json"), ["KB-0001"]
        )

    def test_prepare_shared_candidate_command_is_local_only(self):
        with patch(
            "kb_bootstrap.cli.prepare_candidate", return_value=("RESULT: OK", True)
        ) as prepare:
            result = self.run_cli(
                "prepare-shared-candidate",
                "--input",
                "input.json",
                "--output",
                "candidate.json",
            )

        self.assertEqual(result, 0)
        prepare.assert_called_once_with(Path("input.json"), Path("candidate.json"))

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
