"""Route Path Analysis contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TransportFrequency(StrEnum):
    WEEKLY = "weekly"
    DAILY = "daily"
    COMPARE = "compare"


class PathClass(StrEnum):
    DEFAULT = "Default"
    ALTERNATE = "Alternate"


class PathResultType(StrEnum):
    FULL_PATH = "FULL_PATH"
    PARTIAL_PATH = "PARTIAL_PATH"
    NO_PATH = "NO_PATH"
    FAILED_LOOKUP = "FAILED_LOOKUP"


@dataclass(frozen=True, slots=True)
class RoutePair:
    source: str
    destination: str
    additional_bw_mbps: float = 0.0

    def normalized(self) -> "RoutePair":
        return RoutePair(
            source=str(self.source or "").strip().upper(),
            destination=str(self.destination or "").strip().upper(),
            additional_bw_mbps=float(self.additional_bw_mbps or 0.0),
        )


@dataclass(frozen=True, slots=True)
class RouteRequest:
    pairs: tuple[RoutePair, ...]
    frequency: TransportFrequency = TransportFrequency.WEEKLY
    pairing_mode: str = "paired"  # paired | all_combinations
    alternate_branches: int = 2


@dataclass(frozen=True, slots=True)
class HopMetric:
    source: str
    destination: str
    weight: float
    capacity_mbps: float | None = None
    utilization_pct: float | None = None
    link_type: str = "Unavailable"
    member_count: int | None = None


@dataclass(frozen=True, slots=True)
class PathMetric:
    order: int
    path_class: PathClass
    nodes: tuple[str, ...]
    weight: float
    result_type: PathResultType
    hops: tuple[HopMetric, ...] = ()

    @property
    def bottleneck_capacity_mbps(self) -> float | None:
        values = [h.capacity_mbps for h in self.hops if h.capacity_mbps is not None]
        return min(values) if values else None

    @property
    def maximum_utilization_pct(self) -> float | None:
        values = [h.utilization_pct for h in self.hops if h.utilization_pct is not None]
        return max(values) if values else None


@dataclass(frozen=True, slots=True)
class PairResult:
    source: str
    destination: str
    min_weight: float | None
    additional_bw_mbps: float
    paths: tuple[PathMetric, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    frequency: TransportFrequency
    pairing_mode: str
    alternate_branches: int
    pairs: tuple[PairResult, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)
