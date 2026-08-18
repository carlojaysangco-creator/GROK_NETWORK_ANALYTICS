"""NOC affected topology and gated live topology contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from network_analytics.shared.status import DataState


class CaseKind(StrEnum):
    RECENT_DOWN = "recent_down"
    HIGH_UTILIZATION = "high_utilization"
    TOTAL_DOWN_UTILIZATION = "total_down_utilization"
    COMBINED_AFFECTED = "combined_affected"


@dataclass(frozen=True, slots=True)
class TopologyCase:
    case_id: str
    kind: CaseKind
    affected_link_ids: tuple[str, ...]
    affected_olts: tuple[str, ...] = ()
    fact_generation_id: str | None = None
    artifact_id: str | None = None
    state: DataState = DataState.UNKNOWN
    metadata: dict = field(default_factory=dict)


class LiveJobState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class LiveTopologyRequest:
    """Gated live topology request – disabled until explicitly authorised."""

    request_id: str
    device_ids: tuple[str, ...]
    command_profile: str
    requested_by: str
    allowlist_version: str


@dataclass(frozen=True, slots=True)
class LiveTopologyJob:
    job_id: str
    request: LiveTopologyRequest
    state: LiveJobState
    live_validation_pending: bool = True
    evidence_generation_id: str | None = None
    error: str | None = None
