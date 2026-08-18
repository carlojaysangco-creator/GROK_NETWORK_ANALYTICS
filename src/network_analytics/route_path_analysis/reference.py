"""Load tabular link topology and publish immutable generations."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Iterable, Mapping

from network_analytics.data_platform import (
    GenerationReference,
    GenerationStore,
    SourceIdentity,
    ValidationSummary,
)

from .gold_roles import load_gold_lookup
from .graph_builder import build_graph
from .link_schema import LinkRecord, LinkRole, link_records_from_rows

DATASET_TOPOLOGY = "rpa_topology"
SCHEMA_VERSION = "topology-v1"


def rows_from_csv_text(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def rows_from_csv_path(path: Path) -> list[dict[str, str]]:
    return rows_from_csv_text(path.read_text(encoding="utf-8"))


def publish_link_topology(
    store: GenerationStore,
    rows: Iterable[Mapping],
    *,
    producer_version: str,
    source: SourceIdentity | None = None,
    promote: bool = True,
) -> GenerationReference:
    row_list = list(rows)
    accepted, rejected = link_records_from_rows(row_list)
    issues: list[str] = []
    if not accepted:
        issues.append("no accepted link records")

    ref = store.create_candidate(
        dataset_name=DATASET_TOPOLOGY,
        schema_version=SCHEMA_VERSION,
        producer_version=producer_version,
        source=source,
        metadata={"row_count_input": len(row_list)},
    )

    payload = "\n".join(
        json.dumps(
            {
                "a_end": r.a_end,
                "z_end": r.z_end,
                "weight": r.weight,
                "capacity_mbps": r.capacity_mbps,
                "max_util_pct": r.max_util_pct,
                "link_type": r.link_type,
                "role": r.role.value,
                "link_id": r.link_id,
                "parent_link_id": r.parent_link_id,
                "member_count": r.member_count,
            },
            sort_keys=True,
        )
        for r in accepted
    ).encode("utf-8")
    store.add_data_file(ref, "links.jsonl", payload + (b"\n" if payload else b""))

    validation = ValidationSummary(required_columns_ok=not issues, null_ok=True, issues=issues)
    if issues:
        store.mark_rejected(ref, issues)
        return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, store.load_manifest(ref.path))

    store.mark_validated(
        ref,
        input_count=len(row_list),
        accepted_count=len(accepted),
        rejected_count=rejected,
        validation=validation,
    )
    store.publish(ref)
    if promote:
        store.promote(DATASET_TOPOLOGY, ref.generation_id)
    manifest = store.load_manifest(ref.path)
    return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, manifest)


def load_records_from_generation(ref: GenerationReference) -> list[LinkRecord]:
    path = ref.path / "data" / "links.jsonl"
    if not path.is_file():
        return []
    records: list[LinkRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        records.append(
            LinkRecord(
                a_end=str(raw["a_end"]),
                z_end=str(raw["z_end"]),
                weight=float(raw.get("weight") or 1.0),
                capacity_mbps=raw.get("capacity_mbps"),
                max_util_pct=raw.get("max_util_pct"),
                link_type=str(raw.get("link_type") or "TRANSPORT"),
                role=LinkRole(str(raw.get("role") or "physical")),
                link_id=raw.get("link_id"),
                parent_link_id=raw.get("parent_link_id"),
                member_count=raw.get("member_count"),
            )
        )
    return records


def graph_from_promoted(store: GenerationStore):
    ref = store.resolve_readable(DATASET_TOPOLOGY)
    if ref is None:
        return None
    records = load_records_from_generation(ref)
    if not records:
        return None
    gold = load_gold_lookup(store)
    return build_graph(records, gold_lookup=gold or None)
