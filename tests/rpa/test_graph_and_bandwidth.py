"""Graph construction and bandwidth overlay tests."""

from __future__ import annotations

from network_analytics.data_platform import GenerationStore, SourceIdentity
from network_analytics.route_path_analysis import (
    LinkRecord,
    LinkRole,
    RoutePair,
    RouteRequest,
    TransportFrequency,
    analyze,
    build_graph,
    link_records_from_rows,
    publish_link_topology,
)
from network_analytics.route_path_analysis.bandwidth import share_additional_bw_across_defaults
from network_analytics.route_path_analysis.pathing import select_paths, selection_to_metrics


def test_members_do_not_add_capacity() -> None:
    records = [
        LinkRecord("A", "B", weight=1.0, capacity_mbps=10000, role=LinkRole.PARENT),
        LinkRecord("A", "B", weight=1.0, capacity_mbps=5000, role=LinkRole.MEMBER),
    ]
    g = build_graph(records)
    assert g["A"]["B"]["capacity_mbps"] == 10000


def test_parallel_parents_aggregate_capacity() -> None:
    records = [
        LinkRecord("A", "B", weight=2.0, capacity_mbps=10000, max_util_pct=40.0, role=LinkRole.PARENT),
        LinkRecord("A", "B", weight=1.0, capacity_mbps=10000, max_util_pct=50.0, role=LinkRole.PARENT),
    ]
    g = build_graph(records)
    edge = g["A"]["B"]
    assert edge["capacity_mbps"] == 20000
    assert edge["max_util"] == 50.0
    assert edge["weight"] == 1.0
    assert edge["parent_count"] == 2


def test_missing_capacity_stays_none() -> None:
    records = [LinkRecord("A", "B", weight=1.0, capacity_mbps=None)]
    g = build_graph(records)
    assert g["A"]["B"]["capacity_mbps"] is None


def test_rejected_rows_without_endpoints() -> None:
    accepted, rejected = link_records_from_rows(
        [
            {"a_end": "A", "z_end": "B", "capacity_mbps": "1000"},
            {"a_end": "", "z_end": "B"},
            {"source": "X"},  # missing dest
        ]
    )
    assert len(accepted) == 1
    assert rejected == 2


def test_signed_bw_floors_at_zero() -> None:
    records = [
        LinkRecord("A", "B", weight=1.0, capacity_mbps=10000, max_util_pct=10.0),
        LinkRecord("B", "C", weight=1.0, capacity_mbps=10000, max_util_pct=10.0),
    ]
    g = build_graph(records)
    selection = select_paths(g, "A", "C", alternate_branches=0)
    metrics = selection_to_metrics(g, selection)
    # Remove more traffic than present → util floors at 0
    updated = share_additional_bw_across_defaults(metrics, -50000)
    assert updated[0].hops[0].utilization_pct == 0.0


def test_analyze_applies_ecmp_share() -> None:
    records = [
        LinkRecord("A", "B", 1.0, 10000, 0.0),
        LinkRecord("A", "C", 1.0, 10000, 0.0),
        LinkRecord("B", "D", 1.0, 10000, 0.0),
        LinkRecord("C", "D", 1.0, 10000, 0.0),
    ]
    g = build_graph(records)
    result = analyze(
        g,
        RouteRequest(
            pairs=(RoutePair("A", "D", additional_bw_mbps=2000),),
            frequency=TransportFrequency.WEEKLY,
            alternate_branches=0,
        ),
    )
    defaults = [p for p in result.pairs[0].paths if p.path_class.value == "Default"]
    assert len(defaults) == 2
    # 2000 Mbps split across 2 defaults → 1000 each → 10% on 10G
    for path in defaults:
        assert path.hops[0].utilization_pct == 10.0


def test_publish_and_reload_topology(tmp_path) -> None:
    store = GenerationStore(tmp_path / "gens")
    rows = [
        {"a_end": "PE-A", "z_end": "CORE-1", "weight": "1", "capacity_mbps": "100000", "max_util": "40"},
        {"a_end": "CORE-1", "z_end": "BNG-X", "weight": "1", "capacity_mbps": "200000", "max_util": "55"},
    ]
    ref = publish_link_topology(
        store,
        rows,
        producer_version="0.1.0.dev0",
        source=SourceIdentity(system="test", path_or_job="unit", sha256="x"),
        promote=True,
    )
    assert ref.manifest.status.value == "promoted"
    assert store.resolve_readable("rpa_topology") is not None

    from network_analytics.route_path_analysis.reference import graph_from_promoted

    g = graph_from_promoted(store)
    assert g is not None
    assert g.has_edge("PE-A", "CORE-1")
