"""Native deterministic path selection.

Equal-minimum-weight membership is canonical. Default paths share the ECMP
bucket; alternates are display-only and never replace defaults.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from .contracts import PathClass, PathMetric, PathResultType, HopMetric


@dataclass(frozen=True, slots=True)
class PathSelection:
    default_paths: tuple[tuple[str, ...], ...]
    alternate_paths: tuple[tuple[str, ...], ...]
    min_weight: float | None
    warnings: tuple[str, ...] = ()


def path_total_weight(graph: nx.Graph, nodes: list[str]) -> float:
    total = 0.0
    for left, right in zip(nodes[:-1], nodes[1:]):
        total += float(graph[left][right].get("weight", 1.0) or 1.0)
    return total


def select_paths(
    graph: nx.Graph,
    source: str,
    destination: str,
    *,
    alternate_branches: int = 2,
) -> PathSelection:
    source = str(source).strip().upper()
    destination = str(destination).strip().upper()
    warnings: list[str] = []

    if source not in graph or destination not in graph:
        return PathSelection((), (), None, ("endpoint not present in graph",))

    if source == destination:
        return PathSelection((), (), 0.0, ("source and destination are identical",))

    try:
        # All simple paths is too expensive for large graphs; use shortest-path
        # variants with weight and then expand equal-cost membership.
        min_weight = nx.shortest_path_length(graph, source, destination, weight="weight")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return PathSelection((), (), None, ("no path",))

    # Collect equal-cost shortest paths (ECMP defaults)
    try:
        raw_shortest = list(
            nx.all_shortest_paths(graph, source, destination, weight="weight")
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return PathSelection((), (), None, ("no path",))

    # Deterministic ordering
    default_paths = tuple(sorted(tuple(p) for p in raw_shortest))

    alternates: list[tuple[str, ...]] = []
    if alternate_branches > 0:
        # Simple alternate strategy: loopless paths ordered by weight, skipping defaults
        default_set = set(default_paths)
        candidates: list[tuple[float, tuple[str, ...]]] = []
        try:
            for path in nx.all_simple_paths(graph, source, destination, cutoff=12):
                t = tuple(path)
                if t in default_set:
                    continue
                w = path_total_weight(graph, list(t))
                candidates.append((w, t))
        except nx.NetworkXError:
            pass
        candidates.sort(key=lambda item: (item[0], item[1]))
        seen: set[tuple[str, ...]] = set()
        for _w, path in candidates:
            if path in seen:
                continue
            seen.add(path)
            alternates.append(path)
            if len(alternates) >= alternate_branches:
                break
        if not alternates and alternate_branches > 0:
            warnings.append("no alternate paths found within search bounds")

    return PathSelection(
        default_paths=default_paths,
        alternate_paths=tuple(alternates),
        min_weight=float(min_weight),
        warnings=tuple(warnings),
    )


def selection_to_metrics(
    graph: nx.Graph,
    selection: PathSelection,
) -> tuple[PathMetric, ...]:
    metrics: list[PathMetric] = []
    order = 1
    for path in selection.default_paths:
        metrics.append(_to_metric(graph, path, order, PathClass.DEFAULT))
        order += 1
    for path in selection.alternate_paths:
        metrics.append(_to_metric(graph, path, order, PathClass.ALTERNATE))
        order += 1
    if not metrics and selection.min_weight is None:
        metrics.append(
            PathMetric(
                order=1,
                path_class=PathClass.DEFAULT,
                nodes=(),
                weight=0.0,
                result_type=PathResultType.NO_PATH,
            )
        )
    return tuple(metrics)


def _to_metric(
    graph: nx.Graph,
    path: tuple[str, ...],
    order: int,
    path_class: PathClass,
) -> PathMetric:
    hops: list[HopMetric] = []
    for left, right in zip(path[:-1], path[1:]):
        edge = graph[left][right]
        hops.append(
            HopMetric(
                source=str(left),
                destination=str(right),
                weight=float(edge.get("weight", 1.0) or 1.0),
                capacity_mbps=_maybe_float(edge.get("capacity_mbps")),
                utilization_pct=_maybe_float(edge.get("max_util")),
                link_type=str(edge.get("link_type") or "Unavailable"),
                member_count=_maybe_int(edge.get("member_count")),
            )
        )
    return PathMetric(
        order=order,
        path_class=path_class,
        nodes=path,
        weight=path_total_weight(graph, list(path)),
        result_type=PathResultType.FULL_PATH if path else PathResultType.NO_PATH,
        hops=tuple(hops),
    )


def _maybe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _maybe_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
