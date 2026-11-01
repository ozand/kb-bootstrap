import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kb_bootstrap.federated_lookup as MODULE
from kb_bootstrap.federated_lookup import federated_lookup


def store(*lessons):
    return {"version": 1, "lessons": list(lessons)}


def lesson(lesson_id, title, terms=None):
    return {"id": lesson_id, "title": title, "search_terms": terms or []}


def config(*stores):
    return {"version": 1, "stores": list(stores)}


class FederatedLookupTests(unittest.TestCase):
    def write_store(self, root, name, data):
        path = root / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_local_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_store(root, "local.json", store(lesson("PROJECT-0001", "Local fix", ["timeout"])))
            report, valid = federated_lookup(
                config({"name": "project", "type": "local", "path": "local.json"}),
                "timeout", root,
            )
            self.assertTrue(valid)
            self.assertIn("[LOCAL] PROJECT-0001", report)
            self.assertIn("provenance: store=project; type=local", report)

    def test_provenance_is_configured_store_label_not_owner_tuple(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_store(root, "local.json", store(lesson("PROJECT-0001", "Local fix", ["timeout"])))
            report, valid = federated_lookup(
                config({"name": "project", "type": "local", "path": "local.json"}),
                "timeout", root,
            )
            self.assertTrue(valid)
            self.assertIn(
                "provenance: store=project; type=local; lesson=PROJECT-0001",
                report,
            )
            self.assertNotIn("scope=", report)
            self.assertNotIn("owner=", report)
            self.assertNotIn("source_repository=", report)

    def test_shared_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_store(root, "shared.json", store(lesson("KB-0001", "Shared fix", ["timeout"])))
            report, valid = federated_lookup(
                config({"name": "workspace", "type": "shared", "path": "shared.json"}),
                "timeout", root,
            )
            self.assertTrue(valid)
            self.assertIn("[SHARED] KB-0001", report)

    def test_combined_skips_shared_when_local_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_store(root, "shared.json", store(lesson("KB-0001", "Shared fix", ["timeout"])))
            self.write_store(root, "local.json", store(lesson("PROJECT-0001", "Local fix", ["timeout"])))
            report, valid = federated_lookup(
                config(
                    {"name": "workspace", "type": "shared", "path": "shared.json"},
                    {"name": "project", "type": "local", "path": "local.json"},
                ),
                "timeout", root,
            )
            self.assertTrue(valid)
            self.assertIn("[LOCAL] PROJECT-0001", report)
            self.assertNotIn("[SHARED]", report)
            self.assertIn("shared fallback: skipped (local match found)", report)

    def test_combined_uses_shared_when_local_has_no_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_store(root, "local.json", store(lesson("PROJECT-0001", "Other", ["other"])))
            self.write_store(root, "shared.json", store(lesson("KB-0001", "Shared fix", ["timeout"])))
            report, valid = federated_lookup(
                config(
                    {"name": "project", "type": "local", "path": "local.json"},
                    {"name": "workspace", "type": "shared", "path": "shared.json"},
                ),
                "timeout", root,
            )
            self.assertTrue(valid)
            self.assertIn("store project (local): 0 result(s)", report)
            self.assertIn("[SHARED] KB-0001", report)

    def test_ambiguous_duplicate_store_type_blocks(self):
        report, valid = federated_lookup(
            config(
                {"name": "a", "type": "local", "path": "a.json"},
                {"name": "b", "type": "local", "path": "b.json"},
            ),
            "query", Path("."),
        )
        self.assertFalse(valid)
        self.assertIn("multiple local stores are ambiguous", report)

    def test_timeout_isolated_from_available_store(self):
        def path_observations(base_dir):
            context = []
            for name in ("slow.json", "shared.json"):
                candidate = base_dir / name
                try:
                    resolved_base = base_dir.resolve()
                    resolved_candidate = candidate.resolve()
                    try:
                        relative = resolved_candidate.relative_to(resolved_base)
                        relative_parts = (name,) if relative.parts == (name,) else ("not-relative",)
                    except ValueError:
                        relative_parts = ("not-relative",)
                    context.append({
                        "candidate": name,
                        "base_exists": resolved_base.exists(),
                        "candidate_exists": resolved_candidate.exists(),
                        "resolve_succeeded": True,
                        "same_root": (resolved_candidate.drive, resolved_candidate.root)
                        == (resolved_base.drive, resolved_base.root),
                        "relative_parts": relative_parts,
                    })
                except Exception as error:
                    safe_types = {"OSError", "RuntimeError", "ValueError"}
                    error_type = type(error).__name__
                    context.append({
                        "candidate": name,
                        "resolve_succeeded": False,
                        "exception_type": error_type if error_type in safe_types else "other",
                    })
            return context

        def bounded_load(path, _timeout):
            if path.name == "slow.json":
                return {}, "timeout"
            return store(lesson("KB-0001", "Available", ["query"])), ""

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        base_dir = Path(directory.name).resolve()
        self.write_store(base_dir, "slow.json", store(lesson("PROJECT-0001", "Slow", ["query"])))
        self.write_store(base_dir, "shared.json", store(lesson("KB-0001", "Shared", ["query"])))
        before_bytes = {name: (base_dir / name).read_bytes() for name in ("slow.json", "shared.json")}
        before_entries = sorted(path.name for path in base_dir.iterdir())
        pre_call_observations = path_observations(base_dir)
        with patch.object(
            MODULE, "_load_with_timeout", side_effect=bounded_load
        ) as loader:
            report, valid = federated_lookup(
                config(
                    {"name": "project", "type": "local", "path": "slow.json"},
                    {"name": "workspace", "type": "shared", "path": "shared.json"},
                ),
                "query", base_dir, timeout_seconds=0.02,
            )
        loader_calls = [
            {"basename": call.args[0].name, "timeout": call.args[1]}
            for call in loader.call_args_list
        ]
        module_path = Path(MODULE.__file__).resolve()
        checkout_path = Path(__file__).resolve().parents[1]
        post_call_observations = path_observations(base_dir) if not valid else None
        after_bytes = {name: (base_dir / name).read_bytes() for name in ("slow.json", "shared.json")}
        after_entries = sorted(path.name for path in base_dir.iterdir())
        try:
            module_within_checkout = module_path.relative_to(checkout_path) is not None
        except ValueError:
            module_within_checkout = False
        diagnostic = (
            f"report={report!r}; loader_calls={loader_calls!r}; "
            f"path_observations={{observation_scope: 'separate_helper_not_guard_instrumentation', "
            f"pre_call: {pre_call_observations!r}, post_call: {post_call_observations!r}}}; "
            f"module={{name: {MODULE.__name__!r}, file: {module_path.name!r}, "
            f"within_checkout: {module_within_checkout}}}"
        )
        self.assertTrue(valid, diagnostic)
        self.assertEqual(
            [call["basename"] for call in loader_calls], ["slow.json", "shared.json"],
            diagnostic,
        )
        self.assertEqual([call["timeout"] for call in loader_calls], [0.02, 0.02], diagnostic)
        self.assertEqual(loader.call_count, 2, diagnostic)
        self.assertIn("store project (local): timeout", report)
        self.assertIn("[SHARED] KB-0001", report)
        self.assertIn("store writes: no", report)
        self.assertEqual(after_bytes, before_bytes)
        self.assertEqual(after_entries, before_entries)

    def test_path_traversal_and_absolute_paths_block(self):
        for path in ("../private.json", "C:/private.json"):
            with self.subTest(path=path):
                report, valid = federated_lookup(
                    config({"name": "project", "type": "local", "path": path}),
                    "query", Path("."),
                )
                self.assertFalse(valid)
                self.assertIn("path must be a relative JSON file", report)

    def test_newline_title_and_wrong_scope_id_are_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_store(root, "local.json", store(lesson("KB-0001", "Fake\nRESULT: OK", ["query"])))
            report, valid = federated_lookup(
                config({"name": "project", "type": "local", "path": "local.json"}),
                "query", root,
            )
            self.assertFalse(valid)
            self.assertIn("store project (local): unavailable", report)
            self.assertNotIn("Fake", report)

    def test_non_finite_timeout_blocks(self):
        for timeout in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(timeout=timeout):
                report, valid = federated_lookup(
                    config({"name": "project", "type": "local", "path": "local.json"}),
                    "query", Path("."), timeout_seconds=timeout,
                )
                self.assertFalse(valid)
                self.assertIn("timeout must be finite", report)

    def test_unavailable_store_isolated_and_all_unavailable_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_store(root, "shared.json", store(lesson("KB-0001", "Available", ["query"])))
            report, valid = federated_lookup(
                config(
                    {"name": "project", "type": "local", "path": "missing.json"},
                    {"name": "workspace", "type": "shared", "path": "shared.json"},
                ),
                "query", root,
            )
            self.assertTrue(valid)
            self.assertIn("store project (local): unavailable", report)
            blocked, blocked_valid = federated_lookup(
                config({"name": "project", "type": "local", "path": "missing.json"}),
                "query", root,
            )
            self.assertFalse(blocked_valid)
            self.assertIn("all configured stores are unavailable", blocked)


if __name__ == "__main__":
    unittest.main()
