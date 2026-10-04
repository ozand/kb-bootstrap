"""Synthetic ADR-018 adapter/process regressions."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from kb_bootstrap.bounded_process import run_bounded
from kb_bootstrap.qmd_adapter import validate_records

class BoundedQmdTests(unittest.TestCase):
    def test_detached_child_can_outlive_direct_parent_timeout(self):
        import time
        child = "import time,pathlib;time.sleep(1.5);pathlib.Path('finished').write_bytes(b'done')"
        parent = "import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',%r],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(5)" % child
        owned = Path(tempfile.mkdtemp(prefix='kb-qmd-descendant-test-'))
        output, reason = run_bounded([sys.executable, '-c', parent], owned, os.environ.copy(), timeout=1)
        self.assertEqual(reason, 'timeout')
        deadline = time.monotonic() + 5
        while not (owned / 'finished').exists() and time.monotonic() < deadline:
            time.sleep(.02)
        if not (owned / 'finished').exists():
            self.fail('child completion unconfirmed; owned fixture preserved')
        self.assertEqual((owned / 'finished').read_bytes(), b'done')
        # A marker is not process-exit evidence. Preserve this tiny fixture;
        # no recursive cleanup occurs while descendant exit is unconfirmed.

    def test_abnormal_termination_preserves_owned_cwd(self):
        from unittest.mock import patch
        from kb_bootstrap.qmd_adapter import search_qmd_bounded
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for reason in ('timeout', 'output_limit', 'termination_unconfirmed'):
                for during_search in (False, True):
                    scratch = root / (reason + str(during_search))
                    scratch.mkdir()
                    returns = [(b'qmd 2.8.3\n', ''), (b'', reason)] if during_search else [(b'', reason)]
                    with patch('kb_bootstrap.qmd_adapter.installed_launch', return_value=(['fake'], '')), \
                         patch('kb_bootstrap.qmd_adapter.state_environment', return_value=({}, '')), \
                         patch('kb_bootstrap.qmd_adapter.tempfile.mkdtemp', return_value=str(scratch)), \
                         patch('kb_bootstrap.qmd_adapter.run_bounded', side_effect=returns), \
                         patch('kb_bootstrap.qmd_adapter.shutil.rmtree') as cleanup:
                        report, code = search_qmd_bounded('query', root, 'c', 'i', root)
                    self.assertEqual((report['reason'], code), (reason, 1))
                    cleanup.assert_not_called()
                    self.assertTrue(scratch.is_dir())

    def test_adapter_version_failure_absence_and_static_diagnostics(self):
        from unittest.mock import patch
        from kb_bootstrap.qmd_adapter import search_qmd_bounded
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch('kb_bootstrap.qmd_adapter.installed_launch', return_value=(None, 'executable_absent')):
                report, code = search_qmd_bounded('query', root, 'c', 'i', root)
                self.assertEqual((report['status'], code), ('OPTIONAL_UNAVAILABLE', 1))
            with patch('kb_bootstrap.qmd_adapter.installed_launch', return_value=(['fake'], '')), patch('kb_bootstrap.qmd_adapter.state_environment', return_value=({}, '')), patch('kb_bootstrap.qmd_adapter.run_bounded', return_value=(b'qmd 9.9.9\n', '')) as run:
                report, code = search_qmd_bounded('query', root, 'c', 'i', root)
                self.assertEqual(report['reason'], 'version_mismatch')
                self.assertEqual(run.call_count, 1)
            with patch('kb_bootstrap.qmd_adapter.installed_launch', return_value=(['fake'], '')), patch('kb_bootstrap.qmd_adapter.state_environment', return_value=({}, '')), patch('kb_bootstrap.qmd_adapter.run_bounded', return_value=(b'', 'exit_nonzero')):
                report, code = search_qmd_bounded('query', root, 'c', 'i', root)
                self.assertEqual(report, {'status': 'FAILED', 'results': [], 'reason': 'exit_nonzero'})

    def test_index_selector_matrix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'a.md').write_bytes(b'synthetic')
            for suffix, valid in (('', True), ('?index=smoke', True), ('?index=other', False), ('?index=smoke&index=smoke', False), ('?index=%73moke', False), ('#fragment', False), ('?extra=x', False)):
                record = {'file': 'qmd://c/a.md' + suffix, 'title': 'X', 'score': 1}
                self.assertEqual(validate_records([record], 'c', root, 10, 'smoke') is not None, valid)

    def test_state_defaults_hooks_and_aliases(self):
        import yaml
        from kb_bootstrap.qmd_adapter import state_environment, MODEL_DEFAULTS
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); root = base / 'canonical'; root.mkdir()
            state = base / 'state'; (state / 'config').mkdir(parents=True)
            (state / 'cache/qmd').mkdir(parents=True)
            (state / 'cache/qmd/smoke.sqlite').write_bytes(b'fixture')
            config = state / 'config/smoke.yml'
            spec = {'path': str(root), 'pattern': '**/*.md'}
            for models, valid in ((MODEL_DEFAULTS, True), ({}, True), ({'embed': 'hf:foreign/model'}, False)):
                config.write_text(yaml.safe_dump({'collections': {'c': spec}, 'models': models}), encoding='utf-8')
                env, error = state_environment(state, 'smoke', 'c', root)
                self.assertEqual(not bool(error), valid)
            config.write_text(yaml.safe_dump({'collections': {'c': {**spec, 'update': 'private command'}}}), encoding='utf-8')
            self.assertEqual(state_environment(state, 'smoke', 'c', root)[1], 'config_invalid')

    def test_process_success_failure_timeout_and_caps(self):
        with tempfile.TemporaryDirectory() as cwd:
            cases = [("print('ok')", {}, b'ok', ''),
                     ("raise SystemExit(7)", {}, b'', 'exit_nonzero'),
                     ("import time;time.sleep(2)", {'timeout': .1}, b'', 'timeout'),
                     ("import sys;sys.stdout.write('x'*100000)", {'stdout_limit': 100}, b'', 'output_limit'),
                     ("import sys;sys.stderr.write('x'*100000)", {'stderr_limit': 100}, b'', 'output_limit')]
            for code, options, expected, reason in cases:
                with self.subTest(reason=reason):
                    output, error = run_bounded([sys.executable, '-c', code], cwd, os.environ.copy(), **options)
                    self.assertEqual(error, reason)
                    self.assertTrue(output.startswith(expected))

    def test_records_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'a.md').write_text('synthetic', encoding='utf-8')
            good = {'file': 'qmd://collection/a.md', 'title': 'Example', 'score': 0}
            self.assertIsNotNone(validate_records([good], 'collection', root, 10))
            for bad in (None, 1, [], 'text', {'file': 'qmd://other/a.md', 'title': 'X', 'score': 1}, {**good, 'score': True}, {**good, 'score': float('nan')}, {**good, 'file': 'qmd://collection/../a.md'}):
                self.assertIsNone(validate_records([bad], 'collection', root, 10))
