"""Live topology remains disabled by default."""

from __future__ import annotations

from pathlib import Path

import pytest

from network_analytics.netlynx.future_contracts import LiveTopologyRequest
from network_analytics.netlynx.live import LiveTopologyDisabled, submit_live_topology_job
from network_analytics.shared.config import ApplicationConfig


def test_live_topology_disabled_by_default(project_root: Path) -> None:
    config = ApplicationConfig.from_environment(project_root)
    request = LiveTopologyRequest(
        request_id="t1",
        device_ids=("dev1",),
        command_profile="interfaces",
        requested_by="tester",
        allowlist_version="v0",
    )
    with pytest.raises(LiveTopologyDisabled):
        submit_live_topology_job(config, request)
