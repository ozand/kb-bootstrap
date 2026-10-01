import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.canonical_graph_export import _identity, _read_document


class LegacyPath:
    def __init__(self, path):
        self.path = Path(path)

    def __fspath__(self):
        return os.fspath(self.path)

    def absolute(self):
        return self.path.absolute()

    def is_symlink(self):
        return self.path.is_symlink()

    def is_file(self):
        return self.path.is_file()

    def read_bytes(self):
        return self.path.read_bytes()

    def stat(self):
        return self.path.stat()


class GraphStatCompatibilityTests(unittest.TestCase):
    def test_legacy_path_reads_unchanged_concept(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'concept.md'
            data = b'---\ntype: Concept\n---\n# Example\n'
            path.write_bytes(data)
            legacy = LegacyPath(path)
            document, error = _read_document(legacy)
            self.assertEqual(error, '')
            self.assertEqual(document.content, data)
            details = os.stat(path, follow_symlinks=False)
            self.assertEqual(_identity(legacy), (details.st_dev, details.st_ino))
            self.assertEqual(path.read_bytes(), data)

    def test_source_changed_during_read_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'concept.md'
            path.write_bytes(b'---\ntype: Concept\n---\n# Example\n')
            legacy = LegacyPath(path)
            original = legacy.read_bytes

            def changed():
                data = original()
                path.write_bytes(data + b'changed\n')
                return data

            with patch.object(legacy, 'read_bytes', changed):
                document, error = _read_document(legacy)
            self.assertIsNone(document)
            self.assertEqual(error, 'concept changed while being read')

    def test_symlink_identity_is_link_and_document_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / 'target.md'
            data = b'---\ntype: Concept\n---\n# Private\n'
            target.write_bytes(data)
            link = root / 'link.md'
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlink unavailable')
            legacy = LegacyPath(link)
            details = os.stat(link, follow_symlinks=False)
            self.assertEqual(_identity(legacy), (details.st_dev, details.st_ino))
            self.assertNotEqual(_identity(legacy), _identity(target))
            document, error = _read_document(legacy)
            self.assertIsNone(document)
            self.assertIn('unsafe', error)
            self.assertEqual(target.read_bytes(), data)
