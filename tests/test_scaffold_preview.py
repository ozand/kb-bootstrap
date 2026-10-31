"""Synthetic CLI coverage for the ADR-046 read-only scaffold preview."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from unittest.mock import patch

from kb_bootstrap.cli import main
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


def test_preview_core_only_cli_selects_exact_layout_inventories(tmp_path):
    for layout in ("single", "umbrella"):
        target = tmp_path / ("cli-core-" + layout)
        result = cli("preview", "--target", target, "--type", layout, "--core-only")
        assert result.returncode == 1
        assert "RESULT: CHANGES REQUIRED" in result.stdout
        assert not target.exists()
        listed = [line.split(": ", 1)[1] for line in result.stdout.splitlines() if line.startswith("missing: ")]
        expected = [".agents/skills/kb-wiki-builder/SKILL.md", ".gitignore", "kb/raw/.gitkeep", "kb/research/.gitkeep", "kb/wiki/concepts/.gitkeep", "kb/wiki/entities/.gitkeep", "kb/wiki/reports/.gitkeep"]
        if layout == "umbrella":
            expected += ["kb/apps/.gitkeep", "kb/architecture/.gitkeep", "kb/systems/.gitkeep"]
        assert listed == sorted(expected)


def test_preview_cli_reports_matching_ordinary_scaffolds_both_layouts(tmp_path):
    for layout in ("single", "umbrella"):
        target = tmp_path / ("cli-ordinary-" + layout)
        files = qmd_payloads(layout, project_slug(target.name))
        files.update(_inventory_files(PACKAGE))
        for relative, payload in files.items():
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        before = sorted((p.relative_to(target).as_posix(), p.read_bytes()) for p in target.rglob("*") if p.is_file())
        result = cli("preview", "--target", target, "--type", layout)
        assert result.returncode == 0 and "RESULT: READY" in result.stdout
        assert f"matching={len(files)} missing=0 content differs=0 unsafe=0 unavailable=0" in result.stdout
        assert before == sorted((p.relative_to(target).as_posix(), p.read_bytes()) for p in target.rglob("*") if p.is_file())


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
    import sys
    monkeypatch.setattr(sys, "argv", ["kb-bootstrap", "preview", "--target", ""])
    with patch("kb_bootstrap.scaffold_preview.os.lstat", side_effect=AssertionError("filesystem inspected")), patch("kb_bootstrap.scaffold_preview.os.open", side_effect=AssertionError("file opened")):
        with pytest.raises(SystemExit) as error:
            main()
    assert error.value.code == 2


def test_preview_nonregular_expected_member_is_unsafe_without_open(tmp_path):
    target = tmp_path / "nonregular-member"
    target.mkdir()
    member = target / "qmd.json"
    member.mkdir(parents=True)
    with patch("kb_bootstrap.scaffold_repeat.os.open", side_effect=AssertionError("nonregular member opened")):
        output, code = preview(str(target), PACKAGE, "single")
    assert code == 1 and "unsafe: qmd.json" in output and "RESULT: BLOCKED" in output


def test_preview_unsafe_paths_block_before_content_open(tmp_path):
    target = tmp_path / "unsafe"
    target.mkdir()
    file = target / "qmd.json"
    file.symlink_to(tmp_path / "missing-target")
    with patch("kb_bootstrap.scaffold_repeat.os.open", side_effect=AssertionError("unsafe content opened")):
        out, code = preview(str(target), PACKAGE, "single")
    assert code == 1 and "unsafe:" in out and "RESULT: BLOCKED" in out
    assert str(target) not in out


def test_preview_symlink_root_and_ancestor_block_without_open(tmp_path):
    actual = tmp_path / "real"
    actual.mkdir()
    (actual / "qmd.json").write_text("synthetic", encoding="utf-8")
    for link in (tmp_path / "root-link", tmp_path / "ancestor-link"):
        link.symlink_to(actual, target_is_directory=True)
        selected = link if link.name == "root-link" else link / "child"
        with patch("kb_bootstrap.scaffold_repeat.os.open", side_effect=AssertionError("unsafe descendant opened")):
            output, code = preview(str(selected), PACKAGE, "single")
        assert code == 1 and "unsafe: target" in output
        assert str(actual) not in output


def test_preview_ancestor_symlink_and_nonregular_root_are_blocked(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    link = tmp_path / "link"
    link.symlink_to(actual, target_is_directory=True)
    out, code = preview(str(link / "child"), PACKAGE, "single")
    assert code == 1 and "unsafe: target" in out and str(actual) not in out
    regular_file = tmp_path / "not-a-directory"
    regular_file.write_text("x", encoding="utf-8")
    out = cli("preview", "--target", regular_file)
    assert out.returncode == 1 and "RESULT: BLOCKED" in out.stdout


def test_preview_unavailable_and_oversized_files_do_not_read_contents(tmp_path):
    target = tmp_path / "unavailable"
    files = ordinary(target)
    expected = next(iter(files))
    path = target / expected
    with patch("kb_bootstrap.scaffold_repeat.os.open", side_effect=PermissionError):
        out, code = preview(str(target), PACKAGE, "single")
    assert code == 1 and "unavailable: " + expected in out and "RESULT: BLOCKED" in out
    path.write_bytes(b"x" * (len(files[expected]) + 1))
    original_open = os.open
    def forbid_oversized(file, flags, *args, **kwargs):
        if Path(file) == path:
            raise AssertionError("oversized file opened")
        return original_open(file, flags, *args, **kwargs)
    with patch("kb_bootstrap.scaffold_repeat.os.open", side_effect=forbid_oversized):
        out, code = preview(str(target), PACKAGE, "single")
    assert code == 1 and "content differs: " + expected in out


def test_preview_equal_size_reads_respect_each_file_and_total_payload_bounds(tmp_path):
    target = tmp_path / "bounded"
    expected = ordinary(target)
    original_open, original_read, original_close = os.open, os.read, os.close
    descriptor_paths = {}
    requested = {}
    returned = {}
    def observe_open(file, flags, *args, **kwargs):
        descriptor = original_open(file, flags, *args, **kwargs)
        descriptor_paths[descriptor] = Path(file).relative_to(target).as_posix()
        return descriptor
    def observe_read(descriptor, size):
        name = descriptor_paths[descriptor]
        requested[name] = requested.get(name, 0) + size
        data = original_read(descriptor, size)
        returned[name] = returned.get(name, 0) + len(data)
        return data
    def observe_close(descriptor):
        descriptor_paths.pop(descriptor, None)
        return original_close(descriptor)
    with patch("kb_bootstrap.scaffold_repeat.os.open", side_effect=observe_open), patch("kb_bootstrap.scaffold_repeat.os.read", side_effect=observe_read), patch("kb_bootstrap.scaffold_repeat.os.close", side_effect=observe_close):
        out, code = preview(str(target), PACKAGE, "single")
    assert code == 0
    assert all(requested[name] <= len(expected[name]) for name in requested)
    assert all(returned[name] <= len(expected[name]) for name in returned)
    assert sum(returned.values()) <= sum(map(len, expected.values()))
    assert f"matching={len(expected)} missing=0 content differs=0 unsafe=0 unavailable=0" in out


def test_preview_invokes_no_external_or_mutating_operations(tmp_path):
    target = tmp_path / "absent" / "target"
    import builtins
    import socket
    original_builtin_open, original_path_open = builtins.open, Path.open
    def check_builtin_open(file, mode="r", *args, **kwargs):
        assert not any(flag in mode for flag in "wax+"), "write-mode builtin open invoked"
        return original_builtin_open(file, mode, *args, **kwargs)
    def check_path_open(path, mode="r", *args, **kwargs):
        assert not any(flag in mode for flag in "wax+"), "write-mode Path.open invoked"
        return original_path_open(path, mode, *args, **kwargs)
    with patch("subprocess.run", side_effect=AssertionError("subprocess invoked")), patch("socket.create_connection", side_effect=AssertionError("network invoked")), patch("socket.socket.connect", side_effect=AssertionError("network invoked")), patch("shutil.copytree", side_effect=AssertionError("copy invoked")), patch("pathlib.Path.mkdir", side_effect=AssertionError("directory created")), patch("builtins.open", side_effect=check_builtin_open), patch("pathlib.Path.open", new=check_path_open), patch("pathlib.Path.write_bytes", side_effect=AssertionError("write invoked")), patch("pathlib.Path.write_text", side_effect=AssertionError("write invoked")), patch("pathlib.Path.touch", side_effect=AssertionError("touch invoked")), patch("pathlib.Path.unlink", side_effect=AssertionError("unlink invoked")), patch("os.replace", side_effect=AssertionError("replace invoked")), patch("shutil.copy2", side_effect=AssertionError("copy invoked")):
        output, status = preview(str(target), PACKAGE, "single")
    assert status == 1 and "RESULT: CHANGES REQUIRED" in output
    assert not target.parent.exists()


def test_preview_whitespace_target_is_not_trimmed(monkeypatch):
    import sys
    observed = []
    monkeypatch.setattr(sys, "argv", ["kb-bootstrap", "preview", "--target", "   "])
    with patch("kb_bootstrap.scaffold_preview.preview", side_effect=lambda target, *args: (observed.append(target) or ("RESULT: CHANGES REQUIRED", 1))):
        assert main() == 1
    assert observed == ["   "]


def _tree_snapshot(root):
    rows = []
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        relative = path.relative_to(root).as_posix()
        rows.append((relative, info.st_mode, info.st_size, info.st_mtime_ns, getattr(info, "st_file_attributes", 0), path.read_bytes() if path.is_file() and not path.is_symlink() else None))
    return tuple(rows)


def test_preview_is_repeatable_and_writes_nothing(tmp_path):
    target = tmp_path / "repeat"
    ordinary(target)
    canary = target / "unlisted"
    canary.write_bytes(b"stable")
    before_target = _tree_snapshot(target)
    before_parent = _tree_snapshot(tmp_path)
    first = preview(str(target), PACKAGE, "single")
    second = preview(str(target), PACKAGE, "single")
    assert first == second
    assert before_target == _tree_snapshot(target)
    assert before_parent == _tree_snapshot(tmp_path)
