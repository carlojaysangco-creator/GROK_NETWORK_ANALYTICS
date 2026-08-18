"""Trend event derivation tests."""

from __future__ import annotations

from network_analytics.netlynx.contracts import InterfaceType, Observation
from network_analytics.netlynx.trends import derive_state_transitions
from network_analytics.shared.status import LinkState


def test_transition_event_stable_id() -> None:
    rows = [
        Observation(
            link_id="L1",
            snapshot_time="2026-08-18T10:00:00Z",
            a_end="A",
            z_end="B",
            interface_type=InterfaceType.LAG_PARENT,
            capacity_mbps=1000,
            in_util_pct=10,
            out_util_pct=10,
            state=LinkState.UP,
        ),
        Observation(
            link_id="L1",
            snapshot_time="2026-08-18T11:00:00Z",
            a_end="A",
            z_end="B",
            interface_type=InterfaceType.LAG_PARENT,
            capacity_mbps=1000,
            in_util_pct=0,
            out_util_pct=0,
            state=LinkState.DOWN,
        ),
    ]
    events = derive_state_transitions(rows)
    assert len(events) == 1
    assert events[0].from_state == "up"
    assert events[0].to_state == "down"
    again = derive_state_transitions(rows)
    assert again[0].event_id == events[0].event_id
