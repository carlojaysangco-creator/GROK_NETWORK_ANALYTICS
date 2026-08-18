"""NetLynx operational contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from network_analytics.shared.status import DataState, LinkState


class InterfaceType(StrEnum):
    LAG_PARENT = "LAG_PARENT"
    LAG_MEMBER = "LAG_MEMBER"
    PHYSICAL = "PHYSICAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class Observation:
    """One accepted utilisation / state observation for a link."""

    link_id: str
    snapshot_time: str
    a_end: str | None
    z_end: str | None
    interface_type: InterfaceType
    capacity_mbps: float | None
    in_util_pct: float | None
    out_util_pct: float | None
    state: LinkState
    vendor: str | None = None
    domain: str | None = None
    source_generation_id: str | None = None
    metadata: dict = field(default_factory=dict)

    def max_util_pct(self) -> float | None:
        values = [v for v in (self.in_util_pct, self.out_util_pct) if v is not None]
        return max(values) if values else None


@dataclass(frozen=True, slots=True)
class DimensionLink:
    link_id: str
    a_end: str | None
    z_end: str | None
    capacity_mbps: float | None
    interface_type: InterfaceType
    role: str | None = None
    domain: str | None = None
    parent_link_id: str | None = None  # for members


@dataclass(frozen=True, slots=True)
class CohortIdentity:
    """FACT + dimensions must be selected as one coherent cohort."""

    cohort_id: str
    fact_generation_id: str
    dimension_generation_ids: tuple[str, ...]
    business_date: str | None
    state: DataState = DataState.UNKNOWN
