"""Daily topology must fail closed without a promoted daily generation."""

from __future__ import annotations

import pytest

from network_analytics.data_platform import GenerationStore
from network_analytics.route_path_analysis import DailyUnavailable, resolve_daily_graph
from network_analytics.route_path_analysis.reference import publish_link_topology


def test_daily_unavailable_without_generation(tmp_path) -> None:
    store = GenerationStore(tmp_path / "gens")
    with pytest.raises(DailyUnavailable, match="No promoted RPA-ready Daily"):
        resolve_daily_graph(store)


def test_weekly_topology_does_not_satisfy_daily(tmp_path) -> None:
    store = GenerationStore(tmp_path / "gens")
    publish_link_topology(
        store,
        [{"a_end": "A", "z_end": "B", "weight": "1", "capacity_mbps": "1000"}],
        producer_version="0.1.0.dev0",
        promote=True,
    )
    # Weekly exists, Daily must still fail closed
    with pytest.raises(DailyUnavailable):
        resolve_daily_graph(store)
