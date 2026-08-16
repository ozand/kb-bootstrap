"""Validate Markdown links as a directed knowledge-base graph."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple, Union

import networkx as nx


LINK_PATTERN = re.compile(r"\[.*?\]\((.*?\.md)(?:#.*?)?\)")
DEFAULT_IGNORED_DIRS = ("raw",)


def analyze_graph(
    base_dir: Union[os.PathLike, str] = "docs",
    ignore_dirs: Iterable[str] = DEFAULT_IGNORED_DIRS,
) -> Tuple[nx.DiGraph, Path]:
    """Build a Markdown link graph, preserving the original linter behavior."""
    base_path = Path(base_dir)
    ignored = set(ignore_dirs)
    graph = nx.DiGraph()

    markdown_files = []
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [directory for directory in dirs if directory not in ignored]
        for filename in files:
            if filename.endswith(".md"):
                absolute = Path(root) / filename
                relative = os.path.relpath(absolute, base_path)
                graph.add_node(relative)
                markdown_files.append((absolute, relative))

    for absolute, relative in markdown_files:
        content = absolute.read_text(encoding="utf-8")
        for link in LINK_PATTERN.findall(content):
            target = os.path.normpath(os.path.join(str(absolute.parent), link))
            target_relative = os.path.relpath(target, base_path)
            if target_relative != relative:
                graph.add_edge(relative, target_relative)

    return graph, base_path


def dead_links(graph: nx.DiGraph, base_dir: Union[os.PathLike, str]) -> Set[str]:
    """Return unique link targets that do not exist below *base_dir*."""
    base_path = Path(base_dir)
    return {
        target
        for _, target in graph.edges()
        if not (base_path / target).exists()
    }


def orphan_nodes(graph: nx.DiGraph, invalid_targets: Optional[Set[str]] = None) -> List[str]:
    """Return nodes with no incoming links, excluding dead-link targets."""
    invalid_targets = invalid_targets or set()
    return [
        node
        for node, degree in graph.in_degree()
        if degree == 0 and node not in invalid_targets
    ]


def format_report(graph: nx.DiGraph, base_dir: Union[os.PathLike, str]) -> str:
    """Format the human-readable validation report."""
    invalid_targets = dead_links(graph, base_dir)
    orphans = orphan_nodes(graph, invalid_targets)
    components = list(nx.weakly_connected_components(graph))
    lines = [
        "=== KB Graph Analysis Report ===",
        f"Nodes (MD Files): {graph.number_of_nodes()}",
        f"Edges (Links):    {graph.number_of_edges()}",
        "",
        f"Connected Subgraphs: {len(components)}",
        "",
    ]
    if invalid_targets:
        lines.append(f"DEAD LINKS ({len(invalid_targets)}):")
        lines.extend(f"   - {target}" for target in sorted(invalid_targets)[:10])
    else:
        lines.append("DEAD LINKS: 0")
    lines.extend(["", f"ORPHANS (0 Incoming Links): {len(orphans)}"])
    lines.extend(f"   - {node}" for node in orphans[:5])
    return "\n".join(lines)


def validate(base_dir: Union[os.PathLike, str] = "docs") -> Tuple[str, bool]:
    """Return ``(report, is_valid)``; dead links make validation fail."""
    graph, base_path = analyze_graph(base_dir)
    invalid_targets = dead_links(graph, base_path)
    return format_report(graph, base_path), not invalid_targets
