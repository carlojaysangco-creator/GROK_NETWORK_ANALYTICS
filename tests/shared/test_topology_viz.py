"""Pyvis artifact generation tests."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from network_analytics.shared.topology_viz import render_path_on_graph


def test_render_path_html(tmp_path: Path) -> None:
    pytest.importorskip("pyvis")
    g = nx.Graph()
    g.add_edge("A", "B", weight=1, capacity_mbps=1000, max_util=40)
    g.add_edge("B", "C", weight=1, capacity_mbps=1000, max_util=50)
    out = render_path_on_graph(g, ["A", "B", "C"], tmp_path / "path.html", title="A → C")
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "A" in text and "C" in text
