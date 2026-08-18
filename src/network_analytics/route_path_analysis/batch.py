"""Multi-pair RPA batch analysis."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from .contracts import AnalysisResult, RoutePair, RouteRequest, TransportFrequency
from .export import analysis_to_dict, write_analysis_json
from .service import analyze
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BatchRequest:
    pairs: tuple[RoutePair, ...]
    frequency: TransportFrequency = TransportFrequency.WEEKLY
    alternate_branches: int = 2


def analyze_batch(graph: nx.Graph, request: BatchRequest) -> AnalysisResult:
    return analyze(
        graph,
        RouteRequest(
            pairs=request.pairs,
            frequency=request.frequency,
            alternate_branches=request.alternate_branches,
            pairing_mode="batch",
        ),
    )


def batch_to_rows(result: AnalysisResult) -> list[dict]:
    rows: list[dict] = []
    for pair in result.pairs:
        defaults = [p for p in pair.paths if p.path_class.value == "Default"]
        primary = defaults[0] if defaults else (pair.paths[0] if pair.paths else None)
        rows.append(
            {
                "source": pair.source,
                "destination": pair.destination,
                "min_weight": pair.min_weight,
                "default_count": sum(1 for p in pair.paths if p.path_class.value == "Default"),
                "alternate_count": sum(1 for p in pair.paths if p.path_class.value == "Alternate"),
                "primary_path": " → ".join(primary.nodes) if primary else None,
                "bottleneck_mbps": primary.bottleneck_capacity_mbps if primary else None,
                "max_util_pct": primary.maximum_utilization_pct if primary else None,
            }
        )
    return rows


def export_batch(result: AnalysisResult, path: Path) -> Path:
    return write_analysis_json(result, path)
