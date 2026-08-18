"""Gated live topology job framework (disabled by default)."""

from __future__ import annotations

from pathlib import Path

from network_analytics.shared.config import ApplicationConfig

from .future_contracts import LiveJobState, LiveTopologyJob, LiveTopologyRequest
from .live_allowlist import default_allowlist, load_allowlist, validate_request_against_allowlist


class LiveTopologyDisabled(RuntimeError):
    """Raised when live topology is not enabled or not authorised."""


def submit_live_topology_job(
    config: ApplicationConfig,
    request: LiveTopologyRequest,
    *,
    allowlist_path: Path | None = None,
) -> LiveTopologyJob:
    if not config.live_topology_enabled:
        raise LiveTopologyDisabled(
            "live topology is disabled; enable only with collection and explicit policy"
        )
    if not config.collection_enabled:
        raise LiveTopologyDisabled("live topology requires collection_enabled")

    path = allowlist_path or (config.paths.runtime_root / "live_allowlist.json")
    allowlist = load_allowlist(path) if path.is_file() else default_allowlist()
    ok, errors = validate_request_against_allowlist(
        allowlist,
        device_ids=request.device_ids,
        command_profile=request.command_profile,
    )
    if not ok:
        return LiveTopologyJob(
            job_id=f"live-{request.request_id}",
            request=request,
            state=LiveJobState.FAILED,
            live_validation_pending=True,
            error="; ".join(errors),
        )

    return LiveTopologyJob(
        job_id=f"live-{request.request_id}",
        request=request,
        state=LiveJobState.PENDING,
        live_validation_pending=True,
        error="LIVE_VALIDATION_PENDING: no real device transport in this build",
    )
