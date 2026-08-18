"""Native path selection tests."""

from __future__ import annotations

import networkx as nx
import pytest

from network_analytics.route_path_analysis import (
    RoutePair,
    RouteRequest,
    TransportFrequency,
    analyze,
    validate_request,
)
from network_analytics.route_path_analysis.pathing import select_paths


def _diamond_graph() -> nx.Graph:
    g = nx.Graph()
    g.add_edge("A", "B", weight=1.0, capacity_mbps=10000, max_util=40.0)
    g.add_edge("A", "C", weight=1.0, capacity_mbps=10000, max_util=55.0)
    g.add_edge("B", "D", weight=1.0, capacity_mbps=10000, max_util=30.0)
    g.add_edge("C", "D", weight=1.0, capacity_mbps=10000, max_util=20.0)
    g.add_edge("B", "C", weight=5.0, capacity_mbps=1000, max_util=10.0)
    return g


def test_equal_cost_defaults_are_both_present() -> None:
    g = _diamond_graph()
    selection = select_paths(g, "A", "D", alternate_branches=2)
    assert selection.min_weight == 2.0
    defaults = set(selection.default_paths)
    assert ("A", "B", "D") in defaults
    assert ("A", "C", "D") in defaults
    assert len(selection.default_paths) == 2


def test_analyze_returns_metrics() -> None:
    g = _diamond_graph()
    request = RouteRequest(
        pairs=(RoutePair("A", "D", 0.0),),
        frequency=TransportFrequency.WEEKLY,
        alternate_branches=1,
    )
    result = analyze(g, request)
    assert len(result.pairs) == 1
    pair = result.pairs[0]
    assert pair.min_weight == 2.0
    assert any(p.path_class.value == "Default" for p in pair.paths)
    assert pair.paths[0].bottleneck_capacity_mbps == 10000


def test_daily_rejects_multiple_pairs() -> None:
    request = RouteRequest(
        pairs=(RoutePair("A", "B"), RoutePair("C", "D")),
        frequency=TransportFrequency.DAILY,
        alternate_branches=0,
    )
    validation = validate_request(request)
    assert validation.passed is False
    assert any("exactly one pair" in e for e in validation.errors)


def test_no_path() -> None:
    g = nx.Graph()
    g.add_node("A")
    g.add_node("Z")
    selection = select_paths(g, "A", "Z")
    assert selection.min_weight is None
    assert selection.default_paths == ()
