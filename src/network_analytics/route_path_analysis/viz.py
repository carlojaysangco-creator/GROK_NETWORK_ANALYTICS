"""RPA path visualization artifacts."""

from __future__ import annotations

import re
from pathlib import Path

import networkx as nx

from network_analytics.shared.topology_viz import render_path_on_graph

from .contracts import PathMetric


def _safe_name(*parts: str) -> str:
    raw = "_".join(parts)
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw)[:120]


def write_path_artifact(
    graph: nx.Graph,
    path: PathMetric,
    artifact_root: Path,
    *,
    run_prefix: str = "path",
) -> Path:
    artifact_root.mkdir(parents=True, exist_ok=True)
    name = _safe_name(run_prefix, path.path_class.value, *[str(n) for n in path.nodes[:6]])
    out = artifact_root / f"{name}.html"
    title = f"#{path.order} {path.path_class.value} · weight {path.weight:g} · {" → ".join(path.nodes)}"
    return render_path_on_graph(graph, path.nodes, out, title=title)
