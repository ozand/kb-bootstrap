"""Synthetic acceptance tests for ADR-017; no consumer contents."""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from kb_bootstrap.local_retrieval import search_local, read_local, json_bytes

class LocalRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "canonical"
        self.root.mkdir()

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        return path

    def test_unicode_order_schema_context(self):
        self.put('b.md', '---\nrevision: r1\nreview: [private]\n---\n# B\nStraße\n')
        self.put('a.md', '# A\nSTRASSE\n')
        result, code = search_local('strasse', self.root)
        self.assertEqual(code, 0)
        self.assertEqual([r['path'] for r in result['results']], ['a.md', 'b.md'])
        record = result['results'][1]
        self.assertEqual(record['revision'], 'r1')
        self.assertEqual(record['review'], 'unknown')
        self.assertEqual(record['match_line'], 6)
        self.assertEqual(record['layer'], 'canonical-selection')
        self.assertEqual(record['kb'], 'canonical')

    def test_metadata_alias_unknown(self):
        self.put('a.md', '---\nrevision: &a value\nreview: *a\n---\nneedle\n')
        record = search_local('needle', self.root)[0]['results'][0]
        self.assertEqual(record['revision'], 'unknown')
        self.assertEqual(record['review'], 'unknown')

    def test_result_limit_and_no_hits(self):
        self.put('a.md', 'needle')
        self.assertEqual(search_local('needle', self.root, 1)[1], 0)
        self.put('b.md', 'needle')
        result, code = search_local('needle', self.root, 1)
        self.assertEqual((code, result['limiting_budget']), (3, 'result_limit'))
        self.assertEqual(search_local('absent', self.root)[0]['status'], 'COMPLETE')

    def test_selection_exclusions(self):
        self.put('a.md', 'needle')
        for path in ('raw/a.md', 'Research/a.md', 'LESSONS/a.md', '.hidden/a.md', '.file.md', 'INDEX.md', 'log.md'):
            self.put(path, 'needle')
            self.assertEqual(read_local(path, self.root)[1], 1)
        self.assertEqual([r['path'] for r in search_local('needle', self.root)[0]['results']], ['a.md'])

    def test_directory_budget_no_prefix(self):
        self.put('a.md', 'needle')
        self.put('b.md', 'needle')
        with patch('kb_bootstrap.local_retrieval.MAX_ENTRIES', 1):
            result, code = search_local('needle', self.root)
        self.assertEqual((code, result['results'], result['limiting_budget']), (3, [], 'directory_entries'))

    def test_file_and_aggregate_budgets(self):
        self.put('a.md', 'needle')
        for budget, value, reason in (('MAX_FILES', 0, 'files'), ('MAX_FILE', 2, 'file_bytes'), ('MAX_SCAN', 2, 'scan_bytes')):
            with self.subTest(budget=budget), patch('kb_bootstrap.local_retrieval.' + budget, value):
                result, code = search_local('needle', self.root)
                self.assertEqual((code, result['limiting_budget']), (3, reason))

    def test_exact_file_budget_complete(self):
        for index in range(1000):
            self.put('%04d.md' % index, 'nothing')
        self.assertEqual(search_local('missing', self.root)[1], 0)
        self.put('last.md', 'nothing')
        self.assertEqual(search_local('missing', self.root)[1], 3)

    def test_utf8_boundaries_and_invalid_eof(self):
        for data, budget, status, content in ((b'\xe2\x82', 16, 'BLOCKED', ''), ('ab€z'.encode(), 4, 'TRUNCATED', 'ab'), ('€'.encode() + b'\xff', 1, 'TRUNCATED', ''), (b'\xe2\xff\xac', 1, 'BLOCKED', ''), (b'a\xffb', 3, 'BLOCKED', '')):
            with self.subTest(data=data):
                self.put('a.md', data)
                result, code = read_local('a.md', self.root, budget)
                self.assertEqual((result['status'], result['content']), (status, content))
                self.assertEqual(code, 1 if status == 'BLOCKED' else 3)

    def test_output_cap_and_truncated_exit(self):
        self.put('a.md', b'\x01' * 65536)
        result, code = read_local('a.md', self.root, 65536)
        self.assertEqual((result['status'], result['truncated'], code), ('TRUNCATED', True, 3))
        self.assertLessEqual(len(json_bytes(result)) + 1, 262144)
        self.put('a.md', 'needle')
        with patch('kb_bootstrap.local_retrieval.MAX_OUTPUT', 200):
            result, code = search_local('needle', self.root)
            self.assertLessEqual(len(json_bytes(result)) + 1, 200)
            self.assertEqual(code, 3)

    def test_invalid_query_and_paths(self):
        for query in ('', 'a\nb', 'a\x85b', 'x' * 513):
            self.assertEqual(search_local(query, self.root)[1], 1)
        for path in ('../x.md', '/x.md', 'C:x.md', 'D:/x.md', 'a:b.md', 'NUL.md', 'a\\b.md', 'x.txt'):
            self.assertEqual(read_local(path, self.root)[1], 1)
        self.assertEqual(read_local('a.md', self.root, 65537)[1], 1)

    def test_external_symlink_and_lexical_root(self):
        outside = Path(self.temp.name) / 'outside.md'
        outside.write_bytes(b'private needle')
        link = self.root / 'link.md'
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        with patch('builtins.open', side_effect=AssertionError('must not open outside')):
            self.assertEqual(read_local('link.md', self.root)[1], 1)
        self.assertEqual(search_local('needle', self.root)[1], 1)
        self.assertEqual(search_local('needle', self.root / '..' / 'canonical')[1], 1)
        self.assertEqual(outside.read_bytes(), b'private needle')

    def test_offline_no_write_and_cli_legacy(self):
        from kb_bootstrap.cli import main
        source = self.put('a.md', '--odd\nneedle\n')
        before = source.read_bytes()
        with patch('subprocess.run', side_effect=AssertionError('process')), patch('socket.socket', side_effect=AssertionError('network')):
            self.assertEqual(search_local('--odd', self.root)[1], 0)
            self.assertEqual(read_local('a.md', self.root)[1], 0)
        with patch('sys.stdout', new_callable=io.StringIO) as output, patch('sys.argv', ['kb-bootstrap', 'search-local', '--dir', str(self.root), '--', '--odd']):
            self.assertEqual(main(), 0)
            self.assertEqual(json.loads(output.getvalue())['results'][0]['path'], 'a.md')
        with patch('kb_bootstrap.cli.search_qmd', return_value=('legacy', True)) as legacy, patch('sys.argv', ['kb-bootstrap', 'search', 'query']):
            self.assertEqual(main(), 0)
            legacy.assert_called_once()
        with patch('sys.stderr', new_callable=io.StringIO), patch('sys.argv', ['kb-bootstrap', 'search-local', 'needle']):
            with self.assertRaises(SystemExit) as error:
                main()
            self.assertEqual(error.exception.code, 2)
        self.assertEqual(source.read_bytes(), before)

    def test_actual_windows_junction_root_and_read_ancestor(self):
        import shutil
        import subprocess
        if os.name != 'nt':
            self.skipTest('Windows junctions only')
        base = Path(tempfile.mkdtemp(prefix='kb-local-junction-'))
        aliases = []
        try:
            target = base / 'outside'
            target.mkdir()
            sentinel = target / 'secret.md'
            sentinel.write_bytes(b'private needle')
            root = base / 'canonical'
            root.mkdir()
            for alias, search_root, read_path in ((base / 'root-link', base / 'root-link', 'secret.md'), (root / 'parent', root, 'parent/secret.md')):
                aliases.append(alias)
                run = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(alias), str(target)], capture_output=True, timeout=10)
                self.assertEqual(run.returncode, 0)
                self.assertTrue(os.lstat(alias).st_file_attributes & 0x400)
                with patch('builtins.open', side_effect=AssertionError('outside open')):
                    self.assertEqual(search_local('needle', search_root)[1], 1)
                    self.assertEqual(read_local(read_path, search_root)[1], 1)
                self.assertEqual(sentinel.read_bytes(), b'private needle')
        finally:
            unresolved = False
            for alias in aliases:
                try:
                    info = os.lstat(alias)
                except FileNotFoundError:
                    continue
                except OSError:
                    unresolved = True
                    continue
                if not getattr(info, 'st_file_attributes', 0) & 0x400:
                    unresolved = True
                    continue
                try:
                    os.rmdir(alias)
                    unresolved = unresolved or os.path.lexists(alias)
                except OSError:
                    unresolved = True
            if unresolved:
                raise RuntimeError('junction absence unverified; temporary tree preserved')
            shutil.rmtree(base)


