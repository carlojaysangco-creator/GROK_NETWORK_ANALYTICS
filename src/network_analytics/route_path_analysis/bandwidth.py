"""Signed bandwidth overlay on path metrics.

Additional BW may be positive (add traffic) or negative (remove traffic).
Projected utilisation is floored at zero and left null when capacity is unknown.
"""

from __future__ import annotations

from .contracts import HopMetric, PathMetric


def _projected_util(
    capacity_mbps: float | None,
    current_util_pct: float | None,
    additional_bw_mbps: float,
) -> float | None:
    if capacity_mbps is None or capacity_mbps <= 0:
        return None
    base_traffic = 0.0
    if current_util_pct is not None:
        base_traffic = (current_util_pct / 100.0) * capacity_mbps
    projected = base_traffic + additional_bw_mbps
    if projected < 0:
        projected = 0.0
    return (projected / capacity_mbps) * 100.0


def apply_additional_bw(path: PathMetric, additional_bw_mbps: float) -> PathMetric:
    """Return a copy of path with hop utilisations projected after signed BW.

    Default ECMP sharing is applied when multiple default paths exist at the
    call site; this function treats additional_bw_mbps as the share for *this*
    path.
    """

    if additional_bw_mbps == 0:
        return path

    new_hops: list[HopMetric] = []
    for hop in path.hops:
        projected = _projected_util(hop.capacity_mbps, hop.utilization_pct, additional_bw_mbps)
        new_hops.append(
            HopMetric(
                source=hop.source,
                destination=hop.destination,
                weight=hop.weight,
                capacity_mbps=hop.capacity_mbps,
                utilization_pct=projected if projected is not None else hop.utilization_pct,
                link_type=hop.link_type,
                member_count=hop.member_count,
            )
        )
    return PathMetric(
        order=path.order,
        path_class=path.path_class,
        nodes=path.nodes,
        weight=path.weight,
        result_type=path.result_type,
        hops=tuple(new_hops),
    )


def share_additional_bw_across_defaults(
    paths: tuple[PathMetric, ...],
    additional_bw_mbps: float,
) -> tuple[PathMetric, ...]:
    """Split signed BW equally across Default paths; alternates unchanged."""

    from .contracts import PathClass

    defaults = [p for p in paths if p.path_class is PathClass.DEFAULT]
    if not defaults or additional_bw_mbps == 0:
        return paths

    share = additional_bw_mbps / len(defaults)
    updated: list[PathMetric] = []
    for path in paths:
        if path.path_class is PathClass.DEFAULT:
            updated.append(apply_additional_bw(path, share))
        else:
            updated.append(path)
    return tuple(updated)
