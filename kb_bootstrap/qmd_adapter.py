"""Explicit lexical QMD 2.8.3 adapter (ADR-018)."""
from __future__ import annotations
import json
import math
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, unquote
import yaml
from .bounded_process import run_bounded
from .local_retrieval import checked_root, relative_markdown, safe_components, bounded_text

NAME = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
MODEL_DEFAULTS = {
    "embed": "hf:ggml-org/embeddinggemma-300M-GGUF/embeddinggemma-300M-Q8_0.gguf",
    "generate": "hf:tobil/qmd-query-expansion-1.7B-gguf/qmd-query-expansion-1.7B-q4_k_m.gguf",
    "rerank": "hf:ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF/qwen3-reranker-0.6b-q8_0.gguf",
}


def failed(reason, absent=False):
    return {"status": "OPTIONAL_UNAVAILABLE" if absent else "FAILED",
            "results": [], "reason": reason}, 1


def installed_launch():
    executable = shutil.which("qmd")
    if executable is None:
        return None, "executable_absent"
    path = Path(executable)
    if path.suffix.lower() in (".cmd", ".bat"):
        # Standard npm layout; never execute CMD argument interpolation.
        package = path.parent / "node_modules/@tobilu/qmd"
        script = package / "dist/cli/qmd.js"
        node = shutil.which("node")
        try:
            manifest = json.loads((package / "package.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None, "launcher_unsupported"
        if not node or manifest.get("name") != "@tobilu/qmd" or manifest.get("version") != "2.8.3" or not script.is_file():
            return None, "launcher_unsupported"
        return [node, str(script)], ""
    return [executable], ""

def state_environment(state, index, collection, root):
    state, error = checked_root(state)
    if error or not NAME.fullmatch(index) or not NAME.fullmatch(collection):
        return None, "state_invalid"
    config = state / "config" / (index + ".yml")
    database = state / "cache/qmd" / (index + ".sqlite")
    for path in (config, database):
        if not safe_components(path) or not path.is_file():
            return None, "state_unavailable"
    try:
        if config.stat().st_size > 65536:
            return None, "config_invalid"
        raw = config.read_text(encoding="utf-8")
        # Aliases/anchors and arbitrary YAML objects are not configuration authority.
        events = list(yaml.parse(raw))
        if len(events) > 1024 or any(isinstance(e, yaml.AliasEvent) or getattr(e, "anchor", None) for e in events):
            return None, "config_invalid"
        data = yaml.safe_load(raw)
    except (OSError, UnicodeError, yaml.YAMLError, RecursionError):
        return None, "config_invalid"
    if not isinstance(data, dict) or set(data) - {"collections", "models"} or "collections" not in data:
        return None, "config_invalid"
    models = data.get("models", {})
    if not isinstance(models, dict) or any(k not in MODEL_DEFAULTS or v != MODEL_DEFAULTS[k] for k, v in models.items()):
        return None, "config_invalid"
    collections = data["collections"]
    if not isinstance(collections, dict) or set(collections) != {collection}:
        return None, "collection_invalid"
    spec = collections[collection]
    if not isinstance(spec, dict) or set(spec) - {"path", "pattern", "ignore"}:
        return None, "config_invalid"
    if spec.get("pattern") != "**/*.md" or not isinstance(spec.get("path"), str):
        return None, "config_invalid"
    configured, error = checked_root(spec["path"])
    if error or configured != root:
        return None, "collection_invalid"
    ignores = spec.get("ignore", [])
    if not isinstance(ignores, list) or not all(isinstance(x, str) for x in ignores):
        return None, "config_invalid"
    env = {k: v for k, v in os.environ.items() if not (k.startswith("QMD_") or k.startswith("XDG_") or k == "INDEX_PATH" or k.startswith("NODE_"))}
    env.update(QMD_CONFIG_DIR=str(state / "config"), XDG_CACHE_HOME=str(state / "cache"), INDEX_PATH=str(database))
    return env, ""

def validate_records(payload, collection, root, limit, index=None):
    if not isinstance(payload, list) or len(payload) > limit:
        return None
    records = []
    for item in payload:
        if not isinstance(item, dict):
            return None
        uri, title, score = item.get("file"), item.get("title"), item.get("score")
        if not isinstance(uri, str) or not isinstance(title, str) or not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score):
            return None
        if "%" in uri or "\x00" in uri:
            return None
        parsed = urlsplit(uri)
        if parsed.scheme != "qmd" or parsed.netloc != collection or parsed.fragment or (parsed.query and (index is None or parsed.query != "index=" + index)):
            return None
        relative = relative_markdown(unquote(parsed.path.lstrip("/")))
        if relative is None or parsed.path.startswith("//"):
            return None
        target = root.joinpath(*relative.parts)
        if not safe_components(target) or not target.is_file():
            return None
        records.append({"collection": collection, "path": relative.as_posix(),
                        "title": bounded_text(title), "score": score,
                        "layer": "canonical-selection", "index_freshness": "unknown",
                        "source_verification": "unknown"})
    return records


def search_qmd_bounded(query, directory, collection, index, state_dir, limit=10):
    import unicodedata
    if not isinstance(query, str) or not query or any(unicodedata.category(c) == "Cc" for c in query) or len(query.encode("utf-8")) > 512 or not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        return failed("arguments_invalid")
    root, error = checked_root(directory)
    if error:
        return failed(error)
    launch, error = installed_launch()
    if error:
        return failed(error, error == "executable_absent")
    env, error = state_environment(state_dir, index, collection, root)
    if error:
        return failed(error)
    scratch = tempfile.mkdtemp(prefix="kb-qmd-cwd-")
    uncertain = False
    try:
        version, error = run_bounded(launch + ["--version"], scratch, env)
        if error:
            uncertain = error in {"timeout", "output_limit", "termination_unconfirmed"}
            return failed(error)
        if not re.fullmatch(rb"qmd 2\.8\.3(?: \([0-9a-f]{7,40}\))?\r?\n?", version):
            return failed("version_mismatch")
        output, error = run_bounded(launch + ["--index", index, "search", "-c", collection, "--format", "json", "-n", str(limit), "--", query], scratch, env)
        if error:
            uncertain = error in {"timeout", "output_limit", "termination_unconfirmed"}
            return failed(error)
    finally:
        if not uncertain:
            shutil.rmtree(scratch)
    try:
        payload = json.loads(output.decode("utf-8"))
        records = validate_records(payload, collection, root, limit, index)
    except (ValueError, UnicodeError, OSError, OverflowError):
        return failed("records_invalid")
    if records is None:
        return failed("records_invalid")
    report = {"status": "OK", "results": records}
    if len(json.dumps(report, ensure_ascii=False).encode("utf-8")) + 1 > 262144:
        return failed("output_limit")
    return report, 0

