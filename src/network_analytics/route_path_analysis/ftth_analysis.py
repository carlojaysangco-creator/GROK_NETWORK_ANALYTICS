"""FTTH Access NE analysis – expand mapping then path to each Homing BNG."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from network_analytics.data_platform import GenerationStore

from .contracts import AnalysisResult, RoutePair, RouteRequest, TransportFrequency
from .ftth import destinations_for_access, load_ftth_mappings
from .service import analyze


@dataclass(frozen=True, slots=True)
class FtthAnalysisResult:
    access_ne: str
    homing_bngs: tuple[str, ...]
    per_bng: tuple[tuple[str, AnalysisResult], ...]
    warnings: tuple[str, ...] = ()


def analyze_ftth_access(
    graph: nx.Graph,
    store: GenerationStore,
    access_ne: str,
    *,
    alternate_branches: int = 2,
    additional_bw_mbps: float = 0.0,
) -> FtthAnalysisResult:
    access = access_ne.strip().upper()
    mappings = load_ftth_mappings(store)
    if not mappings:
        return FtthAnalysisResult(
            access_ne=access,
            homing_bngs=(),
            per_bng=(),
            warnings=("No promoted FTTH mapping generation.",),
        )

    bngs = destinations_for_access(store, access)
    if not bngs:
        return FtthAnalysisResult(
            access_ne=access,
            homing_bngs=(),
            per_bng=(),
            warnings=(f"No Homing BNG mapped for Access NE {access}.",),
        )

    # Prefer path from access node if present; otherwise still report BNG list
    per: list[tuple[str, AnalysisResult]] = []
    warnings: list[str] = []
    if access not in graph:
        warnings.append(
            f"Access NE {access} is not a node in the topology graph; "
            "showing mapping only. Publish topology that includes the access node for paths."
        )
        return FtthAnalysisResult(
            access_ne=access,
            homing_bngs=bngs,
            per_bng=(),
            warnings=tuple(warnings),
        )

    for bng in bngs:
        request = RouteRequest(
            pairs=(RoutePair(access, bng, additional_bw_mbps),),
            frequency=TransportFrequency.WEEKLY,
            alternate_branches=alternate_branches,
        )
        per.append((bng, analyze(graph, request)))

    return FtthAnalysisResult(
        access_ne=access,
        homing_bngs=bngs,
        per_bng=tuple(per),
        warnings=tuple(warnings),
    )
