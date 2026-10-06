"""Verify generated assets from locally built distributions, not the checkout."""

import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
import venv
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ASSETS = {
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


def _assets_from_wheel(path):
    with zipfile.ZipFile(path) as archive:
        return {
            name[len("kb_bootstrap/") :]
            for name in archive.namelist()
            if name.startswith("kb_bootstrap/templates/")
        }


def _assets_from_sdist(path):
    with tarfile.open(path, "r:gz") as archive:
        return {
            "/".join(member.name.split("/", 2)[2:])
            for member in archive.getmembers()
            if member.isfile() and "/kb_bootstrap/templates/" in member.name
        }


class InstalledDistributionTests(unittest.TestCase):
    def test_wheel_and_sdist_include_generated_research_and_lesson_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "artifacts"
            output.mkdir()
            subprocess.run(
                [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            wheel = next(output.glob("*.whl"))
            sdist = next(output.glob("*.tar.gz"))
            with zipfile.ZipFile(wheel) as archive:
                wheel_names = archive.namelist()
            with tarfile.open(sdist, "r:gz") as archive:
                sdist_names = [member.name for member in archive.getmembers()]
            for archive_name, names in (("wheel", wheel_names), ("sdist", sdist_names)):
                with self.subTest(archive=archive_name):
                    self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))
                    self.assertFalse(any("/build/" in name or "/dist/" in name for name in names))
            for distribution, assets in (
                ("wheel", _assets_from_wheel(wheel)),
                ("sdist", _assets_from_sdist(sdist)),
            ):
                with self.subTest(distribution=distribution):
                    self.assertTrue(EXPECTED_ASSETS <= assets, EXPECTED_ASSETS - assets)
                    self.assertFalse(any("__pycache__" in item or item.endswith(".pyc") for item in assets))

    def test_installed_wheel_generates_research_and_lesson_assets_outside_checkout(self):
        self._assert_installed_artifact_generates_assets("wheel")

    def test_installed_sdist_generates_research_and_lesson_assets_outside_checkout(self):
        self._assert_installed_artifact_generates_assets("sdist")

    def _assert_installed_artifact_generates_assets(self, artifact_kind):
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            artifacts = temp_root / "artifacts"
            artifacts.mkdir()
            subprocess.run(
                [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(artifacts)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            artifact = next(artifacts.glob("*.whl" if artifact_kind == "wheel" else "*.tar.gz"))
            environment = temp_root / "venv"
            venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment)
            scripts = environment / ("Scripts" if os.name == "nt" else "bin")
            python = scripts / ("python.exe" if os.name == "nt" else "python")
            cli = scripts / ("kb-bootstrap.exe" if os.name == "nt" else "kb-bootstrap")
            subprocess.run(
                [str(python), "-m", "pip", "install", "--no-deps", "--no-index", "--no-build-isolation", str(artifact)],
                cwd=temp_root,
                check=True,
                capture_output=True,
                text=True,
            )
            outside = temp_root / "outside-source"
            outside.mkdir()
            target = outside / "synthetic-project"
            result = subprocess.run(
                [str(cli), "--target", str(target), "--with-project-lessons"],
                cwd=outside,
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": ""},
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
            module_path = subprocess.run(
                [str(python), "-c", "import kb_bootstrap; print(kb_bootstrap.__file__)"],
                cwd=outside,
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": ""},
            ).stdout.strip()
            try:
                Path(module_path).relative_to(environment)
            except ValueError:
                self.fail(f"import resolved outside installed environment: {module_path}")


if __name__ == "__main__":
    unittest.main()
