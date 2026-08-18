"""Append-only publish audit log under runtime root."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class PublishAuditEvent:
    at: str
    actor: str
    dataset: str
    generation_id: str
    status: str
    accepted: int
    rejected: int
    source: str


class PublishAuditLog:
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: PublishAuditEvent) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")

    def list_recent(self, *, limit: int = 50) -> list[PublishAuditEvent]:
        if not self.path.is_file():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
        out: list[PublishAuditEvent] = []
        for line in reversed(lines):
            if not line.strip():
                continue
            raw = json.loads(line)
            out.append(PublishAuditEvent(**raw))
        return out


def audit_event(
    *,
    actor: str,
    dataset: str,
    generation_id: str,
    status: str,
    accepted: int,
    rejected: int,
    source: str,
) -> PublishAuditEvent:
    return PublishAuditEvent(
        at=_utc(),
        actor=actor,
        dataset=dataset,
        generation_id=generation_id,
        status=status,
        accepted=accepted,
        rejected=rejected,
        source=source,
    )
