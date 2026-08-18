"""Gated live topology job framework (disabled by default)."""

from __future__ import annotations

from network_analytics.shared.config import ApplicationConfig

from .future_contracts import LiveJobState, LiveTopologyJob, LiveTopologyRequest


class LiveTopologyDisabled(RuntimeError):
    """Raised when live topology is not enabled or not authorised."""


def submit_live_topology_job(
    config: ApplicationConfig,
    request: LiveTopologyRequest,
) -> LiveTopologyJob:
    """Accept a live topology request only when the feature flag is on.

    Even when enabled, real device access remains LIVE_VALIDATION_PENDING until
    a separate authorised validation task. This function never opens sockets.
    """

    if not config.live_topology_enabled:
        raise LiveTopologyDisabled(
            "live topology is disabled; enable only with collection and explicit policy"
        )
    if not config.collection_enabled:
        raise LiveTopologyDisabled("live topology requires collection_enabled")

    # Framework only – no transport, no Paramiko, no device I/O
    return LiveTopologyJob(
        job_id=f"live-{request.request_id}",
        request=request,
        state=LiveJobState.PENDING,
        live_validation_pending=True,
        error="LIVE_VALIDATION_PENDING: no real device transport in this build",
    )
