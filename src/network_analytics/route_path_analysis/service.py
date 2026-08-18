"""RPA application service – request validation and analysis orchestration."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from .contracts import (
    AnalysisResult,
    PairResult,
    RoutePair,
    RouteRequest,
    TransportFrequency,
)
from .pathing import select_paths, selection_to_metrics


@dataclass(frozen=True, slots=True)
class ValidationResult:
    passed: bool
    errors: tuple[str, ...] = ()


def validate_request(request: RouteRequest) -> ValidationResult:
    errors: list[str] = []
    if not request.pairs:
        errors.append("at least one source/destination pair is required")
    if not 0 <= request.alternate_branches <= 10:
        errors.append("alternate_branches must be between 0 and 10")

    freq = request.frequency
    if freq in {TransportFrequency.DAILY, TransportFrequency.COMPARE}:
        if len(request.pairs) != 1:
            errors.append("Daily/Compare require exactly one pair")
        if any(p.additional_bw_mbps != 0 for p in request.pairs):
            errors.append("Daily/Compare require zero additional bandwidth")
        if request.alternate_branches != 0:
            errors.append("Daily/Compare do not allow planning alternates")

    for pair in request.pairs:
        n = pair.normalized()
        if not n.source or not n.destination:
            errors.append("source and destination must be non-empty")

    return ValidationResult(passed=not errors, errors=tuple(errors))


def analyze(graph: nx.Graph, request: RouteRequest) -> AnalysisResult:
    validation = validate_request(request)
    if not validation.passed:
        raise ValueError("; ".join(validation.errors))

    pair_results: list[PairResult] = []
    for pair in request.pairs:
        n = pair.normalized()
        selection = select_paths(
            graph,
            n.source,
            n.destination,
            alternate_branches=request.alternate_branches,
        )
        metrics = selection_to_metrics(graph, selection)
        pair_results.append(
            PairResult(
                source=n.source,
                destination=n.destination,
                min_weight=selection.min_weight,
                additional_bw_mbps=n.additional_bw_mbps,
                paths=metrics,
                warnings=selection.warnings,
            )
        )

    return AnalysisResult(
        frequency=request.frequency,
        pairing_mode=request.pairing_mode,
        alternate_branches=request.alternate_branches,
        pairs=tuple(pair_results),
    )
