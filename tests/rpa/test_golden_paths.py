"""Golden path cases – fixed topology, expected ECMP membership and bottleneck."""

from __future__ import annotations

from network_analytics.route_path_analysis import (
    LinkRecord,
    LinkRole,
    RoutePair,
    RouteRequest,
    TransportFrequency,
    analyze,
    build_graph,
    link_record_from_mapping,
)


def _soc_style_diamond():
    """Two equal-cost defaults A→B→D and A→C→D; heavier alternate via B-C."""
    rows = [
        {"AEnd_NE": "A", "ZEnd_NE": "B", "Capacity": "10000", "InUti": "0.40", "OutUti": "0.35", "Interface_Type": "LAG_PARENT"},
        {"AEnd_NE": "A", "ZEnd_NE": "C", "Capacity": "10000", "InUti": "0.55", "OutUti": "0.50", "Interface_Type": "LAG_PARENT"},
        {"AEnd_NE": "B", "ZEnd_NE": "D", "Capacity": "10000", "InUti": "0.30", "OutUti": "0.25", "Interface_Type": "LAG_PARENT"},
        {"AEnd_NE": "C", "ZEnd_NE": "D", "Capacity": "10000", "InUti": "0.20", "OutUti": "0.18", "Interface_Type": "LAG_PARENT"},
        {"AEnd": "B", "ZEnd": "C", "weight": "5", "Capacity (Mbps)": "1000", "Max_Util": "10"},
        # member must not inflate A-B capacity
        {"AEnd_NE": "A", "ZEnd_NE": "B", "Capacity": "5000", "Interface_Type": "LAG_MEMBER"},
    ]
    records = []
    for row in rows:
        rec = link_record_from_mapping(row)
        assert rec is not None
        records.append(rec)
    return build_graph(records)


def test_legacy_aliases_and_fraction_util() -> None:
    g = _soc_style_diamond()
    edge_ab = g["A"]["B"]
    assert edge_ab["capacity_mbps"] == 10000  # member excluded
    assert edge_ab["max_util"] == 40.0  # 0.40 fraction → 40%


def test_golden_ecmp_defaults() -> None:
    g = _soc_style_diamond()
    result = analyze(
        g,
        RouteRequest(
            pairs=(RoutePair("A", "D", 0.0),),
            frequency=TransportFrequency.WEEKLY,
            alternate_branches=2,
        ),
    )
    pair = result.pairs[0]
    assert pair.min_weight == 2.0
    default_nodes = {p.nodes for p in pair.paths if p.path_class.value == "Default"}
    assert ("A", "B", "D") in default_nodes
    assert ("A", "C", "D") in default_nodes
    assert len(default_nodes) == 2


def test_golden_bottleneck_on_path() -> None:
    records = [
        LinkRecord("X", "Y", 1.0, capacity_mbps=100000, max_util_pct=10.0, role=LinkRole.PARENT),
        LinkRecord("Y", "Z", 1.0, capacity_mbps=10000, max_util_pct=80.0, role=LinkRole.PARENT),
    ]
    g = build_graph(records)
    result = analyze(
        g,
        RouteRequest(pairs=(RoutePair("X", "Z"),), alternate_branches=0),
    )
    path = result.pairs[0].paths[0]
    assert path.bottleneck_capacity_mbps == 10000
    assert path.maximum_utilization_pct == 80.0


def test_na_capacity_stays_none() -> None:
    rec = link_record_from_mapping({"AEnd": "A", "ZEnd": "B", "Capacity": "n/a", "InUti": "--"})
    assert rec is not None
    assert rec.capacity_mbps is None
    assert rec.in_util_pct is None
