import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.cli import main


class ValidateCoreTests(unittest.TestCase):
    def call(self, argv):
        output = io.StringIO()
        with patch('sys.argv', ['kb-bootstrap', *argv]), redirect_stdout(output):
            result = main()
        return result, output.getvalue()

    def test_valid_core_does_not_call_optional_services_or_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            kb = root / 'kb'
            kb.mkdir()
            file = kb / 'concept.md'
            payload = b'---\ntype: Concept\n---\n# Example\n'
            file.write_bytes(payload)
            with patch('kb_bootstrap.cli.validate_qmd_collections', side_effect=AssertionError('QMD invoked')):
                with patch('subprocess.run', side_effect=AssertionError('process invoked')):
                    with patch('socket.create_connection', side_effect=AssertionError('network invoked')):
                        code, text = self.call(['validate-core', '--dir', str(kb)])
            self.assertEqual(code, 0, text)
            self.assertIn('=== Core Validation Scope ===', text)
            self.assertIn('publication readiness: not checked', text)
            self.assertEqual(file.read_bytes(), payload)
            self.assertEqual(sorted(p.name for p in root.iterdir()), ['kb'])
            legacy_code, legacy = self.call(['validate', '--dir', str(kb), '--project-root', str(root)])
            self.assertEqual(legacy_code, 1, legacy)
            self.assertIn('QMD', legacy)

    def test_invalid_core_metadata_and_dead_link_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'concept.md'
            for payload in (b'no frontmatter\n', b'---\ntype: Concept\n---\n[Missing](absent.md)\n'):
                file.write_bytes(payload)
                code, text = self.call(['validate-core', '--dir', temp])
                self.assertEqual(code, 1, text)
                self.assertIn('=== Core Validation Scope ===', text)
                self.assertEqual(file.read_bytes(), payload)

    def test_core_invalid_comparison_time_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / 'concept.md').write_text('---\ntype: Concept\n---\n', encoding='utf-8')
            code, text = self.call(['validate-core', '--dir', temp, '--now', 'not-a-time'])
            self.assertEqual(code, 1, text)
            self.assertIn('BLOCKED', text)
