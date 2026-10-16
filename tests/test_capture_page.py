import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path("kb_bootstrap/templates/skills/market-research/scripts/capture_page.py").resolve()
SPEC = importlib.util.spec_from_file_location("capture_page", SCRIPT)
capture_page = importlib.util.module_from_spec(SPEC)
_write_bytecode = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True
    SPEC.loader.exec_module(capture_page)
finally:
    sys.dont_write_bytecode = _write_bytecode


class CapturePageExclusiveTests(unittest.TestCase):
    def test_test_loader_does_not_write_bytecode_into_packaged_skill(self):
        self.assertFalse(any(SCRIPT.parent.rglob("*.pyc")))
        self.assertIn("def main", SCRIPT.read_text(encoding="utf-8"))
        self.assertFalse(sys.dont_write_bytecode)

    def study(self, root):
        (root / "raw/img").mkdir(parents=True)
        (root / "brief.md").write_text("# brief\n", encoding="utf-8")

    def run_main(self, root, page, images=0, fail_markdown=False, collide_markdown=False):
        args = ["capture_page.py", str(root), "https://example.test/page", "--window-id", "123456", "--images", str(images)]
        with patch.object(capture_page.sys, "argv", args), \
             patch.object(capture_page, "open_page", return_value="123456"), \
             patch.object(capture_page, "extract", return_value=page), \
             patch.object(capture_page, "surf", return_value=""), \
             patch.object(capture_page, "save_image", side_effect=self.image_writer(root)):
            if collide_markdown:
                original = capture_page._exclusive_write
                def write(path, data, study):
                    if path.suffix == ".md" and not path.exists():
                        with path.open("xb") as stream:
                            stream.write(b"racing winner")
                    return original(path, data, study)
                patcher = patch.object(capture_page, "_exclusive_write", side_effect=write)
            elif fail_markdown:
                original = capture_page._exclusive_write
                def write(path, data, study):
                    if path.suffix == ".md":
                        raise FileExistsError("raced markdown")
                    return original(path, data, study)
                patcher = patch.object(capture_page, "_exclusive_write", side_effect=write)
            else:
                patcher = patch.object(capture_page, "_exclusive_write", wraps=capture_page._exclusive_write)
            with patcher, patch("sys.stdout", new_callable=io.StringIO) as output:
                result = capture_page.main()
                return result, output.getvalue()

    def image_writer(self, root):
        def save(src, base, window, study, created):
            path = base.with_suffix(".png")
            capture_page._exclusive_write(path, b"synthetic image", study)
            created.append(path)
            return path
        return save

    def page(self, *, images=None):
        return {"markdown": "x" * 900, "title": "Example page", "url": "https://example.test/page",
                "images": images or []}

    def test_writer_preserves_existing_markdown_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            target = root / "raw/001-example-page.md"
            target.write_bytes(b"existing capture")
            with patch.object(capture_page, "next_number", return_value=1):
                result, output = self.run_main(root, self.page(), collide_markdown=True)
            self.assertEqual(result, 3)
            self.assertIn("BLOCKED", output)
            self.assertEqual(target.read_bytes(), b"existing capture")

    def test_writer_reports_partial_image_when_markdown_candidate_races(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            image = {"src": "https://example.test/image.png", "width": 800}
            target = root / "raw/001-example-page.md"
            result, output = self.run_main(root, self.page(images=[image]), images=1, fail_markdown=True)
            self.assertEqual(result, 3)
            self.assertIn("PARTIAL", output)
            self.assertIn("raw/img/001-1.png", output)
            self.assertEqual((root / "raw/img/001-1.png").read_bytes(), b"synthetic image")
            self.assertFalse(target.exists())

    def test_later_image_collision_reports_partial_and_preserves_first_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            images = [
                {"src": "https://example.test/first.png", "width": 800},
                {"src": "https://example.test/second.png", "width": 800},
            ]
            calls = []
            def save(src, base, window, study, created):
                calls.append(src)
                if len(calls) == 2:
                    raise FileExistsError("raced image")
                path = base.with_suffix(".png")
                capture_page._exclusive_write(path, b"first image", study)
                created.append(path)
                return path
            args = ["capture_page.py", str(root), "https://example.test/page", "--window-id", "123456", "--images", "2"]
            with patch.object(capture_page.sys, "argv", args), \
                 patch.object(capture_page, "open_page", return_value="123456"), \
                 patch.object(capture_page, "extract", return_value=self.page(images=images)), \
                 patch.object(capture_page, "surf", return_value=""), \
                 patch.object(capture_page, "save_image", side_effect=save), \
                 patch("sys.stdout", new_callable=io.StringIO) as output:
                result = capture_page.main()
            self.assertEqual(result, 3)
            self.assertIn("PARTIAL", output.getvalue())
            self.assertIn("raw/img/001-1.png", output.getvalue())
            self.assertEqual((root / "raw/img/001-1.png").read_bytes(), b"first image")
            self.assertFalse((root / "raw/001-example-page.md").exists())

    def test_symlinked_output_directory_blocks_before_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            outside = root.parent / (root.name + "-outside")
            outside.mkdir()
            (root / "raw/img").rmdir()
            try:
                (root / "raw/img").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                return
            with patch.object(capture_page, "open_page") as open_page:
                args = ["capture_page.py", str(root), "https://example.test/page"]
                with patch.object(capture_page.sys, "argv", args):
                    with self.assertRaises(SystemExit):
                        capture_page.main()
            open_page.assert_not_called()
            self.assertEqual(list(outside.iterdir()), [])

    def test_downloaded_image_uses_response_bytes_without_screenshot_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            payload = bytes((137, 80, 78, 71)) + b"x" * 2500
            with patch.object(capture_page.urllib.request, "urlopen",
                              return_value=io.BytesIO(payload)), \
                 patch.object(capture_page, "surf", side_effect=AssertionError("unexpected screenshot")):
                saved = capture_page.save_image("https://example.test/image.png",
                                                root / "raw/img/001-1", "123456",
                                                root, [])
            self.assertEqual(saved.read_bytes(), payload)
            self.assertEqual(saved.suffix, ".png")

    def test_unsupported_download_uses_screenshot_fallback_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            payload = b"unsupported response"
            def screenshot(*args):
                if "--output" not in args:
                    return ""
                output = Path(args[args.index("--output") + 1])
                output.write_bytes(b"synthetic screenshot")
                return ""
            with patch.object(capture_page.urllib.request, "urlopen",
                              return_value=io.BytesIO(payload)), \
                 patch.object(capture_page.time, "sleep"), \
                 patch.object(capture_page, "surf", side_effect=screenshot):
                created = []
                saved = capture_page.save_image("https://example.test/image.png",
                                                root / "raw/img/001-1", "123456", root, created)
            self.assertEqual(saved.read_bytes(), b"synthetic screenshot")
            self.assertEqual(created, [saved])
            self.assertEqual(saved.name, "001-1.png")

    def test_image_collision_preserves_existing_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            image = root / "raw/img/001-1.png"
            image.write_bytes(b"existing image")
            created = []
            payload = bytes((137, 80, 78, 71)) + b"x" * 2500
            with patch.object(capture_page.urllib.request, "urlopen",
                              return_value=io.BytesIO(payload)):
                with self.assertRaises(FileExistsError):
                    capture_page.save_image("https://example.test/image.png",
                                            root / "raw/img/001-1", "123456", root, created)
            self.assertEqual(image.read_bytes(), b"existing image")
            self.assertEqual(created, [])

    def test_exclusive_writer_rejects_existing_race_target_and_symlink_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            target = root / "raw/001-example.md"
            target.write_bytes(b"winner")
            with self.assertRaises(FileExistsError):
                capture_page._exclusive_write(target, b"loser", root)
            self.assertEqual(target.read_bytes(), b"winner")
            outside = root.parent / (root.name + "-outside")
            outside.mkdir()
            link = root / "raw/link"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                return
            with self.assertRaises(ValueError):
                capture_page._exclusive_write(link / "escaped.md", b"unsafe", root)
            self.assertFalse((outside / "escaped.md").exists())

    def test_successful_capture_format_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            result, output = self.run_main(root, self.page())
            self.assertEqual(result, 0, output)
            saved = root / "raw/001-example-page.md"
            text = saved.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\ntype: RawCapture\n"))
            self.assertIn("# Example page", text)
            self.assertIn("saved ", output)
