"""DimLink cohort publish/load and FACT consistency checks."""

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

from .contracts import DimensionLink, InterfaceType, Observation
from .cohort import load_observations

DATASET_DIM_LINK = "netlynx_dim_link"
SCHEMA_VERSION = "dim-link-v1"


def _iface(value: object) -> InterfaceType:
    text = str(value or "").strip().upper().replace("-", "_")
    for item in InterfaceType:
        if item.value == text:
            return item
    if "PARENT" in text:
        return InterfaceType.LAG_PARENT
    if "MEMBER" in text:
        return InterfaceType.LAG_MEMBER
    return InterfaceType.PHYSICAL if "PHY" in text else InterfaceType.UNKNOWN


def dim_from_row(row: Mapping) -> DimensionLink | None:
    lower = {str(k).strip().lower().replace(" ", "_"): v for k, v in row.items()}

    def pick(*keys: str):
        for key in keys:
            k = key.lower().replace(" ", "_")
            if k in lower and lower[k] not in (None, ""):
                return lower[k]
        return None

    link_id = str(pick("link_id", "linkid") or "").strip()
    if not link_id:
        return None
    cap = pick("capacity_mbps", "capacity")
    try:
        capacity = float(cap) if cap is not None and str(cap).strip() else None
    except (TypeError, ValueError):
        capacity = None
    return DimensionLink(
        link_id=link_id,
        a_end=(str(pick("a_end", "aend", "a_end_ne") or "").strip().upper() or None),
        z_end=(str(pick("z_end", "zend", "z_end_ne") or "").strip().upper() or None),
        capacity_mbps=capacity,
        interface_type=_iface(pick("interface_type", "if_type", "role")),
        role=(str(pick("role") or "").strip() or None),
        domain=(str(pick("domain") or "").strip() or None),
        parent_link_id=(str(pick("parent_link_id", "parent_id") or "").strip() or None),
    )


def publish_dim_links(
    store: GenerationStore,
    rows: Iterable[Mapping],
    *,
    producer_version: str,
    source: SourceIdentity | None = None,
    promote: bool = True,
) -> GenerationReference:
    accepted = [d for d in (dim_from_row(r) for r in rows) if d is not None]
    ref = store.create_candidate(
        dataset_name=DATASET_DIM_LINK,
        schema_version=SCHEMA_VERSION,
        producer_version=producer_version,
        source=source,
    )
    payload = "\n".join(
        json.dumps(
            {
                "link_id": d.link_id,
                "a_end": d.a_end,
                "z_end": d.z_end,
                "capacity_mbps": d.capacity_mbps,
                "interface_type": d.interface_type.value,
                "role": d.role,
                "domain": d.domain,
                "parent_link_id": d.parent_link_id,
            },
            sort_keys=True,
        )
        for d in accepted
    ).encode("utf-8")
    store.add_data_file(ref, "dim_link.jsonl", payload + (b"\n" if payload else b""))
    if not accepted:
        store.mark_rejected(ref, ["no accepted dim link rows"])
        return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, store.load_manifest(ref.path))
    store.mark_validated(
        ref,
        input_count=len(accepted),
        accepted_count=len(accepted),
        validation=ValidationSummary(),
    )
    store.publish(ref)
    if promote:
        store.promote(DATASET_DIM_LINK, ref.generation_id)
    return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, store.load_manifest(ref.path))


def load_dim_links(store: GenerationStore) -> list[DimensionLink]:
    ref = store.resolve_readable(DATASET_DIM_LINK)
    if ref is None:
        return []
    path = ref.path / "data" / "dim_link.jsonl"
    if not path.is_file():
        return []
    out: list[DimensionLink] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        out.append(
            DimensionLink(
                link_id=str(raw["link_id"]),
                a_end=raw.get("a_end"),
                z_end=raw.get("z_end"),
                capacity_mbps=raw.get("capacity_mbps"),
                interface_type=InterfaceType(str(raw.get("interface_type") or "UNKNOWN")),
                role=raw.get("role"),
                domain=raw.get("domain"),
                parent_link_id=raw.get("parent_link_id"),
            )
        )
    return out


@dataclass(frozen=True, slots=True)
class CohortCheckResult:
    fact_only_link_ids: tuple[str, ...]
    dim_only_link_ids: tuple[str, ...]
    endpoint_mismatches: tuple[str, ...]


def check_fact_dim_consistency(store: GenerationStore) -> CohortCheckResult:
    facts = load_observations(store)
    dims = {d.link_id: d for d in load_dim_links(store)}
    fact_ids = {o.link_id for o in facts}
    dim_ids = set(dims)
    mismatches: list[str] = []
    for obs in facts:
        dim = dims.get(obs.link_id)
        if dim is None:
            continue
        if dim.a_end and obs.a_end and dim.a_end != obs.a_end:
            mismatches.append(obs.link_id)
        elif dim.z_end and obs.z_end and dim.z_end != obs.z_end:
            mismatches.append(obs.link_id)
    return CohortCheckResult(
        fact_only_link_ids=tuple(sorted(fact_ids - dim_ids)),
        dim_only_link_ids=tuple(sorted(dim_ids - fact_ids)),
        endpoint_mismatches=tuple(sorted(set(mismatches))),
    )
