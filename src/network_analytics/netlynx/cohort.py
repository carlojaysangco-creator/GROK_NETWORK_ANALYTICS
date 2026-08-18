"""Offline FACT/observation cohort publish and read.

Column aliases aligned with Fixed_Network_Analytics FACT / link_ip_schema:
LinkID, AEnd_NE, ZEnd_NE, Interface_Type, InUti, OutUti, Capacity, SnapshotTime.
"""

from __future__ import annotations

import json
from typing import Iterable, Mapping

from network_analytics.data_platform import (
    GenerationReference,
    GenerationStore,
    SourceIdentity,
    ValidationSummary,
)
from network_analytics.shared.numbers import optional_float, utilization_to_percent
from network_analytics.shared.status import LinkState

from .contracts import InterfaceType, Observation

DATASET_FACT = "netlynx_fact"
SCHEMA_VERSION = "fact-v1"


def _interface_type(value: object) -> InterfaceType:
    text = str(value or "").strip().upper().replace("-", "_")
    for item in InterfaceType:
        if item.value == text or item.name == text:
            return item
    if "PARENT" in text:
        return InterfaceType.LAG_PARENT
    if "MEMBER" in text:
        return InterfaceType.LAG_MEMBER
    if text in {"PHY", "PHYSICAL"}:
        return InterfaceType.PHYSICAL
    return InterfaceType.UNKNOWN


def _link_state(value: object) -> LinkState:
    text = str(value or "").strip().lower()
    if text in {"up", "u", "active"}:
        return LinkState.UP
    if text in {"down", "d", "inactive", "admin down", "admin_down"}:
        return LinkState.DOWN
    if text in {"unavailable"}:
        return LinkState.UNAVAILABLE
    return LinkState.UNKNOWN


def observation_from_row(row: Mapping) -> Observation | None:
    lower = {str(k).strip().lower().replace(" ", "_"): v for k, v in row.items()}

    def pick(*keys: str):
        for key in keys:
            k = key.lower().replace(" ", "_")
            if k in lower and lower[k] not in (None, ""):
                return lower[k]
        for key in keys:
            token = key.lower().replace(" ", "_")
            for lk, lv in lower.items():
                if token in lk and lv not in (None, ""):
                    return lv
        return None

    link_id = str(pick("link_id", "linkid", "link") or "").strip()
    snapshot = str(pick("snapshot_time", "snapshottime", "snapshot", "time", "date_end") or "").strip()
    if not link_id or not snapshot:
        return None

    return Observation(
        link_id=link_id,
        snapshot_time=snapshot,
        a_end=(str(pick("a_end", "aend", "a_end_ne", "aend_ne") or "").strip().upper() or None),
        z_end=(str(pick("z_end", "zend", "z_end_ne", "zend_ne") or "").strip().upper() or None),
        interface_type=_interface_type(pick("interface_type", "if_type", "role")),
        capacity_mbps=optional_float(pick("capacity_mbps", "capacity")),
        in_util_pct=utilization_to_percent(pick("in_util_pct", "in_util", "inuti", "in_uti")),
        out_util_pct=utilization_to_percent(pick("out_util_pct", "out_util", "oututi", "out_uti")),
        state=_link_state(pick("state", "link_state", "status", "status_tag")),
        vendor=(str(pick("vendor") or "").strip() or None),
        domain=(str(pick("domain", "area") or "").strip() or None),
    )


def publish_observations(
    store: GenerationStore,
    rows: Iterable[Mapping],
    *,
    producer_version: str,
    source: SourceIdentity | None = None,
    promote: bool = True,
) -> GenerationReference:
    row_list = list(rows)
    accepted: list[Observation] = []
    rejected = 0
    for row in row_list:
        obs = observation_from_row(row)
        if obs is None:
            rejected += 1
        else:
            accepted.append(obs)

    ref = store.create_candidate(
        dataset_name=DATASET_FACT,
        schema_version=SCHEMA_VERSION,
        producer_version=producer_version,
        source=source,
    )
    payload = "\n".join(
        json.dumps(
            {
                "link_id": o.link_id,
                "snapshot_time": o.snapshot_time,
                "a_end": o.a_end,
                "z_end": o.z_end,
                "interface_type": o.interface_type.value,
                "capacity_mbps": o.capacity_mbps,
                "in_util_pct": o.in_util_pct,
                "out_util_pct": o.out_util_pct,
                "state": o.state.value,
                "vendor": o.vendor,
                "domain": o.domain,
            },
            sort_keys=True,
        )
        for o in accepted
    ).encode("utf-8")
    store.add_data_file(ref, "observations.jsonl", payload + (b"\n" if payload else b""))

    issues = [] if accepted else ["no accepted observations"]
    validation = ValidationSummary(required_columns_ok=not issues, issues=issues)
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
        store.promote(DATASET_FACT, ref.generation_id)
    return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, store.load_manifest(ref.path))


def load_observations(store: GenerationStore) -> list[Observation]:
    ref = store.resolve_readable(DATASET_FACT)
    if ref is None:
        return []
    path = ref.path / "data" / "observations.jsonl"
    if not path.is_file():
        return []
    out: list[Observation] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        out.append(
            Observation(
                link_id=str(raw["link_id"]),
                snapshot_time=str(raw["snapshot_time"]),
                a_end=raw.get("a_end"),
                z_end=raw.get("z_end"),
                interface_type=InterfaceType(str(raw.get("interface_type") or "UNKNOWN")),
                capacity_mbps=raw.get("capacity_mbps"),
                in_util_pct=raw.get("in_util_pct"),
                out_util_pct=raw.get("out_util_pct"),
                state=LinkState(str(raw.get("state") or "unknown")),
                vendor=raw.get("vendor"),
                domain=raw.get("domain"),
                source_generation_id=ref.generation_id,
            )
        )
    return out
