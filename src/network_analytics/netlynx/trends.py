"""Deterministic trend event derivation from ordered observations.

Minimal offline skeleton: state transitions produce events with stable EventId.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from network_analytics.shared.status import LinkState

from .contracts import Observation


@dataclass(frozen=True, slots=True)
class TrendEvent:
    event_id: str
    link_id: str
    from_state: str
    to_state: str
    snapshot_time: str


def _event_id(link_id: str, snapshot_time: str, from_state: str, to_state: str) -> str:
    body = f"{link_id}|{snapshot_time}|{from_state}|{to_state}"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def derive_state_transitions(observations: list[Observation]) -> tuple[TrendEvent, ...]:
    """Group by link_id, sort by snapshot_time, emit transitions."""

    by_link: dict[str, list[Observation]] = {}
    for obs in observations:
        by_link.setdefault(obs.link_id, []).append(obs)

    events: list[TrendEvent] = []
    for link_id, rows in by_link.items():
        ordered = sorted(rows, key=lambda o: o.snapshot_time)
        prev: Observation | None = None
        for obs in ordered:
            if prev is not None and prev.state != obs.state:
                events.append(
                    TrendEvent(
                        event_id=_event_id(
                            link_id,
                            obs.snapshot_time,
                            prev.state.value,
                            obs.state.value,
                        ),
                        link_id=link_id,
                        from_state=prev.state.value,
                        to_state=obs.state.value,
                        snapshot_time=obs.snapshot_time,
                    )
                )
            prev = obs
    events.sort(key=lambda e: (e.snapshot_time, e.link_id, e.event_id))
    return tuple(events)
