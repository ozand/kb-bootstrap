"""Read-only inspection of an optional local GLiNER2 peer installation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Optional, Tuple, Union

from .canonical_profile import _traverses_symlink


def inspect_gliner_environment(
    model_dir: Optional[Union[str, Path]] = None,
) -> Tuple[str, bool]:
    """Inspect this Python process and an explicit model path; run no child process."""
    lines = ["=== Optional GLiNER2 Local Setup ==="]
    errors = []
    compatible = sys.version_info[:2] >= (3, 10)
    lines.append("python: compatible" if compatible else "python: requires 3.10+")
    if not compatible:
        errors.append("optional peer requires Python 3.10 or newer")
    try:
        available = importlib.util.find_spec("gliner2") is not None
    except (ImportError, ValueError, AttributeError):
        available = False
    lines.append("gliner2: available (not imported)" if available else "gliner2: not installed")
    if not available:
        errors.append("optional GLiNER2 runtime is not installed in this interpreter")

    if model_dir is None:
        lines.append("model: not supplied")
        errors.append("provide an explicit local model directory")
    else:
        model = Path(model_dir).absolute()
        if _traverses_symlink(model) or not model.is_dir():
            lines.append("model: unavailable or unsafe")
            errors.append("explicit local model directory is unavailable or unsafe")
        else:
            config = model / "config.json"
            if _traverses_symlink(config) or not config.is_file():
                lines.append("model: incomplete")
                errors.append("local checkpoint config is unavailable or unsafe")
            else:
                lines.append("model: local config present (checkpoint not verified)")

    lines.extend(f"ERROR: {error}" for error in sorted(errors))
    lines.append("RESULT: BLOCKED" if errors else "RESULT: OK (paths present; checkpoint unverified)")
    lines.append("network isolation: not tested; model loading: not tested")
    return "\n".join(lines), not errors
