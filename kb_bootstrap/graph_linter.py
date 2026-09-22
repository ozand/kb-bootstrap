"""Validate Markdown links as a directed knowledge-base graph."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple, Union

import networkx as nx

from .canonical_profile import RESERVED_FILENAMES, _traverses_symlink


LINK_PATTERN = re.compile(r"\[.*?\]\((.*?\.md)(?:#.*?)?\)")
DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[/\\]")
ENCODED_UNSAFE_PATTERN = re.compile(
    r"%(?:0[0-9a-f]|1[0-9a-f]|2e|2f|5c|7f)", re.IGNORECASE
)
DEFAULT_IGNORED_DIRS = ("raw", "lessons")


def _target_path(
    link: str, source: Path, base_path: Path
) -> Tuple[Optional[str], Optional[str]]:
    """Return a canonical-root-contained POSIX target or a safe error marker."""
    if (
        "\x00" in link
        or "\\" in link
        or DRIVE_PATTERN.match(link)
        or link.startswith("//")
        or ENCODED_UNSAFE_PATTERN.search(link)
    ):
        return None, "[unsafe link target]"
    candidate = base_path / link.lstrip("/") if link.startswith("/") else source.parent / link
    normalized = Path(os.path.normpath(str(candidate)))
    try:
        relative = normalized.relative_to(base_path)
    except ValueError:
        return None, "[unsafe link target]"
    if _traverses_symlink(normalized):
        return None, "[unsafe link target]"
    return relative.as_posix(), None


def analyze_graph(
    base_dir: Union[os.PathLike, str] = "docs",
    ignore_dirs: Iterable[str] = DEFAULT_IGNORED_DIRS,
) -> Tuple[nx.DiGraph, Path]:
    """Build a Markdown link graph without inspecting paths outside the root."""
    raw_base_path = Path(base_dir).absolute()
    base_path = raw_base_path.resolve()
    ignored = {directory.casefold() for directory in ignore_dirs}
    graph = nx.DiGraph()
    markdown_files = []
    eligible_targets: Set[str] = set()
    invalid_targets: Set[str] = set()
    if _traverses_symlink(raw_base_path) or not base_path.is_dir():
        graph.graph["invalid_targets"] = {"[unsafe canonical root]"}
        return graph, base_path

    for root, dirs, files in os.walk(base_path):
        dirs[:] = [directory for directory in dirs if directory.casefold() not in ignored]
        for filename in files:
            if not filename.casefold().endswith(".md"):
                continue
            absolute = Path(root) / filename
            relative = absolute.relative_to(base_path).as_posix()
            graph.add_node(relative)
            markdown_files.append((absolute, relative))
            if filename.casefold() not in RESERVED_FILENAMES and not absolute.is_symlink():
                eligible_targets.add(relative)

    for absolute, relative in markdown_files:
        if absolute.is_symlink() or _traverses_symlink(absolute):
            invalid_targets.add("[unsafe source path]")
            continue
        try:
            content = absolute.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            invalid_targets.add("[unreadable source path]")
            continue
        for link in LINK_PATTERN.findall(content):
            target, error = _target_path(link, absolute, base_path)
            target = error or target
            assert target is not None
            if error or target not in eligible_targets:
                invalid_targets.add(target)
                continue
            if target != relative:
                graph.add_edge(relative, target)

    graph.graph["invalid_targets"] = invalid_targets
    return graph, base_path


def dead_links(graph: nx.DiGraph, base_dir: Union[os.PathLike, str]) -> Set[str]:
    """Return unsafe, missing, reserved, or excluded graph targets."""
    invalid_targets = graph.graph.get("invalid_targets")
    if invalid_targets is not None:
        return set(invalid_targets)
    base_path = Path(base_dir)
    return {target for _, target in graph.edges() if not (base_path / target).exists()}


def orphan_nodes(graph: nx.DiGraph, invalid_targets: Optional[Set[str]] = None) -> List[str]:
    invalid_targets = invalid_targets or set()
    return [node for node, degree in graph.in_degree() if degree == 0 and node not in invalid_targets]


def format_report(graph: nx.DiGraph, base_dir: Union[os.PathLike, str]) -> str:
    invalid_targets = dead_links(graph, base_dir)
    orphans = orphan_nodes(graph, invalid_targets)
    components = list(nx.weakly_connected_components(graph))
    lines = ["=== KB Graph Analysis Report ===", f"Nodes (MD Files): {graph.number_of_nodes()}", f"Edges (Links):    {graph.number_of_edges()}", "", f"Connected Subgraphs: {len(components)}", ""]
    if invalid_targets:
        lines.append(f"DEAD LINKS ({len(invalid_targets)}):")
        lines.extend(f"   - {target}" for target in sorted(invalid_targets)[:10])
    else:
        lines.append("DEAD LINKS: 0")
    lines.extend(["", f"ORPHANS (0 Incoming Links): {len(orphans)}"])
    lines.extend(f"   - {node}" for node in orphans[:5])
    return "\n".join(lines)


def validate(base_dir: Union[os.PathLike, str] = "docs") -> Tuple[str, bool]:
    graph, base_path = analyze_graph(base_dir)
    invalid_targets = dead_links(graph, base_path)
    return format_report(graph, base_path), not invalid_targets
