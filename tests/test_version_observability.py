import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import kb_bootstrap
from kb_bootstrap.cli import main


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with patch.object(sys, "argv", ["kb-bootstrap", *args]), redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            result = main()
        except SystemExit as error:
            result = error.code
    return result, stdout.getvalue(), stderr.getvalue()


def make_kb(root, invalid=False):
    (root / "kb").mkdir()
    (root / "qmd/collections").mkdir(parents=True)
    (root / "qmd.json").write_text("{}\n", encoding="utf-8")
    (root / "qmd/collections/wiki.yaml").write_text(
        "name: test-wiki\npaths:\n  - ../../kb/\nexclude:\n  - raw/**\n", encoding="utf-8"
    )
    (root / "qmd/collections/raw.yaml").write_text(
        "name: test-raw\npaths:\n  - ../../kb/raw/\n", encoding="utf-8"
    )
    (root / "kb/raw").mkdir()
    frontmatter = "title: Missing type\n" if invalid else "type: Concept\n"
    (root / "kb/overview.md").write_text(f"---\n{frontmatter}---\n# Overview\n", encoding="utf-8")


def test_top_level_version_contract():
    result, stdout, stderr = run_cli("--version")
    assert result == 0
    assert stdout == f"kb-bootstrap {kb_bootstrap.__version__}\n"
    assert stderr == ""


def test_runtime_version_matches_pyproject():
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', metadata, re.MULTILINE)
    assert match is not None
    assert kb_bootstrap.__version__ == match.group(1)


def test_source_checkout_ignores_stale_metadata_and_consumer_access():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "source"
        consumer = root / "consumer"
        source.mkdir()
        consumer.mkdir()
        shutil.copytree(
            ROOT / "kb_bootstrap", source / "kb_bootstrap",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        (consumer / "pyproject.toml").write_text('[project]\nversion = "99.0.0"\n', encoding="utf-8")
        (consumer / "consumer_validator.py").write_text(
            'raise RuntimeError("consumer import is forbidden")\n', encoding="utf-8"
        )
        (consumer / "qmd.json").write_text("{}\n", encoding="utf-8")
        (consumer / "other-config.json").write_text("{}\n", encoding="utf-8")
        (consumer / "sitecustomize.py").write_text(
            "import os\nimport sys\nfrom pathlib import Path\n"
            "consumer = Path(os.environ['CONSUMER_ROOT']).resolve()\n"
            "blocked = {\n"
            "    consumer / 'pyproject.toml', consumer / 'qmd.json',\n"
            "    consumer / 'other-config.json',\n"
            "    consumer / 'kb_bootstrap-0.0.1.dist-info' / 'METADATA',\n"
            "}\n"
            "def audit(event, args):\n"
            "    if event == 'import' and args[0] == 'consumer_validator':\n"
            "        raise RuntimeError('consumer import is forbidden')\n"
            "    if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):\n"
            "        if Path(args[0]).resolve() in blocked:\n"
            "            raise RuntimeError('consumer file access is forbidden')\n"
            "sys.addaudithook(audit)\n",
            encoding="utf-8",
        )
        stale = consumer / "kb_bootstrap-0.0.1.dist-info"
        stale.mkdir()
        (stale / "METADATA").write_text("Name: kb-bootstrap\nVersion: 0.0.1\n", encoding="utf-8")
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join((str(source), str(consumer)))
        environment["CONSUMER_ROOT"] = str(consumer)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [sys.executable, "-m", "kb_bootstrap.cli", "--version"],
            cwd=consumer, env=environment, text=True, capture_output=True, check=False,
        )
    assert result.returncode == 0
    assert result.stdout == f"kb-bootstrap {kb_bootstrap.__version__}\n"
    assert result.stderr == ""


def test_runtime_version_module_uses_only_the_static_constant():
    source = (ROOT / "kb_bootstrap/__init__.py").read_text(encoding="utf-8")
    assert source == f'__version__ = "{kb_bootstrap.__version__}"\n'


def test_validate_reports_version_once_on_success_and_failure():
    for invalid, expected_code in ((False, 0), (True, 1)):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_kb(root, invalid=invalid)
            result, stdout, stderr = run_cli("validate", "--dir", str(root / "kb"), "--project-root", str(root))
        assert result == expected_code
        assert stderr == ""
        if invalid:
            assert "type must be a non-empty string" in stdout
        assert stdout.startswith(
            f"Validator: kb-bootstrap {kb_bootstrap.__version__}\n\n"
            "=== Canonical OKF v0.2 Profile Validation ===\n"
        )
        assert stdout.count(f"Validator: kb-bootstrap {kb_bootstrap.__version__}") == 1
        for section in (
            "=== Canonical Provenance/Freshness Profile ===",
            "=== kb-bootstrap Graph Integrity Extension ===",
            "=== QMD Collection Validation ===",
        ):
            assert section in stdout
