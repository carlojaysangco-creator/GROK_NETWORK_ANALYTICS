"""NOC case topology visualization artifacts."""

from __future__ import annotations

from pathlib import Path

from network_analytics.data_platform import GenerationStore
from network_analytics.shared.topology_viz import render_edge_list_graph

from .noc_graph import graph_for_case, summarize_all_case_graphs


def write_case_artifact(store: GenerationStore, case_id: str, artifact_root: Path) -> Path | None:
    view = graph_for_case(store, case_id)
    if view is None or not view.edges:
        return None
    artifact_root.mkdir(parents=True, exist_ok=True)
    out = artifact_root / f"noc_case_{case_id}.html"
    title = f"NOC case {case_id} · {view.case.kind.value} · {view.edge_count} links"
    return render_edge_list_graph(view.edges, out, title=title)


def write_all_case_artifacts(store: GenerationStore, artifact_root: Path) -> list[Path]:
    paths: list[Path] = []
    for view in summarize_all_case_graphs(store):
        p = write_case_artifact(store, view.case.case_id, artifact_root)
        if p is not None:
            paths.append(p)
    return paths
