"""Gold device role dimension – optional policy enrichment."""

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

DATASET_GOLD = "rpa_gold_devices"
SCHEMA_VERSION = "gold-v1"


@dataclass(frozen=True, slots=True)
class GoldDevice:
    device_id: str
    role: str
    domain: str | None = None
    site: str | None = None
    excluded: bool = False


def publish_gold_devices(
    store: GenerationStore,
    rows: Iterable[Mapping],
    *,
    producer_version: str,
    source: SourceIdentity | None = None,
    promote: bool = True,
) -> GenerationReference:
    accepted: list[GoldDevice] = []
    for row in rows:
        lower = {str(k).strip().lower().replace(" ", "_"): v for k, v in row.items()}

        def pick(*keys: str):
            for key in keys:
                k = key.lower().replace(" ", "_")
                if k in lower and lower[k] not in (None, ""):
                    return lower[k]
            return None

        device = str(pick("device_id", "device", "ne", "node") or "").strip().upper()
        role = str(pick("role", "device_role", "node_role") or "").strip().upper()
        if not device or not role:
            continue
        excluded_raw = str(pick("excluded", "exclude", "test") or "").strip().lower()
        accepted.append(
            GoldDevice(
                device_id=device,
                role=role,
                domain=(str(pick("domain", "area") or "").strip() or None),
                site=(str(pick("site", "site_name") or "").strip() or None),
                excluded=excluded_raw in {"1", "true", "yes", "y", "excluded"},
            )
        )

    ref = store.create_candidate(
        dataset_name=DATASET_GOLD,
        schema_version=SCHEMA_VERSION,
        producer_version=producer_version,
        source=source,
    )
    payload = "\n".join(
        json.dumps(
            {
                "device_id": d.device_id,
                "role": d.role,
                "domain": d.domain,
                "site": d.site,
                "excluded": d.excluded,
            },
            sort_keys=True,
        )
        for d in accepted
    ).encode("utf-8")
    store.add_data_file(ref, "devices.jsonl", payload + (b"\n" if payload else b""))
    if not accepted:
        store.mark_rejected(ref, ["no accepted gold device rows"])
        return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, store.load_manifest(ref.path))
    store.mark_validated(
        ref,
        input_count=len(accepted),
        accepted_count=len(accepted),
        validation=ValidationSummary(),
    )
    store.publish(ref)
    if promote:
        store.promote(DATASET_GOLD, ref.generation_id)
    return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, store.load_manifest(ref.path))


def load_gold_lookup(store: GenerationStore) -> dict[str, GoldDevice]:
    ref = store.resolve_readable(DATASET_GOLD)
    if ref is None:
        return {}
    path = ref.path / "data" / "devices.jsonl"
    if not path.is_file():
        return {}
    out: dict[str, GoldDevice] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        device = GoldDevice(
            device_id=str(raw["device_id"]),
            role=str(raw["role"]),
            domain=raw.get("domain"),
            site=raw.get("site"),
            excluded=bool(raw.get("excluded")),
        )
        out[device.device_id] = device
    return out


def filter_excluded_endpoints(graph_nodes: set[str], lookup: dict[str, GoldDevice]) -> set[str]:
    """Return node ids that policy marks excluded."""
    return {n for n in graph_nodes if (lookup.get(n) and lookup[n].excluded)}
