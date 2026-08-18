"""OLT homing cohort publish and load."""

from __future__ import annotations

import json
from typing import Iterable, Mapping

from network_analytics.data_platform import (
    GenerationReference,
    GenerationStore,
    SourceIdentity,
    ValidationSummary,
)

from .future_contracts import HomingState, OltHoming

DATASET_OLT = "rpa_olt_homing"
SCHEMA_VERSION = "olt-homing-v1"


def _state(value: object, bng_count: int) -> HomingState:
    text = str(value or "").strip().lower().replace("-", "_")
    for item in HomingState:
        if item.value == text or item.name.lower() == text:
            return item
    if bng_count <= 0:
        return HomingState.ZERO_OLT if text == "zero" else HomingState.MISSING
    if bng_count == 1:
        return HomingState.DIRECT
    if bng_count >= 2:
        return HomingState.DUAL_HOMED
    return HomingState.UNKNOWN


def publish_olt_homing(
    store: GenerationStore,
    rows: Iterable[Mapping],
    *,
    producer_version: str,
    source: SourceIdentity | None = None,
    promote: bool = True,
) -> GenerationReference:
    # group by access NE
    grouped: dict[str, list[str]] = {}
    states: dict[str, str] = {}
    for row in rows:
        lower = {str(k).strip().lower(): v for k, v in row.items()}

        def pick(*keys: str):
            for key in keys:
                if key.lower() in lower and lower[key.lower()] not in (None, ""):
                    return lower[key.lower()]
            return None

        access = str(pick("access_ne", "olt", "access") or "").strip().upper()
        bng = str(pick("homing_bng", "bng", "parent_node") or "").strip().upper()
        if not access:
            continue
        grouped.setdefault(access, [])
        if bng and bng not in grouped[access]:
            grouped[access].append(bng)
        st = pick("homing_state", "state", "homing_type")
        if st:
            states[access] = str(st)

    accepted = [
        OltHoming(
            access_ne=access,
            homing_bngs=tuple(bngs),
            state=_state(states.get(access), len(bngs)),
        )
        for access, bngs in grouped.items()
    ]

    ref = store.create_candidate(
        dataset_name=DATASET_OLT,
        schema_version=SCHEMA_VERSION,
        producer_version=producer_version,
        source=source,
    )
    payload = "\n".join(
        json.dumps(
            {
                "access_ne": h.access_ne,
                "homing_bngs": list(h.homing_bngs),
                "state": h.state.value,
            },
            sort_keys=True,
        )
        for h in accepted
    ).encode("utf-8")
    store.add_data_file(ref, "homing.jsonl", payload + (b"\n" if payload else b""))
    if not accepted:
        store.mark_rejected(ref, ["no accepted OLT homing rows"])
        return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, store.load_manifest(ref.path))
    store.mark_validated(
        ref,
        input_count=len(accepted),
        accepted_count=len(accepted),
        validation=ValidationSummary(),
    )
    store.publish(ref)
    if promote:
        store.promote(DATASET_OLT, ref.generation_id)
    return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, store.load_manifest(ref.path))


def load_olt_homing(store: GenerationStore) -> list[OltHoming]:
    ref = store.resolve_readable(DATASET_OLT)
    if ref is None:
        return []
    path = ref.path / "data" / "homing.jsonl"
    if not path.is_file():
        return []
    out: list[OltHoming] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        out.append(
            OltHoming(
                access_ne=str(raw["access_ne"]),
                homing_bngs=tuple(raw.get("homing_bngs") or []),
                state=HomingState(str(raw.get("state") or "unknown")),
                source_generation_id=ref.generation_id,
            )
        )
    return out
