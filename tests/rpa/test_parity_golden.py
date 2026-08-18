"""Parity-style golden path membership fixtures."""

from __future__ import annotations

from network_analytics.route_path_analysis import (
    LinkRecord,
    LinkRole,
    RoutePair,
    RouteRequest,
    analyze,
    build_graph,
)

# Fixed expected equal-cost membership (engine authority checks)
GOLDEN_CASES = [
    {
        "name": "diamond_ecmp",
        "edges": [
            ("A", "B", 1.0, 10000),
            ("A", "C", 1.0, 10000),
            ("B", "D", 1.0, 10000),
            ("C", "D", 1.0, 10000),
            ("B", "C", 5.0, 1000),
        ],
        "source": "A",
        "destination": "D",
        "expected_defaults": {("A", "B", "D"), ("A", "C", "D")},
        "expected_min_weight": 2.0,
    },
    {
        "name": "single_path",
        "edges": [("X", "Y", 1.0, 1000), ("Y", "Z", 2.0, 500)],
        "source": "X",
        "destination": "Z",
        "expected_defaults": {("X", "Y", "Z")},
        "expected_min_weight": 3.0,
    },
]


def _graph(edges):
    records = [
        LinkRecord(a, z, weight=w, capacity_mbps=cap, role=LinkRole.PARENT) for a, z, w, cap in edges
    ]
    return build_graph(records)


def test_parity_golden_membership() -> None:
    for case in GOLDEN_CASES:
        g = _graph(case["edges"])
        result = analyze(
            g,
            RouteRequest(
                pairs=(RoutePair(case["source"], case["destination"]),),
                alternate_branches=0,
            ),
        )
        pair = result.pairs[0]
        assert pair.min_weight == case["expected_min_weight"], case["name"]
        defaults = {p.nodes for p in pair.paths if p.path_class.value == "Default"}
        assert defaults == case["expected_defaults"], case["name"]
