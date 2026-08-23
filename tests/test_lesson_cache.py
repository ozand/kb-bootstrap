import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.lesson_cache import check_cache, sync_cache


def source_bundle(version="r1", lesson_version="v1", ids=("KB-0001", "KB-0002")):
    return {
        "version": 1,
        "source_repository": "example/shared-lessons",
        "registry_version": version,
        "generated_at": "2026-08-23T00:00:00Z",
        "lessons": [
            {
                "id": lesson_id,
                "version": lesson_version,
                "updated": "2026-08-22",
                "content": {
                    "title": f"Lesson {lesson_id}",
                    "problem": "A portable failure occurs.",
                    "resolution": "Use the reviewed deterministic fix.",
                    "prevention": "Validate before retrying.",
                    "private": "not copied",
                },
            }
            for lesson_id in ids
        ],
    }


class LessonCacheTests(unittest.TestCase):
    def write_source(self, root, bundle=None):
        path = root / "source.json"
        path.write_text(json.dumps(bundle or source_bundle()), encoding="utf-8")
        return path

    def test_empty_allowlist_blocks_without_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.write_source(root)
            cache = root / "cache.json"
            report, valid = sync_cache(source, cache, [])
            self.assertFalse(valid)
            self.assertIn("allowlist must contain", report)
            self.assertFalse(cache.exists())

    def test_explicit_allowlist_exports_only_selected_lesson_with_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.write_source(root)
            cache = root / "cache.json"
            report, valid = sync_cache(source, cache, ["KB-0002"])
            self.assertTrue(valid)
            data = json.loads(cache.read_text(encoding="utf-8"))
            self.assertEqual(data["selection"], ["KB-0002"])
            self.assertEqual([entry["id"] for entry in data["entries"]], ["KB-0002"])
            entry = data["entries"][0]
            self.assertEqual(entry["source_repository"], "example/shared-lessons")
            self.assertEqual(entry["registry_version"], "r1")
            self.assertEqual(entry["lesson_version"], "v1")
            self.assertEqual(entry["freshness"], "fresh")
            self.assertNotIn("private", entry["content"])
            self.assertIn("shared store write: no", report)

    def test_refresh_updates_selected_and_preserves_unselected_without_prune(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.write_source(root)
            cache = root / "cache.json"
            sync_cache(source, cache, ["KB-0001", "KB-0002"])
            source.write_text(json.dumps(source_bundle(version="r2", lesson_version="v2")), encoding="utf-8")
            report, valid = sync_cache(source, cache, ["KB-0001"])
            self.assertTrue(valid)
            entries = {entry["id"]: entry for entry in json.loads(cache.read_text(encoding="utf-8"))["entries"]}
            self.assertEqual(entries["KB-0001"]["lesson_version"], "v2")
            self.assertEqual(entries["KB-0002"]["freshness"], "stale")
            self.assertIn("pruned: none", report)

    def test_prune_removes_only_local_unselected_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.write_source(root)
            cache = root / "cache.json"
            sync_cache(source, cache, ["KB-0001", "KB-0002"])
            report, valid = sync_cache(source, cache, ["KB-0001"], prune=True)
            self.assertTrue(valid)
            data = json.loads(cache.read_text(encoding="utf-8"))
            self.assertEqual([entry["id"] for entry in data["entries"]], ["KB-0001"])
            self.assertIn("pruned: KB-0002", report)
            self.assertEqual(len(source_bundle()["lessons"]), 2)

    def test_check_reports_stale_and_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.write_source(root)
            cache = root / "cache.json"
            sync_cache(source, cache, ["KB-0001"])
            original = cache.read_bytes()
            source.write_text(json.dumps(source_bundle(lesson_version="v2")), encoding="utf-8")
            report, valid = check_cache(source, cache, ["KB-0001"])
            self.assertFalse(valid)
            self.assertIn("RESULT: STALE", report)
            self.assertIn("KB-0001", report)
            self.assertEqual(cache.read_bytes(), original)

    def test_punctuation_wrapped_paths_fail_sanitization(self):
        for value in ('error_path":"/etc/passwd"', '{"target":"C:\\Windows\\System32"}', "['//var/private']"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle = source_bundle()
                bundle["lessons"][0]["content"]["problem"] = value
                source = self.write_source(root, bundle)
                cache = root / "cache.json"
                report, valid = sync_cache(source, cache, ["KB-0001"])
                self.assertFalse(valid)
                self.assertIn("content problem failed sanitization", report)
                self.assertFalse(cache.exists())

    def test_source_failure_or_conflict_preserves_existing_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.write_source(root)
            cache = root / "cache.json"
            sync_cache(source, cache, ["KB-0001"])
            original = cache.read_bytes()
            source.unlink()
            report, valid = sync_cache(source, cache, ["KB-0001"])
            self.assertFalse(valid)
            self.assertIn("source bundle is unavailable", report)
            self.assertEqual(cache.read_bytes(), original)

    def test_temp_write_failure_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.write_source(root)
            cache = root / "cache.json"

            class FailingTemp:
                def __init__(self, path):
                    self.name = str(path)
                def __enter__(self):
                    Path(self.name).write_text("partial", encoding="utf-8")
                    return self
                def write(self, _):
                    raise OSError("disk full")
                def __exit__(self, *args):
                    return False

            temp_path = root / "leaked.tmp"
            with patch("kb_bootstrap.lesson_cache.tempfile.NamedTemporaryFile", return_value=FailingTemp(temp_path)):
                report, valid = sync_cache(source, cache, ["KB-0001"])

            self.assertFalse(valid)
            self.assertIn("cache cannot be written", report)
            self.assertFalse(temp_path.exists())
            self.assertFalse(cache.exists())

    def test_atomic_write_failure_preserves_existing_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.write_source(root)
            cache = root / "cache.json"
            sync_cache(source, cache, ["KB-0001"])
            original = cache.read_bytes()
            with patch("kb_bootstrap.lesson_cache.os.replace", side_effect=PermissionError):
                report, valid = sync_cache(source, cache, ["KB-0002"])
            self.assertFalse(valid)
            self.assertIn("cache cannot be written", report)
            self.assertEqual(cache.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
