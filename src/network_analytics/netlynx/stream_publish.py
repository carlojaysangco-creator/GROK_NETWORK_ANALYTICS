"""Stream large FACT CSV files into GenerationStore without full in-memory load."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from network_analytics.data_platform import (
    GenerationReference,
    GenerationStore,
    SourceIdentity,
    ValidationSummary,
)

from .cohort import DATASET_FACT, SCHEMA_VERSION, observation_from_row


def _file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def publish_fact_csv_streaming(
    store: GenerationStore,
    path: Path,
    *,
    producer_version: str,
    promote: bool = True,
    progress_every: int = 50_000,
) -> GenerationReference:
    path = path.expanduser().resolve()
    source = SourceIdentity(system="file", path_or_job=str(path), sha256=_file_sha256(path))
    ref = store.create_candidate(
        dataset_name=DATASET_FACT,
        schema_version=SCHEMA_VERSION,
        producer_version=producer_version,
        source=source,
    )

    accepted = 0
    rejected = 0
    input_count = 0
    out_path = ref.path / "data" / "observations.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(encoding="utf-8-sig", newline="") as src, out_path.open("w", encoding="utf-8") as dst:
        reader = csv.DictReader(src)
        for row in reader:
            input_count += 1
            obs = observation_from_row(row)
            if obs is None:
                rejected += 1
                continue
            dst.write(
                json.dumps(
                    {
                        "link_id": obs.link_id,
                        "snapshot_time": obs.snapshot_time,
                        "a_end": obs.a_end,
                        "z_end": obs.z_end,
                        "interface_type": obs.interface_type.value,
                        "capacity_mbps": obs.capacity_mbps,
                        "in_util_pct": obs.in_util_pct,
                        "out_util_pct": obs.out_util_pct,
                        "state": obs.state.value,
                        "vendor": obs.vendor,
                        "domain": obs.domain,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            accepted += 1
            if progress_every and accepted % progress_every == 0:
                # intentional lightweight progress marker in metadata only at end
                pass

    if accepted == 0:
        store.mark_rejected(ref, ["no accepted observations"])
        return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, store.load_manifest(ref.path))

    store.mark_validated(
        ref,
        input_count=input_count,
        accepted_count=accepted,
        rejected_count=rejected,
        validation=ValidationSummary(),
    )
    store.publish(ref)
    if promote:
        store.promote(DATASET_FACT, ref.generation_id)
    return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, store.load_manifest(ref.path))
