"""Daily topology builder from FACT."""

from __future__ import annotations

from network_analytics.data_platform import GenerationStore
from network_analytics.netlynx import publish_observations
from network_analytics.route_path_analysis import resolve_daily_graph
from network_analytics.route_path_analysis.loaders import publish_daily_topology_from_fact


def test_build_daily_from_fact(tmp_path) -> None:
    store = GenerationStore(tmp_path / "gens")
    publish_observations(
        store,
        [
            {
                "link_id": "L1",
                "snapshot_time": "2026-08-18T12:00:00Z",
                "a_end": "PE-A",
                "z_end": "BNG-X",
                "interface_type": "LAG_PARENT",
                "capacity_mbps": "100000",
                "in_util_pct": "40",
                "state": "up",
            }
        ],
        producer_version="0.1.0.dev0",
        promote=True,
    )
    ref = publish_daily_topology_from_fact(store, producer_version="0.1.0.dev0", promote=True)
    assert ref.manifest.status.value == "promoted"
    topo = resolve_daily_graph(store)
    assert topo.graph.has_edge("PE-A", "BNG-X")
