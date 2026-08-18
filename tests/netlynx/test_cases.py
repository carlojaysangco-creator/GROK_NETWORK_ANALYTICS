"""NOC case detection tests."""

from __future__ import annotations

from network_analytics.data_platform import GenerationStore
from network_analytics.netlynx import publish_observations
from network_analytics.netlynx.cases import detect_cases
from network_analytics.netlynx.future_contracts import CaseKind


def test_detect_down_and_high_util(tmp_path) -> None:
    store = GenerationStore(tmp_path / "gens")
    rows = [
        {
            "link_id": "L-DOWN",
            "snapshot_time": "2026-08-18T12:00:00Z",
            "a_end": "A",
            "z_end": "B",
            "interface_type": "LAG_PARENT",
            "capacity_mbps": "10000",
            "in_util_pct": "0",
            "state": "down",
        },
        {
            "link_id": "L-HOT",
            "snapshot_time": "2026-08-18T12:00:00Z",
            "a_end": "C",
            "z_end": "D",
            "interface_type": "PHYSICAL",
            "capacity_mbps": "10000",
            "in_util_pct": "90",
            "out_util_pct": "88",
            "state": "up",
        },
        {
            "link_id": "L-OK",
            "snapshot_time": "2026-08-18T12:00:00Z",
            "interface_type": "LAG_PARENT",
            "capacity_mbps": "10000",
            "in_util_pct": "10",
            "state": "up",
        },
    ]
    publish_observations(store, rows, producer_version="0.1.0.dev0", promote=True)
    cases = detect_cases(store)
    kinds = {c.kind for c in cases}
    assert CaseKind.RECENT_DOWN in kinds
    assert CaseKind.HIGH_UTILIZATION in kinds
    assert CaseKind.COMBINED_AFFECTED in kinds
    down = next(c for c in cases if c.kind is CaseKind.RECENT_DOWN)
    assert down.affected_link_ids == ("L-DOWN",)
