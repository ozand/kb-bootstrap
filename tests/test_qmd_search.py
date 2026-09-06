import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.qmd_search import search_qmd


class QmdSearchTests(unittest.TestCase):
    def make_project(self, directory: str, raw: bool = True, duplicate_raw: bool = False):
        root = Path(directory)
        (root / "kb/raw").mkdir(parents=True)
        collections = root / "qmd/collections"
        collections.mkdir(parents=True)
        (collections / "wiki.yaml").write_text(
            "name: demo-wiki\npaths:\n  - ../../kb/\n", encoding="utf-8"
        )
        if raw:
            (collections / "raw.yaml").write_text(
                "name: demo-raw\npaths:\n  - ../../kb/raw/\n", encoding="utf-8"
            )
        if duplicate_raw:
            (collections / "other-raw.yaml").write_text(
                "name: other-raw\npaths:\n  - ../../kb/raw/\n", encoding="utf-8"
            )
        return root

    def test_canonical_is_default_and_uses_wiki_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_project(directory)
            result = [{"title": "Guide", "file": "qmd://demo-wiki/guide.md", "score": 0.9}]
            with patch(
                "kb_bootstrap.qmd_search._run",
                return_value=(json.dumps(result), True),
            ) as run:
                report, valid = search_qmd("setup", project_root=root)

            self.assertTrue(valid)
            self.assertIn("mode: canonical", report)
            self.assertIn("[CANONICAL] Guide", report)
            self.assertIn("collection=demo-wiki", report)
            command = run.call_args.args[0]
            self.assertEqual(command[:4], ["qmd", "search", "-c", "demo-wiki"])
            self.assertEqual(command[-2:], ["--", "setup"])

    def test_raw_mode_is_explicit_and_labels_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_project(directory)
            result = [{"title": "Capture", "file": "qmd://demo-raw/capture.md", "score": 0.8}]
            with patch(
                "kb_bootstrap.qmd_search._run",
                return_value=(json.dumps(result), True),
            ) as run:
                report, valid = search_qmd("trace", mode="raw", project_root=root)

            self.assertTrue(valid)
            self.assertIn("mode: raw", report)
            self.assertIn("[RAW] Capture", report)
            self.assertIn("provenance: collection=demo-raw; source=qmd://demo-raw/capture.md", report)
            command = run.call_args.args[0]
            self.assertEqual(command[:4], ["qmd", "search", "-c", "demo-raw"])
            self.assertEqual(command[-2:], ["--", "trace"])

    def test_absolute_result_path_is_not_disclosed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_project(directory)
            result = [{"title": "Capture", "file": "C:/private/work/capture.md", "score": 0.8}]
            with patch(
                "kb_bootstrap.qmd_search._run",
                return_value=(json.dumps(result), True),
            ):
                report, valid = search_qmd("trace", mode="raw", project_root=root)

            self.assertTrue(valid)
            self.assertIn("source=unavailable", report)
            self.assertNotIn("C:/private", report)

    def test_missing_or_ambiguous_raw_collection_blocks_without_qmd_call(self):
        for raw, duplicate in [(False, False), (True, True)]:
            with self.subTest(raw=raw, duplicate=duplicate), tempfile.TemporaryDirectory() as directory:
                root = self.make_project(directory, raw=raw, duplicate_raw=duplicate)
                with patch("kb_bootstrap.qmd_search._run") as run:
                    report, valid = search_qmd("trace", mode="raw", project_root=root)

                self.assertFalse(valid)
                self.assertIn("raw collection is missing or ambiguous", report)
                self.assertIn("RESULT: BLOCKED", report)
                run.assert_not_called()

    def test_hyphen_prefixed_query_is_passed_after_option_terminator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_project(directory)
            with patch(
                "kb_bootstrap.qmd_search._run", return_value=("[]", True)
            ) as run:
                _, valid = search_qmd("--index other", mode="raw", project_root=root)

            self.assertTrue(valid)
            self.assertEqual(run.call_args.args[0][-2:], ["--", "--index other"])

    def test_missing_qmd_executable_blocks_without_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_project(directory)
            with patch("kb_bootstrap.qmd_search.shutil.which", return_value=None):
                report, valid = search_qmd("anything", project_root=root)

            self.assertFalse(valid)
            self.assertIn("QMD search is unavailable", report)
            self.assertIn("RESULT: BLOCKED", report)

    def test_resolves_windows_executable_path_without_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_project(directory)
            result = [{"title": "Guide", "file": "qmd://demo-wiki/guide.md", "score": 0.9}]
            windows_qmd = r"C:\\Program Files\\QMD\\qmd.cmd"
            with patch("kb_bootstrap.qmd_search.shutil.which", return_value=windows_qmd), patch(
                "kb_bootstrap.qmd_search.subprocess.run",
                return_value=type("Result", (), {"stdout": json.dumps(result), "returncode": 0})(),
            ) as run:
                report, valid = search_qmd("setup", project_root=root)

            self.assertTrue(valid)
            self.assertIn("[CANONICAL] Guide", report)
            command = run.call_args.args[0]
            self.assertEqual(command[0], windows_qmd)
            self.assertEqual(command[-2:], ["--", "setup"])
            self.assertFalse(run.call_args.kwargs.get("shell", False))

    def test_search_wrapper_uses_only_read_only_qmd_search_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_project(directory)
            with patch(
                "kb_bootstrap.qmd_search._run", return_value=("[]", True)
            ) as run:
                _, valid = search_qmd("anything", mode="raw", project_root=root)

            self.assertTrue(valid)
            command = run.call_args.args[0]
            self.assertEqual(command[0:2], ["qmd", "search"])
            self.assertNotIn("update", command)
            self.assertNotIn("embed", command)
            self.assertNotIn("collection", command)

    # The three faults that "QMD search is unavailable" used to hide behind one
    # word. Each must stay distinguishable from the report alone.

    def test_missing_executable_diagnostic_names_the_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_project(directory)
            with patch("kb_bootstrap.qmd_search.shutil.which", return_value=None):
                report, valid = search_qmd("anything", project_root=root)

            self.assertFalse(valid)
            self.assertIn("QMD search is unavailable: qmd executable not found on PATH", report)

    def test_unregistered_collection_diagnostic_is_qmd_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_project(directory)
            failed = type(
                "Result", (), {"stdout": "", "stderr": "Collection not found: demo-wiki\n", "returncode": 1}
            )()
            with patch("kb_bootstrap.qmd_search.shutil.which", return_value="/usr/bin/qmd"), patch(
                "kb_bootstrap.qmd_search.subprocess.run", return_value=failed
            ):
                report, valid = search_qmd("anything", project_root=root)

            self.assertFalse(valid)
            self.assertIn("QMD search is unavailable: Collection not found: demo-wiki", report)
            self.assertIn("RESULT: BLOCKED", report)

    def test_nonzero_exit_without_output_reports_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_project(directory)
            failed = type("Result", (), {"stdout": "", "stderr": "", "returncode": 3})()
            with patch("kb_bootstrap.qmd_search.shutil.which", return_value="/usr/bin/qmd"), patch(
                "kb_bootstrap.qmd_search.subprocess.run", return_value=failed
            ):
                report, valid = search_qmd("anything", project_root=root)

            self.assertFalse(valid)
            self.assertIn("QMD search is unavailable: qmd exited 3", report)

    def test_diagnostic_is_one_line_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_project(directory)
            failed = type(
                "Result", (), {"stdout": "", "stderr": ("x" * 500) + "\nsecond line\n", "returncode": 1}
            )()
            with patch("kb_bootstrap.qmd_search.shutil.which", return_value="/usr/bin/qmd"), patch(
                "kb_bootstrap.qmd_search.subprocess.run", return_value=failed
            ):
                report, _ = search_qmd("anything", project_root=root)

            error_line = next(line for line in report.splitlines() if "QMD search is unavailable" in line)
            self.assertNotIn("second line", report)
            self.assertLessEqual(len(error_line), len("  - QMD search is unavailable: ") + 200)

    def test_success_path_and_legacy_two_tuple_patches_are_unchanged(self):
        # Callers and tests that patch _run with a bare ("", False) still get
        # the stable phrase with no dangling separator.
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_project(directory)
            with patch("kb_bootstrap.qmd_search._run", return_value=("", False)):
                report, valid = search_qmd("anything", project_root=root)

            self.assertFalse(valid)
            self.assertIn("  - QMD search is unavailable\n", report + "\n")
            self.assertNotIn("unavailable:", report)


if __name__ == "__main__":
    unittest.main()
