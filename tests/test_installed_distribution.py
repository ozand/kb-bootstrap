"""Verify built distributions preserve tracked templates and run outside the checkout."""

import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import venv
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_TIMEOUT = 180
COMMAND_TIMEOUT = 60

# These independent contract files complement the exhaustive tracked-template
# inventory: they assert important research/lesson content, not just filenames.
REQUIRED_ASSETS = {
    "templates/skills/market-research/SKILL.md",
    "templates/skills/market-research/assets/brief-template.md",
    "templates/skills/market-research/assets/report-template.md",
    "templates/skills/market-research/evals/evals.json",
    "templates/skills/market-research/references/sources.md",
    "templates/skills/market-research/scripts/new_research.py",
    "templates/skills/market-research/scripts/check_research.py",
    "templates/skills/market-research/scripts/extract_markdown.js",
    "templates/lessons/SCHEMA.md",
    "templates/lessons/index.yaml",
    "templates/lessons/lesson-stores.json",
}


def _run(command, *, cwd, env=None, timeout=COMMAND_TIMEOUT, on_timeout=None):
    try:
        return subprocess.run(
            command, cwd=cwd, env=env, check=True, capture_output=True,
            text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        if on_timeout is not None:
            on_timeout()
        raise AssertionError(f"Command timed out after {timeout}s: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise AssertionError(
            f"Command failed ({exc.returncode}): {command[0]}\n"
            f"stdout: {exc.stdout[-4000:]}\nstderr: {exc.stderr[-4000:]}"
        ) from exc


def _tracked_templates():
    listing = _run(
        ["git", "ls-files", "--", "kb_bootstrap/templates"],
        cwd=ROOT,
    ).stdout
    return {
        (line[len("kb_bootstrap/") :] if line.startswith("kb_bootstrap/") else line).replace("\\", "/")
        for line in listing.splitlines()
        if line
    }


def _asset_members(artifact, kind):
    prefix = "kb_bootstrap/templates/"
    if kind == "wheel":
        with zipfile.ZipFile(artifact) as archive:
            return {
                name[len("kb_bootstrap/") :]
                for name in archive.namelist()
                if name.startswith(prefix) and not name.endswith("/")
            }, archive.namelist()
    with tarfile.open(artifact, "r:gz") as archive:
        members = archive.getmembers()
    names = [member.name for member in members]
    assets = {
        "/".join(member.name.split("/", 2)[2:])
        for member in members
        if member.isfile() and "/kb_bootstrap/templates/" in member.name
    }
    return assets, names


def _build_input(destination):
    """Copy only tracked build inputs; never copy local runtime or untracked state."""
    tracked = _run(
        ["git", "ls-files", "-z", "--", "pyproject.toml", "README.md", "MANIFEST.in", "kb_bootstrap"],
        cwd=ROOT,
    ).stdout
    paths = [
        item for item in tracked.split("\x00")
        if item and "__pycache__" not in item and not item.endswith(".pyc")
    ]
    for relative in paths:
        source = ROOT / relative
        if source.is_file():
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return destination


class InstalledDistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("git") is None:
            raise unittest.SkipTest("git is required to enumerate tracked template inputs")
        import importlib.util

        if importlib.util.find_spec("build") is None:
            raise unittest.SkipTest(
                "optional test tool 'build' is unavailable; install the project build tooling to run distribution tests"
            )
        try:
            importlib.import_module("build")
        except Exception as exc:
            raise RuntimeError("build module is discoverable but cannot be imported") from exc
        cls.expected_templates = _tracked_templates()
        cls.preserve_temp = False
        cls.temp_context = tempfile.TemporaryDirectory()
        cls.temp_root = Path(cls.temp_context.name)
        cls.temp_context._finalizer.detach()
        cls.source_copy = _build_input(cls.temp_root / "source")
        cls.artifacts = cls.temp_root / "artifacts"
        cls.artifacts.mkdir()
        try:
            _run(
                [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(cls.artifacts)],
                cwd=cls.source_copy,
                timeout=BUILD_TIMEOUT,
                on_timeout=lambda: setattr(cls, "preserve_temp", True),
            )
        except (AssertionError, OSError) as exc:
            raise RuntimeError(f"Distribution build failed with build tooling present: {exc}") from exc

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "temp_root") and not getattr(cls, "preserve_temp", False):
            shutil.rmtree(cls.temp_root, ignore_errors=True)

    def test_timeout_preserves_owned_working_directory(self):
        from unittest.mock import patch

        timed_out = []
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("child", 1)):
            with self.assertRaisesRegex(AssertionError, "timed out"):
                _run(["child"], cwd=ROOT, timeout=1, on_timeout=lambda: timed_out.append(True))
        self.assertEqual([True], timed_out)

    def test_build_tool_preflight_skips_only_when_module_is_absent(self):
        from unittest.mock import patch

        with patch("importlib.util.find_spec", return_value=None):
            with self.assertRaises(unittest.SkipTest):
                InstalledDistributionTests.setUpClass()
        with patch("importlib.util.find_spec", return_value=object()), patch(
            "importlib.import_module", side_effect=ImportError("broken build install")
        ):
            with self.assertRaisesRegex(RuntimeError, "discoverable but cannot be imported"):
                InstalledDistributionTests.setUpClass()

    def test_wheel_and_sdist_include_tracked_templates_without_build_artifacts(self):
        wheel = next(self.artifacts.glob("*.whl"))
        sdist = next(self.artifacts.glob("*.tar.gz"))
        for kind, artifact in (("wheel", wheel), ("sdist", sdist)):
            assets, names = _asset_members(artifact, kind)
            with self.subTest(distribution=kind):
                self.assertEqual(self.expected_templates, assets)
                self.assertTrue(REQUIRED_ASSETS <= assets)
                self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))
                self.assertFalse(any("/build/" in name or "/dist/" in name for name in names))

    def test_installed_wheel_generates_research_and_lesson_assets_outside_checkout(self):
        self._assert_installed_artifact_generates_assets("wheel")

    def test_installed_sdist_generates_research_and_lesson_assets_outside_checkout(self):
        self._assert_installed_artifact_generates_assets("sdist")

    def _assert_installed_artifact_generates_assets(self, kind):
        artifact = next(self.artifacts.glob("*.whl" if kind == "wheel" else "*.tar.gz"))
        temp_root = Path(tempfile.mkdtemp(prefix=f"kb-bootstrap-{kind}-"))
        preserve_temp = []
        self.addCleanup(
            lambda: None if preserve_temp else shutil.rmtree(temp_root, ignore_errors=True)
        )
        environment = temp_root / "venv"
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment)
        scripts = environment / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        cli = scripts / ("kb-bootstrap.exe" if os.name == "nt" else "kb-bootstrap")
        _run(
            [str(python), "-m", "pip", "install", "--no-deps", "--no-index", "--no-build-isolation", str(artifact)],
            cwd=temp_root,
            on_timeout=lambda: preserve_temp.append(True),
        )
        outside = temp_root / "outside-source"
        outside.mkdir()
        target = outside / "synthetic-project"
        result = _run(
            [str(cli), "--target", str(target), "--with-project-lessons"],
            cwd=outside,
            env={**os.environ, "PYTHONPATH": ""},
            on_timeout=lambda: preserve_temp.append(True),
        )
        self.assertIn("kb-capture", result.stdout)
        self.assertIn("market-research", result.stdout)
        for relative in (
            ".agents/skills/market-research/SKILL.md",
            ".agents/skills/market-research/assets/brief-template.md",
            ".agents/skills/market-research/scripts/new_research.py",
            "kb/lessons/SCHEMA.md",
            "kb/lessons/index.yaml",
            "lesson-stores.json",
            ".agents/skills/kb-capture/SKILL.md",
        ):
            with self.subTest(asset=relative):
                self.assertTrue((target / relative).is_file(), relative)
        module_path = _run(
            [str(python), "-c", "import kb_bootstrap; print(kb_bootstrap.__file__)"],
            cwd=outside,
            env={**os.environ, "PYTHONPATH": ""},
            on_timeout=lambda: preserve_temp.append(True),
        ).stdout.strip()
        try:
            Path(module_path).relative_to(environment)
        except ValueError:
            self.fail(f"import resolved outside installed environment: {module_path}")


if __name__ == "__main__":
    unittest.main()
