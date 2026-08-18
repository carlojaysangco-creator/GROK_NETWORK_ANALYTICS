"""In-process registry for gated live topology jobs (no device I/O)."""

from __future__ import annotations

import json
from pathlib import Path

from network_analytics.shared.config import ApplicationConfig

from .future_contracts import LiveJobState, LiveTopologyJob, LiveTopologyRequest
from .live import LiveTopologyDisabled, submit_live_topology_job


class LiveJobRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._path = self.root / "live_jobs.jsonl"

    def submit(self, config: ApplicationConfig, request: LiveTopologyRequest) -> LiveTopologyJob:
        job = submit_live_topology_job(config, request)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "job_id": job.job_id,
                        "state": job.state.value,
                        "live_validation_pending": job.live_validation_pending,
                        "error": job.error,
                        "request_id": request.request_id,
                        "device_ids": list(request.device_ids),
                        "requested_by": request.requested_by,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
        return job

    def list_jobs(self, *, limit: int = 50) -> list[dict]:
        if not self._path.is_file():
            return []
        lines = self._path.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(line) for line in reversed(lines) if line.strip()]
