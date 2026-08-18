"""Synthetic topology for offline RPA demonstration."""

from __future__ import annotations

import networkx as nx


def build_demo_graph() -> nx.Graph:
    """Small fixed-network style topology for UI and tests."""
    g = nx.Graph()
    edges = [
        ("PE-A", "AGG-1", 1.0, 100000, 35.0),
        ("PE-A", "AGG-2", 1.0, 100000, 42.0),
        ("AGG-1", "CORE-1", 1.0, 200000, 50.0),
        ("AGG-2", "CORE-1", 1.0, 200000, 48.0),
        ("AGG-1", "CORE-2", 2.0, 100000, 20.0),
        ("AGG-2", "CORE-2", 2.0, 100000, 22.0),
        ("CORE-1", "BNG-X", 1.0, 200000, 60.0),
        ("CORE-2", "BNG-X", 1.0, 200000, 55.0),
        ("CORE-1", "BNG-Y", 1.5, 100000, 30.0),
        ("CORE-2", "BNG-Y", 1.0, 100000, 28.0),
        ("PE-B", "AGG-3", 1.0, 100000, 25.0),
        ("AGG-3", "CORE-1", 1.0, 100000, 40.0),
        ("AGG-3", "CORE-2", 1.0, 100000, 33.0),
    ]
    for a, z, w, cap, util in edges:
        g.add_edge(
            a,
            z,
            weight=w,
            capacity_mbps=cap,
            max_util=util,
            link_type="TRANSPORT",
            member_count=1,
        )
    return g


def demo_nodes() -> tuple[str, ...]:
    return tuple(sorted(build_demo_graph().nodes))
