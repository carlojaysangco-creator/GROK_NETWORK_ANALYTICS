"""Routing policy and N4I floor tests."""

from __future__ import annotations

from network_analytics.route_path_analysis.graph_builder import build_graph
from network_analytics.route_path_analysis.link_schema import LinkRecord
from network_analytics.route_path_analysis.routing_policy import (
    N4I_LINK_WEIGHT,
    default_policy,
    is_n4i_node,
)


def test_n4i_node_detection() -> None:
    assert is_n4i_node("PE-N4I-01")
    assert is_n4i_node("HUN4-EDGE")
    assert not is_n4i_node("PE-A")


def test_n4i_floor_applied() -> None:
    records = [
        LinkRecord("PE-A", "N4I-BORDER", weight=1.0, capacity_mbps=10000, link_type="TRANSPORT"),
    ]
    g = build_graph(records)
    assert g["PE-A"]["N4I-BORDER"]["weight"] >= N4I_LINK_WEIGHT


def test_explicit_weight_respected_with_floor() -> None:
    policy = default_policy()
    w = policy.edge_weight(a_end="A", z_end="B", link_type="CORE", explicit_weight=3.0)
    assert w == 3.0
    w2 = policy.edge_weight(a_end="A", z_end="N4I-X", link_type="CORE", explicit_weight=3.0)
    assert w2 == N4I_LINK_WEIGHT
