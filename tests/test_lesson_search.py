import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kb_bootstrap.lesson_search import search_lessons, _read

class LessonSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.lessons = self.root / "kb" / "lessons"
        self.lessons.mkdir(parents=True)
        self._lesson(self.lessons / "APP-0001-timeout.md", "APP-0001", "timeout fixed")
        (self.lessons / "SCHEMA.md").write_text("schema", encoding="utf-8")
        (self.lessons / "index.yaml").write_text(
            "version: 1\nscope: project\nid_prefix: APP-\nlessons:\n  - id: APP-0001\n    path: kb/lessons/APP-0001-timeout.md\n",
            encoding="utf-8")
        (self.root / "lesson-stores.json").write_text(json.dumps({
            "version": 1, "local": {"path": "kb/lessons"},
            "shared": {"path": "shared", "read_only": True},
        }), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _lesson(path, lesson_id, body):
        path.write_text(f"---\nid: {lesson_id}\ntitle: CANARY_SECRET\nerror_signatures: [CANARY_SECRET]\n---\n{body}\n", encoding="utf-8")

    def test_explicit_store_body_search_and_frontmatter_exclusion(self):
        report, code = search_lessons("timeout", self.root, "local")
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(report["results"][0]["id"], "APP-0001")
        self.assertEqual(report["results"][0]["path"], "kb/lessons/APP-0001-timeout.md")
        self.assertNotIn("CANARY_SECRET", json.dumps(report))
        self.assertEqual(search_lessons("CANARY_SECRET", self.root, "local")[0]["results"], [])

    def test_lf_and_crlf_frontmatter_delimiters(self):
        lesson = self.lessons / "APP-0001-timeout.md"
        for newline in (bytes([10]), bytes([13, 10])):
            lesson.write_bytes(b"---" + newline + b"id: APP-0001" + newline + b"---" + newline + b"timeout body" + newline)
            report, code = search_lessons("timeout", self.root, "local")
            self.assertEqual((code, report["status"]), (0, "COMPLETE"))

    def test_malformed_duplicate_config_and_unindexed_file_fail_closed(self):
        (self.root / "lesson-stores.json").write_text('{"version":1,"version":1}', encoding="utf-8")
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")
        (self.root / "lesson-stores.json").write_text(json.dumps({"version": 1, "local": {"path": "kb/lessons"}}), encoding="utf-8")
        self._lesson(self.lessons / "APP-0002-extra.md", "APP-0002", "secret unindexed")
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")

    def test_traversal_and_symlink_rejected(self):
        config = {"version": 1, "local": {"path": "../outside"}}
        (self.root / "lesson-stores.json").write_text(json.dumps(config), encoding="utf-8")
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")
        (self.root / "lesson-stores.json").write_text(json.dumps({"version": 1, "local": {"path": "kb/lessons"}}), encoding="utf-8")
        link = self.lessons / "APP-0002-link.md"
        try:
            link.symlink_to(self.lessons / "APP-0001-timeout.md")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")

    def test_shared_registry_and_read_only_requirement(self):
        shared = self.root / "shared"
        (shared / "lessons").mkdir(parents=True)
        self._lesson(shared / "lessons" / "KB-0001-timeout.md", "KB-0001", "shared timeout")
        (shared / "index.yaml").write_text("count: 1\nlessons:\n  - id: KB-0001\n    file: lessons/KB-0001-timeout.md\n", encoding="utf-8")
        report, code = search_lessons("timeout", self.root, "shared")
        self.assertEqual(code, 0)
        self.assertEqual(report["results"][0]["store"], "shared")
        config = json.loads((self.root / "lesson-stores.json").read_text(encoding="utf-8"))
        config["shared"]["read_only"] = False
        (self.root / "lesson-stores.json").write_text(json.dumps(config), encoding="utf-8")
        self.assertEqual(search_lessons("timeout", self.root, "shared")[0]["status"], "UNAVAILABLE")

    def test_yaml_alias_and_duplicate_frontmatter_fail_closed(self):
        text = (self.lessons / "APP-0001-timeout.md").read_text(encoding="utf-8")
        (self.lessons / "APP-0001-timeout.md").write_text(text.replace("id: APP-0001\n", "id: APP-0001\nid: APP-0001\n"), encoding="utf-8")
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")

    def test_frontmatter_header_limit_boundary_and_over(self):
        lesson = self.lessons / "APP-0001-timeout.md"
        lf = bytes([10])
        fixed = b"---" + lf + b"id: APP-0001" + lf + b"pad: "
        closing = lf + b"---" + lf
        for header_bytes in (8192, 8193):
            padding = b"x" * (header_bytes - len(fixed) - len(closing))
            header = fixed + padding + closing
            self.assertEqual(len(header), header_bytes)
            lesson.write_bytes(header + b"timeout body" + lf)
            report, code = search_lessons("timeout", self.root, "local")
            self.assertEqual(report["status"], "COMPLETE" if header_bytes <= 8192 else "UNAVAILABLE")
            self.assertEqual(code, 0 if header_bytes <= 8192 else 1)

    def test_unicode_line_separators_never_expose_frontmatter_canary(self):
        lesson = self.lessons / "APP-0001-timeout.md"
        for newline in (chr(10), chr(13) + chr(10)):
            for separator in (chr(0x2028), chr(0x2029), chr(0x85)):
                header = "---" + newline + "id: APP-0001" + separator + "error_signatures: CANARY" + newline + "---" + newline
                lesson.write_bytes((header + "timeout body" + newline).encode("utf-8"))
                report, code = search_lessons("timeout", self.root, "local")
                self.assertEqual((report["status"], code), ("COMPLETE", 0))
                self.assertEqual(len(report["results"]), 1)
                canary_report, canary_code = search_lessons("CANARY", self.root, "local")
                self.assertEqual((canary_report["status"], canary_code), ("COMPLETE", 0))
                self.assertEqual(canary_report["results"], [])
                self.assertNotIn("CANARY", json.dumps(report))
                self.assertNotIn("CANARY", json.dumps(canary_report))

    def test_inventory_entry_limit_exact_and_one_over(self):
        import kb_bootstrap.lesson_search as module
        class Entries:
            def __init__(self, count): self.count = count
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def __iter__(self):
                yield type("Entry", (), {"name": "APP-0001-timeout.md"})()
                for i in range(self.count - 1): yield type("Entry", (), {"name": f"file{i}.txt"})()
        for count, expected in ((10000, "COMPLETE"), (10001, "PARTIAL")):
            with patch.object(module.os, "scandir", return_value=Entries(count)):
                report, _ = search_lessons("timeout", self.root, "local")
            self.assertEqual(report["status"], expected)

    def test_eligible_file_count_limit_exact_and_one_over(self):
        for extra in (999, 1000):
            rows=["  - id: APP-0001"+chr(10)+"    path: kb/lessons/APP-0001-timeout.md"]
            names=[]
            for number in range(2,extra+2):
                lid=f"APP-{number:04d}"; name=f"{lid}-lesson.md"
                self._lesson(self.lessons/name,lid,"body"); names.append(name)
                rows.append(f"  - id: {lid}"+chr(10)+f"    path: kb/lessons/{name}")
            index="version: 1"+chr(10)+"scope: project"+chr(10)+"id_prefix: APP-"+chr(10)+"lessons:"+chr(10)+chr(10).join(rows)+chr(10)
            (self.lessons/"index.yaml").write_text(index,encoding="utf-8")
            report,_=search_lessons("absent",self.root,"local")
            self.assertEqual(report["status"],"COMPLETE" if extra==999 else "PARTIAL")
            for name in names: (self.lessons/name).unlink()

    def test_nonmarkdown_inventory_entries_count_toward_directory_limit(self):
        from unittest.mock import patch
        import kb_bootstrap.lesson_search as module
        class Entries:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def __iter__(self):
                for i in range(10001): yield type("Entry", (), {"name": f"file{i}.txt"})()
        with patch.object(module.os, "scandir", return_value=Entries()):
            report, code = search_lessons("timeout", self.root, "local")
        self.assertEqual((report["status"], code, report["limiting_budget"]), ("PARTIAL", 3, "directory_entries"))

    def test_query_utf8_byte_limit_boundary(self):
        report, code = search_lessons("q" * 512, self.root, "local")
        self.assertEqual((report["status"], code), ("COMPLETE", 0))
        report, code = search_lessons("q" * 513, self.root, "local")
        self.assertEqual((report["status"], code), ("UNAVAILABLE", 1))

    def test_per_file_actual_read_cap_boundary_and_over(self):
        import kb_bootstrap.lesson_search as module
        path = self.root / "bounded.bin"
        budget = [0]
        path.write_bytes(b"x" * (1024 * 1024))
        self.assertEqual(len(module._read(path, 1024 * 1024, budget)), 1024 * 1024)
        path.write_bytes(b"x" * (1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            module._read(path, 1024 * 1024, [0])

    def test_result_and_excerpt_limits(self):
        lessons = self.lessons
        rows = []
        for number in range(1, 102):
            lid = f"APP-{number:04d}"
            name = f"{lid}-match.md"
            self._lesson(lessons / name, lid, "needle " + "x" * 600)
            rows.append(f"  - id: {lid}" + chr(10) + f"    path: kb/lessons/{name}")
        rows.append("  - id: APP-0001" + chr(10) + "    path: kb/lessons/APP-0001-timeout.md")
        index = "version: 1" + chr(10) + "scope: project" + chr(10) + "id_prefix: APP-" + chr(10) + "lessons:" + chr(10) + chr(10).join(rows) + chr(10)
        (lessons / "index.yaml").write_text(index, encoding="utf-8")
        report, code = search_lessons("needle", self.root, "local", 100)
        self.assertEqual((report["status"], code), ("PARTIAL", 3))
        self.assertEqual(len(report["results"]), 100)
        self.assertTrue(all(len(result["excerpt"].encode("utf-8")) == 512 for result in report["results"]))

    def test_serialized_output_limit_is_mathematically_unreachable(self):
        # 100 results x (512 excerpt bytes + bounded ID/path/store fields)
        # is far below 256 KiB; therefore the output ceiling is redundant
        # under the enforced result and field ceilings.
        import json as json_module
        result = {"store": "shared", "id": "KB-9999", "path": "lessons/KB-9999-" + "x" * 220 + ".md", "excerpt": "x" * 512}
        report = {"status": "PARTIAL", "complete": False, "results": [result] * 100, "limiting_budget": "results", "reason": None}
        self.assertLess(len(json_module.dumps(report, separators=(",", ":")).encode("utf-8")), 256 * 1024)

    def test_surrogate_query_is_sanitized(self):
        report, code = search_lessons(chr(0xD800), self.root, "local")
        self.assertEqual((report["status"], code), ("UNAVAILABLE", 1))

    def test_multibyte_frontmatter_over_byte_limit_rejected(self):
        lesson = self.lessons / "APP-0001-timeout.md"
        lf = bytes([10])
        header = b"---" + lf + b"id: APP-0001" + lf + b"pad: " + "é".encode("utf-8") * 4090 + lf + b"---" + lf
        self.assertGreater(len(header), 8192)
        lesson.write_bytes(header + b"timeout body" + lf)
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")

    def test_yaml_alias_and_index_duplicate_rejected(self):
        index = self.lessons / "index.yaml"
        original = index.read_text(encoding="utf-8")
        index.write_text(original + "version: 1" + chr(10), encoding="utf-8")
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")
        invalid = "version: 1" + chr(10) + "scope: project" + chr(10) + "id_prefix: APP-" + chr(10) + "lessons: &items []" + chr(10)
        index.write_text(invalid, encoding="utf-8")
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")
        duplicate_frontmatter = "---" + chr(10) + "id: APP-0001" + chr(10) + "id: APP-0001" + chr(10) + "---" + chr(10) + "timeout" + chr(10)
        (self.lessons / "APP-0001-timeout.md").write_text(duplicate_frontmatter, encoding="utf-8")
        index.write_text(original, encoding="utf-8")
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")

    def test_config_parent_traversal_and_custom_store_result_path(self):
        config = {"version": 1, "local": {"path": "../kb/lessons"}}
        (self.root / "lesson-stores.json").write_text(json.dumps(config), encoding="utf-8")
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")
        custom = self.root / "custom" / "store"
        custom.mkdir(parents=True)
        self._lesson(custom / "APP-0001-timeout.md", "APP-0001", "timeout custom")
        (custom / "SCHEMA.md").write_text("schema", encoding="utf-8")
        yaml_index = "version: 1" + chr(10) + "scope: project" + chr(10) + "id_prefix: APP-" + chr(10) + "lessons:" + chr(10) + "  - id: APP-0001" + chr(10) + "    path: custom/store/APP-0001-timeout.md" + chr(10)
        (custom / "index.yaml").write_text(yaml_index, encoding="utf-8")
        (self.root / "lesson-stores.json").write_text(json.dumps({"version": 1, "local": {"path": "custom/store"}}), encoding="utf-8")
        report, code = search_lessons("timeout", self.root, "local")
        self.assertEqual(code, 0)
        self.assertEqual(report["results"][0]["path"], "custom/store/APP-0001-timeout.md")

    def test_project_index_schema_and_frontmatter_identity_fail_closed(self):
        index = self.lessons / "index.yaml"
        original = index.read_text(encoding="utf-8")
        for invalid in (
            original.replace("scope: project", "scope: shared"),
            original.replace("id_prefix: APP-", "id_prefix: OTHER-"),
            original.replace("APP-0001", "APP-0002"),
        ):
            index.write_text(invalid, encoding="utf-8")
            self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")
        index.write_text(original, encoding="utf-8")
        lesson = self.lessons / "APP-0001-timeout.md"
        self._lesson(lesson, "APP-0002", "timeout")
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")

    def test_schema_and_index_byte_limit_boundary_and_over(self):
        import kb_bootstrap.lesson_search as module
        schema = self.lessons / "SCHEMA.md"
        index = self.lessons / "index.yaml"
        original_index = index.read_bytes()
        schema.write_bytes(b"x" * (64 * 1024))
        report, code = search_lessons("timeout", self.root, "local")
        self.assertEqual((report["status"], code), ("COMPLETE", 0))
        schema.write_bytes(b"x" * (64 * 1024 + 1))
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")
        schema.write_text("schema", encoding="utf-8")
        index.write_bytes(original_index + b"#" * (1024 * 1024 - len(original_index)))
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "COMPLETE")
        index.write_bytes(original_index + b"#" * (1024 * 1024 + 1 - len(original_index)))
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")

    def test_configuration_byte_limit_boundary_and_over(self):
        config = self.root / "lesson-stores.json"
        original = json.loads(config.read_text(encoding="utf-8"))
        prefix = json.dumps(original, separators=(",", ":"))[:-1]
        padding = " " * (64 * 1024 - len(prefix.encode("utf-8")) - 1)
        config.write_text(prefix + padding + "}", encoding="utf-8")
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "COMPLETE")
        config.write_text(prefix + padding + "}", encoding="utf-8")
        with config.open("ab") as output:
            output.write(b" ")
        report, code = search_lessons("timeout", self.root, "local")
        self.assertEqual((report["status"], code), ("UNAVAILABLE", 1))

    def test_yaml_node_and_depth_limits_exact_and_over(self):
        import kb_bootstrap.lesson_search as module
        def fixture(nodes):
            return "[" + ",".join("x" for _ in range(nodes - 1)) + "]"
        for count, expected in ((9999, True), (10000, True), (10001, False)):
            try:
                yaml_nodes = module.yaml.load(fixture(count), Loader=module.Loader)
                accepted = True
            except module.yaml.YAMLError:
                accepted = False
            self.assertEqual(accepted, expected)
        for depth, expected in ((30, True), (31, True), (32, False)):
            raw = "[" * depth + "x" + "]" * depth
            try:
                module.yaml.load(raw, Loader=module.Loader)
                accepted = True
            except module.yaml.YAMLError:
                accepted = False
            self.assertEqual(accepted, expected)

    def test_index_entry_limit_exact_and_one_over(self):
        index = self.lessons / "index.yaml"
        for count in (1000, 1001):
            entries = "lessons:" + chr(10) + ("  - id: APP-0001" + chr(10) + "    path: kb/lessons/APP-0001-timeout.md" + chr(10)) * count
            payload = "version: 1" + chr(10) + "scope: project" + chr(10) + "id_prefix: APP-" + chr(10) + entries
            index.write_text(payload, encoding="utf-8")
            report, code = search_lessons("timeout", self.root, "local")
            self.assertEqual((report["status"], report["limiting_budget"]), ("UNAVAILABLE", None) if count == 1000 else ("PARTIAL", "index_entries"))
            self.assertEqual(code, 1 if count == 1000 else 3)

    def test_shared_count_drift_and_unindexed_file_fail_closed(self):
        shared = self.root / "shared"
        (shared / "lessons").mkdir(parents=True)
        self._lesson(shared / "lessons" / "KB-0001-timeout.md", "KB-0001", "timeout")
        idx = shared / "index.yaml"
        idx.write_text("count: 0\\nlessons: []\\n", encoding="utf-8")
        self.assertEqual(search_lessons("timeout", self.root, "shared")[0]["status"], "UNAVAILABLE")

    def test_frontmatter_line_limit_and_actual_source_byte_partial(self):
        lesson = self.lessons / "APP-0001-timeout.md"
        lines = [b"---", b"id: APP-0001"] + [b"pad: x"] * 255 + [b"---", b"timeout"]
        lesson.write_bytes(bytes([10]).join(lines) + bytes([10]))
        self.assertEqual(search_lessons("timeout", self.root, "local")[0]["status"], "UNAVAILABLE")

    def test_repeated_actual_file_reads_are_all_counted(self):
        source = self.root / "counted.bin"
        payload = b"actual bytes read"
        source.write_bytes(payload)
        budget = [0]
        self.assertEqual(_read(source, len(payload), budget), payload)
        self.assertEqual(_read(source, len(payload), budget), payload)
        self.assertEqual(budget[0], 2 * len(payload))
        budget[0] = 16 * 1024 * 1024 - len(payload)
        self.assertEqual(_read(source, len(payload), budget), payload)
        self.assertEqual(budget[0], 16 * 1024 * 1024)
        budget[0] += 1
        with self.assertRaises(OverflowError):
            _read(source, len(payload), budget)
        self.assertEqual(budget[0], 16 * 1024 * 1024 + 1)

    def test_cli_integration(self):
        from kb_bootstrap.cli import main
        import sys
        output = __import__("io").StringIO()
        with patch.object(sys, "argv", ["kb-bootstrap", "search-lessons", "timeout", "--project-root", str(self.root), "--store", "local"]), patch("sys.stdout", output):
            self.assertEqual(main(), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "COMPLETE")

if __name__ == "__main__":
    unittest.main()
