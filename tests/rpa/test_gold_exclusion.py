"""Gold excluded devices must not enter topology edges."""

from __future__ import annotations

from network_analytics.route_path_analysis import LinkRecord, LinkRole, build_graph
from network_analytics.route_path_analysis.gold_roles import GoldDevice


def test_excluded_endpoint_drops_edge() -> None:
    records = [
        LinkRecord("PE-A", "LAB-TEST", weight=1.0, capacity_mbps=1000, role=LinkRole.PARENT),
        LinkRecord("PE-A", "CORE-1", weight=1.0, capacity_mbps=1000, role=LinkRole.PARENT),
    ]
    gold = {
        "LAB-TEST": GoldDevice(device_id="LAB-TEST", role="TEST", excluded=True),
    }
    g = build_graph(records, gold_lookup=gold)
    assert not g.has_edge("PE-A", "LAB-TEST")
    assert g.has_edge("PE-A", "CORE-1")
    assert g.graph["gold_exclusion_audit"]
