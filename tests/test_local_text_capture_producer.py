import importlib.util
import subprocess
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "kb_bootstrap/templates/skills/market-research/scripts"
_TEST_SCRIPTS = tempfile.TemporaryDirectory()
SCRIPT_COPY = Path(_TEST_SCRIPTS.name)
for script_name in ("produce_local_capture.py", "import_local_capture.py"):
    shutil.copyfile(SCRIPTS / script_name, SCRIPT_COPY / script_name)
sys.path.insert(0, str(SCRIPT_COPY))
SPEC = importlib.util.spec_from_file_location("produce_local_capture", SCRIPT_COPY / "produce_local_capture.py")
producer = importlib.util.module_from_spec(SPEC)
with patch("sys.dont_write_bytecode", True):
    SPEC.loader.exec_module(producer)
sys.path.remove(str(SCRIPT_COPY))
ImportErrorResult = producer.capture.ImportErrorResult


class LocalTextCaptureProducerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.study = self.root / "study"
        (self.study / "raw/img").mkdir(parents=True)
        self.source = self.inputs / "text.md"
        self.metadata = dict(title='Title "quoted" \\ : value', url='local: supplied "reference"',
                             captured_at='2026-11-01T10:00:00+03:00', captured_by='agent \\ "quoted"',
                             entity='yaml: [inert]', fidelity="partial")

    def produce(self, name="001-local.md", **overrides):
        metadata = dict(self.metadata)
        metadata.update(overrides)
        return producer.produce_capture(self.study, self.inputs, "text.md", name, **metadata)

    def test_body_bytes_preserved_for_newline_variants(self):
        for i, body in enumerate((b"a\n", b"a\r\n", b"a\r", b"a"), 1):
            with self.subTest(body=body):
                self.source.write_bytes(body)
                status, relative = self.produce(f"{i:03d}-local.md")
                self.assertEqual(status, "CREATED")
                output = (self.study / relative).read_bytes()
                self.assertTrue(output.endswith(body))
                self.assertEqual(output[output.index(b"---\n", 4) + 4:], body)

    def test_metadata_quotes_roundtrip_using_importer_json_scalar_parser(self):
        self.source.write_bytes(b"text")
        _, relative = self.produce()
        output = (self.study / relative).read_bytes()
        result = producer.capture._validate_frontmatter(output)
        self.assertEqual(result, "text")
        parsed = {}
        for line in output.decode("utf-8").splitlines()[1:]:
            if ":" not in line:
                break
            key, scalar = line.split(":", 1)
            if key in self.metadata and key != "fidelity":
                parsed[key] = producer.capture._parse_scalar(
                    scalar, allow_empty=(key == "entity"))
        for key in ("title", "url", "captured_at", "captured_by", "entity"):
            self.assertEqual(parsed[key], self.metadata[key], key)

    def test_bom_invalid_utf8_controls_and_invalid_metadata_block_without_output(self):
        for data in (b"\xef\xbb\xbftext", b"\xff", b"nul\x00", b"del\x7f"):
            with self.subTest(data=data):
                self.source.write_bytes(data)
                with self.assertRaises(ImportErrorResult):
                    self.produce("002-local.md")
                self.assertFalse((self.study / "raw/002-local.md").exists())
        self.source.write_bytes(b"valid")
        for key, value in (("title", ""), ("captured_at", "yesterday"),
                           ("captured_by", "a\nextra"), ("entity", "bad\u2028line")):
            with self.subTest(key=key):
                with self.assertRaises(ImportErrorResult):
                    self.produce("003-local.md", **{key: value})
                self.assertFalse((self.study / "raw/003-local.md").exists())

    def test_links_follow_importer_subset_without_dereference(self):
        self.source.write_bytes(b"[example](https://example.test/path)\n")
        self.assertEqual(self.produce()[0], "CREATED")
        self.source.write_bytes(b"![x](missing.png)")
        with self.assertRaises(ImportErrorResult) as caught:
            self.produce("002-local.md")
        self.assertEqual(caught.exception.status, "UNSUPPORTED")
        self.assertFalse((self.study / "raw/002-local.md").exists())

    def test_unsafe_source_path_and_collision_preserve_winner(self):
        self.source.write_bytes(b"text")
        for spelling in ("../text.md", "nested//text.md", "nested\\\\text.md"):
            with self.subTest(spelling=spelling), self.assertRaises(ImportErrorResult):
                producer.produce_capture(self.study, self.inputs, spelling, "003-local.md", **self.metadata)
        outside = self.root / "outside.md"
        outside.write_bytes(b"text")
        link = self.inputs / "linked.md"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            pass
        else:
            with self.assertRaises(ImportErrorResult):
                producer.produce_capture(self.study, self.inputs, "linked.md", "003-local.md", **self.metadata)
        winner = self.study / "raw/004-local.md"
        winner.write_bytes(b"winner")
        with self.assertRaises(ImportErrorResult) as caught:
            self.produce("004-local.md")
        self.assertEqual(caught.exception.status, "BLOCKED")
        self.assertEqual(winner.read_bytes(), b"winner")

    def test_producer_importer_checker_compose_in_synthetic_study(self):
        kb = self.root / "kb"
        for folder in ("wiki/concepts", "wiki/entities", "wiki/reports"):
            (kb / folder).mkdir(parents=True, exist_ok=True)
        created = subprocess.run([sys.executable, str(SCRIPTS / "new_research.py"),
                                  "local-study", "--title", "Synthetic local study", "--kb", str(kb)],
                                 cwd=self.root, capture_output=True, text=True, check=False)
        self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
        study = self.root / created.stdout.strip()
        self.assertTrue((study / "brief.md").is_file())
        self.source.write_bytes(b"Feature X from supplied bytes.\\r\\n")
        original = self.source.read_bytes()
        args = [sys.executable, str(SCRIPTS / "produce_local_capture.py"), str(study),
                "--input-root", str(self.inputs), "--input", "text.md",
                "--destination", "001-local.md", "--title", self.metadata["title"],
                "--url", self.metadata["url"], "--captured-at", self.metadata["captured_at"],
                "--captured-by", self.metadata["captured_by"], "--entity", "",
                "--fidelity", "full"]
        made = subprocess.run(args, capture_output=True, text=True, check=False)
        self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
        produced = study / "raw/001-local.md"
        self.assertTrue(produced.read_bytes().endswith(original))
        self.assertEqual(self.source.read_bytes(), original)
        input_root = self.root / "produced-input"
        input_root.mkdir()
        shutil.copyfile(produced, input_root / "capture.md")
        imported = subprocess.run([sys.executable, str(SCRIPTS / "import_local_capture.py"),
                                  str(study), "--input-root", str(input_root), "--input", "capture.md",
                                  "--destination", "002-local-copy.md"],
                                 capture_output=True, text=True, check=False)
        self.assertEqual(imported.returncode, 0, imported.stdout + imported.stderr)
        self.assertEqual((study / "raw/002-local-copy.md").read_bytes(), produced.read_bytes())
        (kb / "wiki/concepts/local.md").write_text("# Local\\n", encoding="utf-8")
        report = kb / "wiki/reports" / f"{study.name}.md"
        report.write_text(f"Brief: [brief](../../research/{study.name}/brief.md)\\n"
                          f"Capture: [raw](../../research/{study.name}/raw/001-local.md)\\n"
                          "Concept: [local](../concepts/local.md)\\n", encoding="utf-8")
        checked = subprocess.run([sys.executable, str(SCRIPTS / "check_research.py"), str(study),
                                  "--kb", str(kb), "--min-screenshots", "0", "--skip-validate"],
                                 capture_output=True, text=True, check=False)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertIn("raw pages: 2", checked.stdout)
        self.assertIn("OK", checked.stdout)

    def test_raced_destination_is_blocked_without_changing_winner(self):
        self.source.write_bytes(b"text")
        def raced(destination, data, study):
            with destination.open("xb") as stream:
                stream.write(b"racing winner")
            raise FileExistsError(destination)
        with patch.object(producer, "_exclusive_publish", raced):
            with self.assertRaises(ImportErrorResult) as caught:
                self.produce()
        self.assertEqual(caught.exception.status, "BLOCKED")
        self.assertEqual((self.study / "raw/001-local.md").read_bytes(), b"racing winner")

    def test_post_create_write_failure_is_partial_and_preserves_own_file(self):
        self.source.write_bytes(b"text")
        def partial(destination, data, study):
            with destination.open("xb") as stream:
                stream.write(data[:8])
            raise producer.capture.PartialCopyError("synthetic write failure")
        with patch.object(producer, "_exclusive_publish", partial):
            with self.assertRaises(ImportErrorResult) as caught:
                self.produce()
        self.assertEqual(caught.exception.status, "PARTIAL")
        self.assertEqual((self.study / "raw/001-local.md").read_bytes(), b"---\ntype")


if __name__ == "__main__":
    unittest.main()
