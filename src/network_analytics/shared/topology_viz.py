"""Pyvis HTML topology artifacts (visualization only)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import networkx as nx


class TopologyVizUnavailable(RuntimeError):
    """Raised when pyvis is not installed."""


def _require_pyvis():
    try:
        from pyvis.network import Network
    except ImportError as exc:
        raise TopologyVizUnavailable(
            "pyvis is not installed. Install with: pip install -e \".[rpa]\""
        ) from exc
    return Network


def neighborhood_subgraph(
    graph: nx.Graph,
    focus_nodes: Iterable[str],
    *,
    hop: int = 1,
    max_nodes: int = 120,
) -> nx.Graph:
    focus = {str(n).upper() for n in focus_nodes}
    keep = set(focus)
    frontier = set(focus)
    for _ in range(max(0, hop)):
        nxt: set[str] = set()
        for node in frontier:
            if node not in graph:
                # try original casing match
                matches = [n for n in graph.nodes if str(n).upper() == node]
                node_key = matches[0] if matches else None
            else:
                node_key = node
            if node_key is None:
                continue
            for nbr in graph.neighbors(node_key):
                nxt.add(str(nbr).upper())
        keep |= nxt
        frontier = nxt
        if len(keep) >= max_nodes:
            break

    node_map = {str(n).upper(): n for n in graph.nodes}
    chosen = []
    for key in keep:
        if key in node_map:
            chosen.append(node_map[key])
        if len(chosen) >= max_nodes:
            break
    if not chosen:
        return graph.copy()
    return graph.subgraph(chosen).copy()


def render_graph_html(
    graph: nx.Graph,
    output_path: Path,
    *,
    title: str = "Topology",
    highlight_nodes: Iterable[str] | None = None,
    highlight_edges: Iterable[tuple[str, str]] | None = None,
    height: str = "720px",
    width: str = "100%",
    max_nodes: int = 150,
) -> Path:
    Network = _require_pyvis()
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if graph.number_of_nodes() > max_nodes:
        focus = list(highlight_nodes or list(graph.nodes)[:10])
        graph = neighborhood_subgraph(graph, focus, hop=1, max_nodes=max_nodes)

    hi_nodes = {str(n).upper() for n in (highlight_nodes or [])}
    hi_edges = set()
    for a, z in highlight_edges or []:
        hi_edges.add(frozenset({str(a).upper(), str(z).upper()}))

    net = Network(height=height, width=width, bgcolor="#0f1419", font_color="#e7ecf3", directed=False)
    net.barnes_hut()
    net.set_options(
        """
        var options = {
          "nodes": {"shape": "dot", "font": {"size": 14}},
          "edges": {"smooth": false, "color": {"inherit": false}},
          "physics": {"stabilization": {"iterations": 120}}
        }
        """
    )

    for node in graph.nodes:
        label = str(node)
        key = label.upper()
        color = "#3b82f6" if key in hi_nodes else "#64748b"
        size = 22 if key in hi_nodes else 14
        net.add_node(key, label=label, color=color, size=size, title=label)

    for a, z, data in graph.edges(data=True):
        ak, zk = str(a).upper(), str(z).upper()
        highlighted = frozenset({ak, zk}) in hi_edges
        util = data.get("max_util")
        cap = data.get("capacity_mbps")
        weight = data.get("weight")
        title_bits = [f"{a} — {z}"]
        if weight is not None:
            title_bits.append(f"weight={weight}")
        if cap is not None:
            title_bits.append(f"cap={cap}")
        if util is not None:
            title_bits.append(f"util={util}%")
        net.add_edge(
            ak,
            zk,
            color="#f59e0b" if highlighted else "#334155",
            width=4 if highlighted else 1.5,
            title=" · ".join(title_bits),
        )

    net.write_html(str(output_path), open_browser=False, notebook=False)
    try:
        html = output_path.read_text(encoding="utf-8")
        banner = (
            f"<div style='padding:8px 12px;background:#1a2332;color:#e7ecf3;"
            f"font-family:system-ui'>{title}</div>"
        )
        if "<body>" in html:
            html = html.replace("<body>", f"<body>{banner}", 1)
            output_path.write_text(html, encoding="utf-8")
    except OSError:
        pass
    return output_path


def render_path_on_graph(
    graph: nx.Graph,
    path_nodes: list[str] | tuple[str, ...],
    output_path: Path,
    *,
    title: str | None = None,
    hop: int = 1,
    max_nodes: int = 120,
) -> Path:
    nodes = [str(n) for n in path_nodes]
    edges = list(zip(nodes[:-1], nodes[1:]))
    sub = neighborhood_subgraph(graph, nodes, hop=hop, max_nodes=max_nodes) if nodes else graph
    return render_graph_html(
        sub,
        output_path,
        title=title or (" → ".join(nodes) if nodes else "Path"),
        highlight_nodes=nodes,
        highlight_edges=edges,
        max_nodes=max_nodes,
    )


def render_edge_list_graph(
    edges: Iterable[tuple[str, str, str | None]],
    output_path: Path,
    *,
    title: str = "Affected topology",
) -> Path:
    g = nx.Graph()
    for a, z, link_id in edges:
        g.add_edge(str(a), str(z), link_id=link_id or "")
    return render_graph_html(
        g,
        output_path,
        title=title,
        highlight_nodes=list(g.nodes),
        highlight_edges=list(g.edges),
    )
