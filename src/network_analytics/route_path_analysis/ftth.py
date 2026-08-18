"""FTTH Access NE → Homing BNG mapping."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Mapping

from network_analytics.data_platform import (
    GenerationReference,
    GenerationStore,
    SourceIdentity,
    ValidationSummary,
)

DATASET_FTTH = "rpa_ftth_mapping"
SCHEMA_VERSION = "ftth-v1"


@dataclass(frozen=True, slots=True)
class FtthMapping:
    access_ne: str
    homing_bng: str
    service_class: str | None = None


def mapping_from_row(row: Mapping) -> FtthMapping | None:
    lower = {str(k).strip().lower(): v for k, v in row.items()}

    def pick(*keys: str):
        for key in keys:
            if key.lower() in lower:
                return lower[key.lower()]
        return None

    access = str(pick("access_ne", "access", "olt", "a_end") or "").strip().upper()
    bng = str(pick("homing_bng", "bng", "z_end", "destination") or "").strip().upper()
    if not access or not bng:
        return None
    service = pick("service_class", "service", "class")
    return FtthMapping(
        access_ne=access,
        homing_bng=bng,
        service_class=(str(service).strip() if service is not None else None) or None,
    )


def publish_ftth_mapping(
    store: GenerationStore,
    rows: Iterable[Mapping],
    *,
    producer_version: str,
    source: SourceIdentity | None = None,
    promote: bool = True,
) -> GenerationReference:
    row_list = list(rows)
    accepted: list[FtthMapping] = []
    rejected = 0
    for row in row_list:
        item = mapping_from_row(row)
        if item is None:
            rejected += 1
        else:
            accepted.append(item)

    ref = store.create_candidate(
        dataset_name=DATASET_FTTH,
        schema_version=SCHEMA_VERSION,
        producer_version=producer_version,
        source=source,
    )
    payload = "\n".join(
        json.dumps(
            {
                "access_ne": m.access_ne,
                "homing_bng": m.homing_bng,
                "service_class": m.service_class,
            },
            sort_keys=True,
        )
        for m in accepted
    ).encode("utf-8")
    store.add_data_file(ref, "mappings.jsonl", payload + (b"\n" if payload else b""))

    issues = [] if accepted else ["no accepted FTTH mappings"]
    if issues:
        store.mark_rejected(ref, issues)
        return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, store.load_manifest(ref.path))

    store.mark_validated(
        ref,
        input_count=len(row_list),
        accepted_count=len(accepted),
        rejected_count=rejected,
        validation=ValidationSummary(issues=issues),
    )
    store.publish(ref)
    if promote:
        store.promote(DATASET_FTTH, ref.generation_id)
    return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, store.load_manifest(ref.path))


def load_ftth_mappings(store: GenerationStore) -> list[FtthMapping]:
    ref = store.resolve_readable(DATASET_FTTH)
    if ref is None:
        return []
    path = ref.path / "data" / "mappings.jsonl"
    if not path.is_file():
        return []
    out: list[FtthMapping] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        out.append(
            FtthMapping(
                access_ne=str(raw["access_ne"]),
                homing_bng=str(raw["homing_bng"]),
                service_class=raw.get("service_class"),
            )
        )
    return out


def destinations_for_access(store: GenerationStore, access_ne: str) -> tuple[str, ...]:
    access = access_ne.strip().upper()
    return tuple(
        sorted({m.homing_bng for m in load_ftth_mappings(store) if m.access_ne == access})
    )
