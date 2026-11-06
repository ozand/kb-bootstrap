import importlib.util
import io
import json
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
        self.assertEqual(sys.dont_write_bytecode, _write_bytecode)

    def study(self, root):
        (root / "raw/img").mkdir(parents=True)
        (root / "brief.md").write_text("# brief\n", encoding="utf-8")

    def run_main(self, root, page, images=0, fail_markdown=False, collide_markdown=False,
                 save_func=None):
        args = ["capture_page.py", str(root), "https://example.test/page", "--window-id", "123456", "--images", str(images)]
        with patch.object(capture_page.sys, "argv", args), \
             patch.object(capture_page, "open_page", return_value="123456"), \
             patch.object(capture_page, "extract", return_value=page), \
             patch.object(capture_page, "surf", return_value=""), \
             patch.object(capture_page, "save_image",
                          side_effect=save_func or self.image_writer(root)):
            if collide_markdown:
                original = capture_page._exclusive_write
                def write(path, data, study, on_created=None):
                    if path.suffix == ".md" and not path.exists():
                        with path.open("xb") as stream:
                            stream.write(b"racing winner")
                    return original(path, data, study, on_created)
                patcher = patch.object(capture_page, "_exclusive_write", side_effect=write)
            elif fail_markdown:
                original = capture_page._exclusive_write
                def write(path, data, study, on_created=None):
                    if path.suffix == ".md":
                        raise FileExistsError("raced markdown")
                    return original(path, data, study, on_created)
                patcher = patch.object(capture_page, "_exclusive_write", side_effect=write)
            else:
                patcher = patch.object(capture_page, "_exclusive_write", wraps=capture_page._exclusive_write)
            with patcher, patch("sys.stdout", new_callable=io.StringIO) as output:
                result = capture_page.main()
                return result, output.getvalue()

    def image_writer(self, root):
        def save(src, base, window, study, created, method_out):
            path = base.with_suffix(".png")
            capture_page._exclusive_write(path, b"synthetic image", study, created.append)
            method_out.append("downloaded_response")
            return path
        return save

    def page(self, *, images=None):
        markdown = "x" * 900
        if images:
            markdown += "\n![image](%s)" % images[0]["src"]
        return {"markdown": markdown, "title": "Example page", "url": "https://example.test/page",
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
            def save(src, base, window, study, created, method_out):
                calls.append(src)
                if len(calls) == 2:
                    raise FileExistsError("raced image")
                path = base.with_suffix(".png")
                capture_page._exclusive_write(path, b"first image", study)
                created.append(path)
                method_out.append("downloaded_response")
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
            method = []
            with patch.object(capture_page.urllib.request, "urlopen",
                              return_value=io.BytesIO(payload)), \
                 patch.object(capture_page, "surf", side_effect=AssertionError("unexpected screenshot")):
                saved = capture_page.save_image("https://example.test/image.png",
                                                root / "raw/img/001-1", "123456",
                                                root, [], method)
            self.assertEqual(saved.read_bytes(), payload)
            self.assertEqual(saved.suffix, ".png")
            self.assertEqual(method, ["downloaded_response"])
            self.assertEqual(method, ["downloaded_response"])

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
                method = []
                saved = capture_page.save_image("https://example.test/image.png",
                                                root / "raw/img/001-1", "123456", root, created, method)
            self.assertEqual(saved.read_bytes(), b"synthetic screenshot")
            self.assertEqual(created, [saved])
            self.assertEqual(saved.name, "001-1.png")
            self.assertEqual(method, ["surf_screenshot_fallback"])
            self.assertEqual(method, ["surf_screenshot_fallback"])

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

    def test_exclusive_write_failure_after_create_records_owned_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            target = root / "raw/001-owned.md"
            owned = []
            original = capture_page.os.fdopen

            class FailingStream:
                def __init__(self, stream):
                    self.stream = stream
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    self.stream.close()
                    raise OSError("synthetic close failure")
                def write(self, data):
                    self.stream.write(data[:5])
                    raise OSError("synthetic write failure")

            with patch.object(capture_page.os, "fdopen",
                              side_effect=lambda *args, **kwargs: FailingStream(original(*args, **kwargs))):
                with self.assertRaises(OSError):
                    capture_page._exclusive_write(target, b"partial output", root, owned.append)
            self.assertEqual(owned, [target])
            self.assertEqual(target.read_bytes(), b"parti")
            with self.assertRaises(FileExistsError):
                capture_page._exclusive_write(target, b"replacement", root, owned.append)
            self.assertEqual(target.read_bytes(), b"parti")
            self.assertEqual(owned, [target])

    def test_image_manifest_exact_bytes_and_method_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            images = [{"src": "https://example.test/one.png", "width": 800},
                      {"src": "https://example.test/two.png", "width": 800}]
            methods = iter(["downloaded_response", "surf_screenshot_fallback"])

            def save(src, base, window, study, created, method_out):
                path = base.with_suffix(".png")
                capture_page._exclusive_write(path, src.encode("ascii"), study)
                created.append(path)
                method_out.append(next(methods))
                return path

            original = capture_page._exclusive_write
            def write(path, data, study, on_created=None):
                return original(path, data, study, on_created)

            with patch.object(capture_page, "_exclusive_write", side_effect=write):
                result, output = self.run_main(root, self.page(images=images), images=2,
                                               save_func=save)
            self.assertEqual(result, 0, output)
            expected = (b'{"format":"kb-bootstrap-image-capture-methods","version":1,'
                        b'"capture":"raw/001-example-page.md","images":['
                        b'{"path":"raw/img/001-1.png","method":"downloaded_response"},'
                        b'{"path":"raw/img/001-2.png","method":"surf_screenshot_fallback"}]}\n')
            self.assertEqual((root / "raw/001-example-page.images.json").read_bytes(), expected)
            self.assertEqual((root / "raw/img/001-1.png").read_bytes(), images[0]["src"].encode("ascii"))

    def test_no_image_and_failed_fallback_do_not_emit_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            result, output = self.run_main(root, self.page())
            self.assertEqual(result, 0, output)
            self.assertFalse((root / "raw/001-example-page.images.json").exists())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            image = {"src": "https://example.test/image.png", "width": 800}
            result, output = self.run_main(root, self.page(images=[image]), images=1,
                                           save_func=lambda *args: None)
            self.assertEqual(result, 0, output)
            self.assertFalse((root / "raw/001-example-page.images.json").exists())
            text = (root / "raw/001-example-page.md").read_text(encoding="utf-8")
            self.assertIn(image["src"], text)

    def test_manifest_collision_before_capture_blocks_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            manifest = root / "raw/001-example-page.images.json"
            manifest.write_bytes(b"winner")
            image = {"src": "https://example.test/image.png", "width": 800}
            with patch.object(capture_page, "next_number", return_value=1):
                result, output = self.run_main(root, self.page(images=[image]), images=1)
            self.assertEqual(result, 3)
            self.assertIn("BLOCKED", output)
            self.assertEqual(manifest.read_bytes(), b"winner")
            self.assertFalse((root / "raw/img/001-1.png").exists())

    def test_image_write_failure_after_exclusive_create_is_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            image = {"src": "https://example.test/image.png", "width": 800}
            original = capture_page._exclusive_write

            def write_image_then_fail(path, data, study, on_created=None):
                original(path, data, study, on_created)
                if path.parent.name == "img":
                    raise OSError("synthetic close failure")

            with patch.object(capture_page, "_exclusive_write", side_effect=write_image_then_fail):
                result, output = self.run_main(root, self.page(images=[image]), images=1)
            self.assertEqual(result, 3)
            self.assertIn("PARTIAL", output)
            self.assertIn("raw/img/001-1.png", output)
            self.assertTrue((root / "raw/img/001-1.png").is_file())
            self.assertFalse((root / "raw/001-example-page.images.json").exists())

    def test_markdown_write_failure_after_exclusive_create_is_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            original = capture_page._exclusive_write

            def write_markdown_then_fail(path, data, study, on_created=None):
                original(path, data, study, on_created)
                if path.suffix == ".md":
                    raise OSError("synthetic close failure")

            with patch.object(capture_page, "_exclusive_write", side_effect=write_markdown_then_fail):
                result, output = self.run_main(root, self.page())
            self.assertEqual(result, 3)
            self.assertIn("PARTIAL", output)
            self.assertIn("raw/001-example-page.md", output)
            self.assertTrue((root / "raw/001-example-page.md").is_file())

    def test_manifest_write_failure_after_capture_is_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            image = {"src": "https://example.test/image.png", "width": 800}
            original = capture_page._exclusive_write
            def fail_manifest(path, data, study, on_created=None):
                if path.name.endswith(".images.json"):
                    raise OSError("synthetic manifest failure")
                return original(path, data, study, on_created)
            args = ["capture_page.py", str(root), "https://example.test/page", "--window-id", "123456", "--images", "1"]
            with patch.object(capture_page, "_exclusive_write", side_effect=fail_manifest):
                result, output = self.run_main(root, self.page(images=[image]), images=1)
            self.assertEqual(result, 3)
            self.assertIn("PARTIAL", output)
            self.assertTrue((root / "raw/001-example-page.md").is_file())
            self.assertTrue((root / "raw/img/001-1.png").is_file())
            self.assertFalse((root / "raw/001-example-page.images.json").exists())

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

    def test_urlopen_and_response_read_oserrors_use_screenshot_manifest(self):
        for failure in (OSError("urlopen failure"), OSError("response read failure")):
            with self.subTest(failure=str(failure)), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.study(root)
                image = {"src": "https://example.test/image.png", "width": 800}
                page = self.page(images=[image])
                payload = bytes((137, 80, 78, 71)) + b"x" * 2500

                class BrokenResponse:
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        return False
                    def read(self, size):
                        raise failure

                def screenshot(*args):
                    if "--output" in args:
                        Path(args[args.index("--output") + 1]).write_bytes(b"synthetic screenshot")
                    return ""

                args = ["capture_page.py", str(root), "https://example.test/page",
                        "--window-id", "123456", "--images", "1"]
                urlopen = patch.object(capture_page.urllib.request, "urlopen",
                                       side_effect=failure) if str(failure).startswith("urlopen") else \
                          patch.object(capture_page.urllib.request, "urlopen",
                                       return_value=BrokenResponse())
                with urlopen, patch.object(capture_page.time, "sleep"), \
                     patch.object(capture_page, "surf", side_effect=screenshot), \
                     patch.object(capture_page.sys, "argv", args), \
                     patch.object(capture_page, "open_page", return_value="123456"), \
                     patch.object(capture_page, "extract", return_value=page), \
                     patch("sys.stdout", new_callable=io.StringIO) as output:
                    result = capture_page.main()
                self.assertEqual(result, 0, output.getvalue())
                self.assertEqual((root / "raw/img/001-1.png").read_bytes(),
                                 b"synthetic screenshot")
                manifest = json.loads((root / "raw/001-example-page.images.json").read_text())
                self.assertEqual(manifest["images"][0]["method"], "surf_screenshot_fallback")

    def test_image_exclusive_write_failure_after_create_is_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            payload = bytes((137, 80, 78, 71)) + b"x" * 2500
            image = {"src": "https://example.test/image.png", "width": 800}
            original_fdopen = capture_page.os.fdopen

            class FailingStream:
                def __init__(self, stream):
                    self.stream = stream
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    self.stream.close()
                    raise OSError("synthetic close failure")
                def write(self, data):
                    self.stream.write(data[:5])
                    raise OSError("synthetic write failure")

            original_save = capture_page.save_image
            with patch.object(capture_page.os, "fdopen",
                              side_effect=lambda *args, **kwargs:
                              FailingStream(original_fdopen(*args, **kwargs))), \
                 patch.object(capture_page.urllib.request, "urlopen",
                              return_value=io.BytesIO(payload)):
                result, output = self.run_main(root, self.page(images=[image]), images=1,
                                               save_func=original_save)
            self.assertEqual(result, 3)
            self.assertIn("PARTIAL", output)
            target = root / "raw/img/001-1.png"
            self.assertEqual(target.read_bytes(), payload[:5])
            self.assertFalse((root / "raw/001-example-page.images.json").exists())

    def test_markdown_exclusive_write_failure_after_create_is_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.study(root)
            original_fdopen = capture_page.os.fdopen

            class FailingStream:
                def __init__(self, stream):
                    self.stream = stream
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    self.stream.close()
                    raise OSError("synthetic close failure")
                def write(self, data):
                    self.stream.write(data[:5])
                    raise OSError("synthetic write failure")

            with patch.object(capture_page.os, "fdopen",
                              side_effect=lambda *args, **kwargs:
                              FailingStream(original_fdopen(*args, **kwargs))):
                result, output = self.run_main(root, self.page())
            self.assertEqual(result, 3)
            self.assertIn("PARTIAL", output)
            target = root / "raw/001-example-page.md"
            self.assertEqual(target.read_bytes(), b"---\nt")
