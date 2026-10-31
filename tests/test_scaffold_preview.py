"""Synthetic CLI coverage for the ADR-046 read-only scaffold preview."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from kb_bootstrap.scaffold_preview import preview
from kb_bootstrap.scaffold_repeat import _inventory_files, qmd_payloads
from kb_bootstrap.qmd_names import project_slug

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "kb_bootstrap"


def cli(*args):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run([sys.executable, "-m", "kb_bootstrap.cli", *map(str, args)], cwd=ROOT, env=env, capture_output=True, text=True)


def ordinary(root):
    files = qmd_payloads("single", project_slug(root.name))
    files.update(_inventory_files(PACKAGE))
    for relative, payload in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return files


def test_preview_requires_explicit_target_and_selects_one_layout_mode(tmp_path):
    assert cli("preview").returncode == 2
    assert cli("preview", "--target", "", "--core-only").returncode == 2
    assert cli("preview", "--target", str(tmp_path / "missing"), "--with-project-lessons").returncode == 2


def test_preview_reports_complete_ordinary_inventory(tmp_path):
    for layout in ("single", "umbrella"):
        target = tmp_path / layout
        expected = ordinary(target)
        output, status = preview(str(target), PACKAGE, layout)
        assert status == 0
        paths = [line.split(": ", 1)[1] for line in output.splitlines() if line.startswith("matching: ")]
        assert paths == sorted(expected)
        assert "RESULT: READY" in output


def test_preview_core_only_uses_exact_adr039_inventory(tmp_path):
    for layout in ("single", "umbrella"):
        target = tmp_path / ("core-" + layout)
        output, status = preview(str(target), PACKAGE, layout, core_only=True)
        paths = [line.split(": ", 1)[1] for line in output.splitlines() if line.startswith("missing: ")]
        common = [".agents/skills/kb-wiki-builder/SKILL.md", ".gitignore", "kb/raw/.gitkeep", "kb/research/.gitkeep", "kb/wiki/concepts/.gitkeep", "kb/wiki/entities/.gitkeep", "kb/wiki/reports/.gitkeep"]
        expected = common + (["kb/apps/.gitkeep", "kb/architecture/.gitkeep", "kb/systems/.gitkeep"] if layout == "umbrella" else [])
        assert paths == sorted(expected)
        assert status == 1 and "RESULT: CHANGES REQUIRED" in output


def test_preview_missing_and_partial_targets_are_read_only(tmp_path):
    absent = tmp_path / "parent" / "new-root"
    out = cli("preview", "--target", absent)
    assert out.returncode == 1 and "RESULT: CHANGES REQUIRED" in out.stdout
    assert not absent.parent.exists()
    target = tmp_path / "partial"
    files = ordinary(target)
    (target / next(iter(files))).unlink()
    out = cli("preview", "--target", target)
    assert out.returncode == 1 and "missing:" in out.stdout


def test_preview_differences_are_sanitized_and_unlisted_paths_ignored(tmp_path):
    target = tmp_path / "sensitive-consumer-name"
    files = ordinary(target)
    edited = next(iter(files))
    (target / edited).write_bytes(b"X" * len(files[edited]))
    canary = target / "private-canary.txt"
    canary.write_text("DO NOT READ OR REPORT", encoding="utf-8")
    before = canary.read_bytes()
    out = cli("preview", "--target", target)
    assert out.returncode == 1 and "content differs: " + edited in out.stdout
    assert "DO NOT READ" not in out.stdout and str(target) not in out.stdout
    assert "private-canary" not in out.stdout and canary.read_bytes() == before


def test_preview_rejects_literal_empty_before_filesystem_access(monkeypatch, tmp_path):
    # Argument rejection occurs in argparse before preview/path metadata calls.
    out = cli("preview", "--target", "")
    assert out.returncode == 2
    assert "must not be empty" in out.stderr
    assert str(tmp_path) not in out.stderr


def test_preview_unsafe_paths_block_before_content_open(tmp_path):
    target = tmp_path / "unsafe"
    target.mkdir()
    file = target / "qmd.json"
    file.symlink_to(tmp_path / "missing-target")
    out, code = preview(str(target), PACKAGE, "single")
    assert code == 1 and "unsafe:" in out and "RESULT: BLOCKED" in out
    assert str(target) not in out


def test_preview_is_repeatable_and_writes_nothing(tmp_path):
    target = tmp_path / "repeat"
    ordinary(target)
    canary = target / "unlisted"
    canary.write_bytes(b"stable")
    snapshot = sorted((p.relative_to(target).as_posix(), p.read_bytes()) for p in target.rglob("*") if p.is_file())
    first = preview(str(target), PACKAGE, "single")
    second = preview(str(target), PACKAGE, "single")
    assert first == second
    assert snapshot == sorted((p.relative_to(target).as_posix(), p.read_bytes()) for p in target.rglob("*") if p.is_file())
