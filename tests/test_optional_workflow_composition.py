"""Core validation and explicitly selected QMD remain separate outcomes."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

from kb_bootstrap.cli import main
from kb_bootstrap.qmd_adapter import MODEL_DEFAULTS, search_qmd_bounded


class OptionalWorkflowCompositionTests(unittest.TestCase):
    def _core_validate(self, canonical):
        output = io.StringIO()
        with patch("sys.argv", ["kb-bootstrap", "validate-core", "--dir", str(canonical)]):
            with redirect_stdout(output):
                code = main()
        self.assertEqual(code, 0, output.getvalue())
        self.assertIn("Core Validation Scope", output.getvalue())
        self.assertIn("retrieval, index freshness and publication readiness: not checked", output.getvalue())

    def _qmd_state(self, base, canonical):
        state = base / "state"
        (state / "config").mkdir(parents=True)
        (state / "cache/qmd").mkdir(parents=True)
        (state / "cache/qmd/smoke.sqlite").write_bytes(b"fixture")
        config = {"collections": {"c": {"path": str(canonical), "pattern": "**/*.md"}}, "models": MODEL_DEFAULTS}
        (state / "config/smoke.yml").write_text(yaml.safe_dump(config), encoding="utf-8")
        return state

    def test_core_passes_when_optional_qmd_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            canonical = base / "canonical"
            canonical.mkdir()
            (canonical / "concept.md").write_text("---\ntype: Concept\n---\n# Synthetic\n", encoding="utf-8")
            state = self._qmd_state(base, canonical)
            with patch("kb_bootstrap.qmd_adapter.installed_launch", return_value=(None, "executable_absent")) as launch:
                self._core_validate(canonical)
                report, code = search_qmd_bounded("synthetic", canonical, "c", "smoke", state)
            launch.assert_called_once_with()
            self.assertEqual((report["status"], report["reason"], code), ("OPTIONAL_UNAVAILABLE", "executable_absent", 1))

    def test_configured_qmd_runs_version_and_search_and_preserves_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            canonical = base / "canonical"
            canonical.mkdir()
            (canonical / "concept.md").write_text("---\ntype: Concept\n---\n# Synthetic\n", encoding="utf-8")
            state = self._qmd_state(base, canonical)
            for process_results, expected in (
                ([(b"qmd 2.8.3\n", ""), (b"", "exit_nonzero")], ("FAILED", "exit_nonzero", 1)),
                ([(b"qmd 2.8.3\n", ""), (json.dumps([{"file": "qmd://c/concept.md", "title": "Synthetic", "score": 1}]).encode(), "")], ("OK", None, 0)),
            ):
                with self.subTest(expected=expected):
                    with patch("kb_bootstrap.qmd_adapter.installed_launch", return_value=(["fake-qmd"], "")) as launch, patch(
                        "kb_bootstrap.qmd_adapter.run_bounded", side_effect=process_results
                    ) as process:
                        report, code = search_qmd_bounded("synthetic", canonical, "c", "smoke", state)
                    launch.assert_called_once_with()
                    self.assertEqual(process.call_count, 2)
                    self.assertEqual(process.call_args_list[0].args[0], ["fake-qmd", "--version"])
                    self.assertEqual(process.call_args_list[1].args[0][:7], ["fake-qmd", "--index", "smoke", "search", "-c", "c", "--format"])
                    self.assertEqual((report["status"], report.get("reason"), code), expected)
