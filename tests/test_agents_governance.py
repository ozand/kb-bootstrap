import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kb_bootstrap.agents_governance as MODULE
from kb_bootstrap.agents_governance import (
    END_MARKER,
    START_MARKER,
    update_agents_file,
)


class AgentsGovernanceTests(unittest.TestCase):
    def test_creates_new_agents_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "AGENTS.md"
            report, valid = update_agents_file("AGENTS.md", "example/project", root)
            content = path.read_text(encoding="utf-8")

        self.assertTrue(valid)
        self.assertIn("updated", report)
        self.assertNotIn(str(root), report)
        self.assertEqual(content.count(START_MARKER), 1)
        self.assertEqual(content.count(END_MARKER), 1)
        self.assertIn("Expected repository: `example/project`", content)

    def test_append_and_update_preserve_surrounding_bytes_and_mode(self):
        prefix = b"# Local instructions\r\n\r\nKeep this text.\r\n"
        suffix = b"\r\n# Local footer\r\nDo not change.\r\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "AGENTS.md"
            path.write_bytes(prefix)
            path.chmod(0o640)
            _, valid = update_agents_file("AGENTS.md", "example/first", root)
            first = path.read_bytes()
            path.write_bytes(first + suffix)

            _, valid = update_agents_file("AGENTS.md", "example/second", root)
            updated = path.read_bytes()
            mode = stat.S_IMODE(path.stat().st_mode)

        self.assertTrue(valid)
        self.assertTrue(updated.startswith(prefix))
        self.assertTrue(updated.endswith(suffix))
        self.assertIn(b"example/second", updated)
        self.assertNotIn(b"example/first", updated)
        self.assertEqual(updated.count(START_MARKER.encode()), 1)
        if os.name != "nt":
            self.assertEqual(mode, 0o640)

    def test_repeated_update_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "AGENTS.md"
            update_agents_file("AGENTS.md", "example/project", root)
            first = path.read_bytes()
            report, valid = update_agents_file("AGENTS.md", "example/project", root)
            second = path.read_bytes()

        self.assertTrue(valid)
        self.assertIn("already current", report)
        self.assertEqual(first, second)

    def test_malformed_or_duplicate_markers_block_without_writing(self):
        cases = [
            f"before\n{START_MARKER}\nmissing end\n",
            f"{END_MARKER}\ntext\n{START_MARKER}\n",
            f"{START_MARKER}\na\n{END_MARKER}\n{START_MARKER}\nb\n{END_MARKER}\n",
        ]
        for content in cases:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / "AGENTS.md"
                path.write_text(content, encoding="utf-8")
                before = path.read_bytes()
                report, valid = update_agents_file("AGENTS.md", "example/project", root)

                self.assertFalse(valid)
                self.assertIn("malformed or conflicting", report)
                self.assertEqual(before, path.read_bytes())

    def test_absolute_escape_nul_missing_parent_and_unavailable_root_block(self):
        with tempfile.TemporaryDirectory(prefix="private-root-") as directory:
            root = Path(directory)
            cases = (
                (str(root / "AGENTS.md"), root),
                ("../AGENTS.md", root),
                ("bad\x00name", root),
                ("missing/AGENTS.md", root),
                ("AGENTS.md", root / "missing-root"),
            )
            for file_path, project_root in cases:
                with self.subTest(file_path=file_path):
                    report, valid = update_agents_file(
                        file_path, "example/project", project_root
                    )
                    self.assertFalse(valid)
                    self.assertIn("RESULT: BLOCKED", report)
                    self.assertNotIn(str(root), report)
                    self.assertNotIn("private-root-", report)
            self.assertFalse((root / "AGENTS.md").exists())

    def test_symlinked_root_parent_and_target_block_without_external_write(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external_directory:
            root = Path(directory)
            external = Path(external_directory)
            target = root / "AGENTS.md"
            external_file = external / "external.md"
            external_file.write_text("outside", encoding="utf-8")
            try:
                target.symlink_to(external_file)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")

            target_report, target_valid = update_agents_file(
                "AGENTS.md", "example/project", root
            )
            target.unlink()
            parent = root / "nested"
            parent.symlink_to(external, target_is_directory=True)
            parent_report, parent_valid = update_agents_file(
                "nested/AGENTS.md", "example/project", root
            )
            root_link = root / "root-link"
            root_link.symlink_to(external, target_is_directory=True)
            root_report, root_valid = update_agents_file(
                "AGENTS.md", "example/project", root_link
            )

            self.assertFalse(target_valid or parent_valid or root_valid)
            self.assertIn("symlink", target_report)
            self.assertIn("symlink", parent_report)
            self.assertIn("symlink", root_report)
            self.assertEqual(external_file.read_text(encoding="utf-8"), "outside")
            self.assertFalse((external / "AGENTS.md").exists())

    def test_concurrent_modification_blocks_and_preserves_foreign_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "AGENTS.md"
            path.write_text("# Original\n", encoding="utf-8")
            real_source_matches = MODULE._source_matches

            def modify_then_compare(target, observation):
                target.write_text("# Foreign edit\n", encoding="utf-8")
                return real_source_matches(target, observation)

            with patch.object(MODULE, "_source_matches", side_effect=modify_then_compare):
                report, valid = update_agents_file(
                    "AGENTS.md", "example/project", root
                )

            self.assertFalse(valid)
            self.assertIn("changed before replacement", report)
            self.assertEqual(path.read_text(encoding="utf-8"), "# Foreign edit\n")
            self.assertEqual(list(root.glob(".kb-bootstrap-agents-*.tmp")), [])

    def test_atomic_write_failure_preserves_existing_file_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "AGENTS.md"
            path.write_text("# Original\n", encoding="utf-8")
            original = path.read_bytes()

            with patch.object(MODULE.os, "replace", side_effect=OSError("injected")):
                report, valid = update_agents_file(
                    "AGENTS.md", "example/project", root
                )

            self.assertFalse(valid)
            self.assertIn("cannot be updated atomically", report)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(root.glob(".kb-bootstrap-agents-*.tmp")), [])

    def test_partial_stage_write_failure_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "AGENTS.md"
            path.write_text("# Original\n", encoding="utf-8")
            original = path.read_bytes()

            with patch.object(MODULE, "_write_staged", side_effect=OSError("injected")):
                report, valid = update_agents_file(
                    "AGENTS.md", "example/project", root
                )

            self.assertFalse(valid)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(root.glob(".kb-bootstrap-agents-*.tmp")), [])

    def test_unsupported_exclusive_creation_leaves_no_destination_or_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "AGENTS.md"

            with patch.object(MODULE.os, "link", side_effect=OSError("unsupported")):
                report, valid = update_agents_file(
                    "AGENTS.md", "example/project", root
                )

            self.assertFalse(valid)
            self.assertIn("cannot be updated atomically", report)
            self.assertFalse(path.exists())
            self.assertEqual(list(root.glob(".kb-bootstrap-agents-*.tmp")), [])

    def test_post_link_cleanup_failure_rolls_back_owned_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "AGENTS.md"
            real_unlink = Path.unlink
            failures = {"count": 0}

            def fail_first_temp_unlink(candidate, *args, **kwargs):
                if candidate.name.startswith(".kb-bootstrap-agents-") and failures["count"] == 0:
                    failures["count"] += 1
                    raise OSError("injected")
                return real_unlink(candidate, *args, **kwargs)

            with patch.object(Path, "unlink", new=fail_first_temp_unlink):
                report, valid = update_agents_file(
                    "AGENTS.md", "example/project", root
                )

            self.assertFalse(valid)
            self.assertIn("cannot be updated atomically", report)
            self.assertFalse(path.exists())
            self.assertEqual(list(root.glob(".kb-bootstrap-agents-*.tmp")), [])

    def test_parent_change_before_staging_blocks_without_external_temp(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external_directory:
            root = Path(directory)
            external = Path(external_directory)
            nested = root / "nested"
            nested.mkdir()
            real_write = MODULE._write_staged

            def replace_parent(parent, content, mode, parent_identity):
                parent.rmdir()
                try:
                    parent.symlink_to(external, target_is_directory=True)
                except (OSError, NotImplementedError):
                    self.skipTest("directory symlink creation is unavailable")
                return real_write(parent, content, mode, parent_identity)

            with patch.object(MODULE, "_write_staged", side_effect=replace_parent):
                report, valid = update_agents_file(
                    "nested/AGENTS.md", "example/project", root
                )

            self.assertFalse(valid)
            self.assertIn("cannot be updated atomically", report)
            self.assertEqual(list(external.rglob("*")), [])

    def test_missing_target_race_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "AGENTS.md"
            real_link = os.link

            def race_link(source, destination):
                Path(destination).write_text("foreign creation", encoding="utf-8")
                return real_link(source, destination)

            with patch.object(MODULE.os, "link", side_effect=race_link):
                report, valid = update_agents_file(
                    "AGENTS.md", "example/project", root
                )

            self.assertFalse(valid)
            self.assertIn("cannot be updated atomically", report)
            self.assertEqual(path.read_text(encoding="utf-8"), "foreign creation")
            self.assertEqual(list(root.glob(".kb-bootstrap-agents-*.tmp")), [])

    def test_invalid_utf8_blocks_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "AGENTS.md"
            path.write_bytes(b"\xff\xfe")
            original = path.read_bytes()

            report, valid = update_agents_file(
                "AGENTS.md", "example/project", root
            )

            self.assertFalse(valid)
            self.assertIn("not valid UTF-8", report)
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
