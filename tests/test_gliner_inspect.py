import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.cli import main
from kb_bootstrap.gliner_inspect import inspect_gliner_environment


class GlinerInspectTests(unittest.TestCase):
    def test_absent_model_and_runtime_report_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = list(root.iterdir())
            report, ready = inspect_gliner_environment(root / "missing")
            self.assertFalse(ready)
            self.assertIn("=== Optional GLiNER2 Local Setup ===", report)
            self.assertIn("model: unavailable or unsafe", report)
            self.assertIn("network isolation: not tested", report)
            self.assertNotIn(str(root), report)
            self.assertEqual(list(root.iterdir()), before)

    def test_module_presence_never_claims_complete_model_or_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory)
            (model / "config.json").write_text("{}", encoding="utf-8")
            report, ready = inspect_gliner_environment(model)
            self.assertIn("model: local config present (checkpoint not verified)", report)
            self.assertIn("model loading: not tested", report)
            self.assertNotIn(str(model), report)
            self.assertIn("gliner2: ", report)
            self.assertEqual(ready, "ERROR:" not in report)

    def test_model_symlinks_block_when_available(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "model"
            try:
                model.symlink_to(root, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            report, ready = inspect_gliner_environment(model)
            self.assertFalse(ready)
            self.assertIn("model: unavailable or unsafe", report)
            self.assertNotIn(str(root), report)

    def test_cli_captures_stdout_and_exit_without_child_process(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("subprocess.run") as spawn:
                with patch.object(sys, "argv", ["kb-bootstrap", "inspect-gliner", "--model-dir", directory]):
                    output = io.StringIO()
                    with redirect_stdout(output):
                        result = main()
                spawn.assert_not_called()
            self.assertEqual(result, 1)
            self.assertIn("RESULT: BLOCKED", output.getvalue())
            self.assertIn("model loading: not tested", output.getvalue())
            self.assertNotIn(directory, output.getvalue())

    def test_runtime_absence_is_not_model_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory)
            (model / "config.json").write_text("{}", encoding="utf-8")
            with patch("kb_bootstrap.gliner_inspect.importlib.util.find_spec", return_value=None):
                report, ready = inspect_gliner_environment(model)
            self.assertFalse(ready)
            self.assertIn("gliner2: module not discoverable", report)
            self.assertNotIn("RESULT: OK", report)

    def test_old_python_blocks_without_model_loading(self):
        with patch("kb_bootstrap.gliner_inspect.sys.version_info", (3, 9, 21)):
            report, ready = inspect_gliner_environment()
        self.assertFalse(ready)
        self.assertIn("python: requires 3.10+", report)
        self.assertIn("model loading: not tested", report)

    def test_model_config_symlink_is_not_a_verified_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "model"
            model.mkdir()
            target = Path(directory) / "config.json"
            target.write_text("{}", encoding="utf-8")
            try:
                (model / "config.json").symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            report, ready = inspect_gliner_environment(model)
            self.assertFalse(ready)
            self.assertIn("model: incomplete", report)
            self.assertNotIn(str(target), report)
