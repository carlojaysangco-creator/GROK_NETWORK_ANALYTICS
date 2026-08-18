"""NetLynx offline cohort tests."""

from __future__ import annotations

from network_analytics.data_platform import GenerationStore
from network_analytics.netlynx import load_observations, publish_observations


def test_publish_and_load_observations(tmp_path) -> None:
    store = GenerationStore(tmp_path / "gens")
    rows = [
        {
            "link_id": "L1",
            "snapshot_time": "2026-08-18T10:00:00Z",
            "a_end": "A",
            "z_end": "B",
            "interface_type": "LAG_PARENT",
            "capacity_mbps": "100000",
            "in_util_pct": "40",
            "out_util_pct": "42",
            "state": "up",
        },
        {
            "link_id": "L1-m1",
            "snapshot_time": "2026-08-18T10:00:00Z",
            "interface_type": "LAG_MEMBER",
            "capacity_mbps": "50000",
            "in_util_pct": "41",
            "state": "up",
        },
        {"link_id": "", "snapshot_time": "x"},  # rejected
    ]
    ref = publish_observations(store, rows, producer_version="0.1.0.dev0", promote=True)
    assert ref.manifest.status.value == "promoted"
    assert ref.manifest.accepted_count == 2
    assert ref.manifest.rejected_count == 1

    loaded = load_observations(store)
    assert len(loaded) == 2
    parent = next(o for o in loaded if o.link_id == "L1")
    assert parent.max_util_pct() == 42.0
    assert parent.capacity_mbps == 100000
