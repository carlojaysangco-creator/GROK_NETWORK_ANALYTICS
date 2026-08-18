"""Contracts for future RPA-adjacent phases (DFON, OLT homing).

These are designed in from the start. Implementations remain fail-closed
until authoritative sources and validation are wired.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SegmentKind(StrEnum):
    DFON = "DFON"
    FOC = "FOC"
    DIRECT_PATCH = "DIRECT_PATCH"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class PhysicalSegment:
    order: int
    kind: SegmentKind
    identity: str | None = None
    engineering_cost: float | None = None  # never invent production costs


@dataclass(frozen=True, slots=True)
class LogicalLinkSegments:
    link_id: str
    segments: tuple[PhysicalSegment, ...]
    routing_metric: float | None = None  # separate from engineering cost


class HomingState(StrEnum):
    DIRECT = "direct"
    DUAL_HOMED = "dual_homed"
    AMBIGUOUS = "ambiguous"
    STALE = "stale"
    MISSING = "missing"
    UNKNOWN = "unknown"
    ZERO_OLT = "zero_olt"


@dataclass(frozen=True, slots=True)
class OltHoming:
    access_ne: str
    homing_bngs: tuple[str, ...]
    state: HomingState
    source_generation_id: str | None = None
