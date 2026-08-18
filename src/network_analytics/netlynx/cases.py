"""NOC affected topology case detection (read-only over promoted FACT)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from network_analytics.data_platform import GenerationStore
from network_analytics.shared.status import DataState, LinkState

from .cohort import load_observations
from .contracts import InterfaceType, Observation
from .future_contracts import CaseKind, TopologyCase


def _stable_case_id(kind: CaseKind, link_ids: tuple[str, ...], generation_id: str | None) -> str:
    body = f"{kind.value}|{generation_id or ''}|{'|'.join(sorted(link_ids))}"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def _authoritative(obs: Observation) -> bool:
    return obs.interface_type in {InterfaceType.LAG_PARENT, InterfaceType.PHYSICAL}


@dataclass(frozen=True, slots=True)
class CaseDetectionConfig:
    high_util_threshold_pct: float = 80.0


def detect_cases(
    store: GenerationStore,
    config: CaseDetectionConfig | None = None,
) -> tuple[TopologyCase, ...]:
    """Derive simple cases from the promoted FACT cohort.

    Does not collect, does not write, and does not mutate routing truth.
    """

    cfg = config or CaseDetectionConfig()
    observations = [o for o in load_observations(store) if _authoritative(o)]
    if not observations:
        return ()

    generation_id = observations[0].source_generation_id
    down_ids = tuple(
        sorted({o.link_id for o in observations if o.state in {LinkState.DOWN}})
    )
    high_ids = tuple(
        sorted(
            {
                o.link_id
                for o in observations
                if (u := o.max_util_pct()) is not None and u >= cfg.high_util_threshold_pct
            }
        )
    )

    cases: list[TopologyCase] = []
    if down_ids:
        cases.append(
            TopologyCase(
                case_id=_stable_case_id(CaseKind.RECENT_DOWN, down_ids, generation_id),
                kind=CaseKind.RECENT_DOWN,
                affected_link_ids=down_ids,
                fact_generation_id=generation_id,
                state=DataState.FRESH,
                metadata={"count": len(down_ids)},
            )
        )
    if high_ids:
        cases.append(
            TopologyCase(
                case_id=_stable_case_id(CaseKind.HIGH_UTILIZATION, high_ids, generation_id),
                kind=CaseKind.HIGH_UTILIZATION,
                affected_link_ids=high_ids,
                fact_generation_id=generation_id,
                state=DataState.FRESH,
                metadata={
                    "count": len(high_ids),
                    "threshold_pct": cfg.high_util_threshold_pct,
                },
            )
        )
    combined = tuple(sorted(set(down_ids) | set(high_ids)))
    if combined and (down_ids or high_ids):
        cases.append(
            TopologyCase(
                case_id=_stable_case_id(CaseKind.COMBINED_AFFECTED, combined, generation_id),
                kind=CaseKind.COMBINED_AFFECTED,
                affected_link_ids=combined,
                fact_generation_id=generation_id,
                state=DataState.FRESH,
                metadata={"count": len(combined)},
            )
        )
    return tuple(cases)
