"""Daily topology resolution – fail-closed until a coherent generation exists."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from network_analytics.data_platform import GenerationStore

from .reference import DATASET_TOPOLOGY, graph_from_promoted, load_records_from_generation

DATASET_DAILY_TOPOLOGY = "rpa_daily_topology"


class DailyUnavailable(RuntimeError):
    """Raised when Daily analysis is requested without a promoted cohort."""


@dataclass(frozen=True, slots=True)
class TopologySource:
    name: str
    generation_id: str | None
    graph: nx.Graph
    is_daily: bool


def resolve_weekly_graph(store: GenerationStore) -> TopologySource | None:
    """Prefer promoted weekly/planning topology; None if missing."""
    ref = store.resolve_readable(DATASET_TOPOLOGY)
    if ref is None:
        return None
    records = load_records_from_generation(ref)
    if not records:
        return None
    from .graph_builder import build_graph

    return TopologySource(
        name="promoted_rpa_topology",
        generation_id=ref.generation_id,
        graph=build_graph(records),
        is_daily=False,
    )


def resolve_daily_graph(store: GenerationStore) -> TopologySource:
    """Daily must use an explicit daily topology generation – never Weekly fallback."""
    ref = store.resolve_readable(DATASET_DAILY_TOPOLOGY)
    if ref is None:
        raise DailyUnavailable(
            "No promoted RPA-ready Daily topology generation. "
            "NetLynx monitoring data is not used as a routing-engine substitute."
        )
    records = load_records_from_generation(ref)
    if not records:
        raise DailyUnavailable(
            f"Daily topology generation {ref.generation_id} has no accepted links."
        )
    from .graph_builder import build_graph

    return TopologySource(
        name="promoted_rpa_daily_topology",
        generation_id=ref.generation_id,
        graph=build_graph(records),
        is_daily=True,
    )
