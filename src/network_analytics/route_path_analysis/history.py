"""Append-only analysis run history under target-owned data root."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .contracts import AnalysisResult, PathClass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class AnalysisRunSummary:
    run_id: str
    created_at: str
    frequency: str
    source: str
    destination: str
    min_weight: float | None
    default_count: int
    alternate_count: int
    topology_generation_id: str | None


def append_run(
    history_root: Path,
    result: AnalysisResult,
    *,
    topology_generation_id: str | None = None,
) -> AnalysisRunSummary:
    history_root.mkdir(parents=True, exist_ok=True)
    pair = result.pairs[0]
    summary = AnalysisRunSummary(
        run_id=f"run-{uuid.uuid4().hex[:12]}",
        created_at=_utc_now(),
        frequency=result.frequency.value,
        source=pair.source,
        destination=pair.destination,
        min_weight=pair.min_weight,
        default_count=sum(1 for p in pair.paths if p.path_class is PathClass.DEFAULT),
        alternate_count=sum(1 for p in pair.paths if p.path_class is PathClass.ALTERNATE),
        topology_generation_id=topology_generation_id,
    )
    path = history_root / "analysis_runs.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(summary), sort_keys=True) + "\n")
    return summary


def list_recent_runs(history_root: Path, *, limit: int = 50) -> list[AnalysisRunSummary]:
    path = history_root / "analysis_runs.jsonl"
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    out: list[AnalysisRunSummary] = []
    for line in reversed(lines):
        if not line.strip():
            continue
        raw = json.loads(line)
        out.append(AnalysisRunSummary(**raw))
    return out
