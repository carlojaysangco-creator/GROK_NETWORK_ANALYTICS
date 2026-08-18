"""DFON / physical segment mapping publish and load."""

from __future__ import annotations

import json
from typing import Iterable, Mapping

from network_analytics.data_platform import (
    GenerationReference,
    GenerationStore,
    SourceIdentity,
    ValidationSummary,
)

from .future_contracts import LogicalLinkSegments, PhysicalSegment, SegmentKind

DATASET_DFON = "rpa_dfon_segments"
SCHEMA_VERSION = "dfon-v1"


def _kind(value: object) -> SegmentKind:
    text = str(value or "").strip().upper().replace("-", "_")
    for item in SegmentKind:
        if item.value == text or item.name == text:
            return item
    return SegmentKind.UNKNOWN


def segments_from_rows(rows: Iterable[Mapping]) -> list[LogicalLinkSegments]:
    by_link: dict[str, list[PhysicalSegment]] = {}
    metrics: dict[str, float | None] = {}
    for row in rows:
        lower = {str(k).strip().lower(): v for k, v in row.items()}

        def pick(*keys: str):
            for key in keys:
                if key.lower() in lower and lower[key.lower()] not in (None, ""):
                    return lower[key.lower()]
            return None

        link_id = str(pick("link_id", "iplinkid", "ip_link_id") or "").strip()
        if not link_id:
            continue
        order_raw = pick("segment_order", "order")
        try:
            order = int(order_raw) if order_raw is not None else len(by_link.get(link_id, [])) + 1
        except (TypeError, ValueError):
            order = len(by_link.get(link_id, [])) + 1
        kind = _kind(pick("segment_type", "kind", "type"))
        # Never invent engineering cost – only accept explicit numeric
        cost = pick("engineering_cost", "cost")
        try:
            eng = float(cost) if cost is not None and str(cost).strip() != "" else None
        except (TypeError, ValueError):
            eng = None
        metric = pick("routing_metric", "metric")
        try:
            rm = float(metric) if metric is not None and str(metric).strip() != "" else None
        except (TypeError, ValueError):
            rm = None
        by_link.setdefault(link_id, []).append(
            PhysicalSegment(
                order=order,
                kind=kind,
                identity=str(pick("segment_id", "identity") or "") or None,
                engineering_cost=eng,
            )
        )
        if rm is not None:
            metrics[link_id] = rm

    out: list[LogicalLinkSegments] = []
    for link_id, segs in by_link.items():
        ordered = tuple(sorted(segs, key=lambda s: s.order))
        out.append(
            LogicalLinkSegments(
                link_id=link_id,
                segments=ordered,
                routing_metric=metrics.get(link_id),
            )
        )
    return out


def publish_dfon_segments(
    store: GenerationStore,
    rows: Iterable[Mapping],
    *,
    producer_version: str,
    source: SourceIdentity | None = None,
    promote: bool = True,
) -> GenerationReference:
    accepted = segments_from_rows(rows)
    ref = store.create_candidate(
        dataset_name=DATASET_DFON,
        schema_version=SCHEMA_VERSION,
        producer_version=producer_version,
        source=source,
    )
    payload = "\n".join(
        json.dumps(
            {
                "link_id": item.link_id,
                "routing_metric": item.routing_metric,
                "segments": [
                    {
                        "order": s.order,
                        "kind": s.kind.value,
                        "identity": s.identity,
                        "engineering_cost": s.engineering_cost,
                    }
                    for s in item.segments
                ],
            },
            sort_keys=True,
        )
        for item in accepted
    ).encode("utf-8")
    store.add_data_file(ref, "segments.jsonl", payload + (b"\n" if payload else b""))
    if not accepted:
        store.mark_rejected(ref, ["no accepted DFON segment rows"])
        return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, store.load_manifest(ref.path))
    store.mark_validated(
        ref,
        input_count=len(list(rows)) if hasattr(rows, "__len__") else len(accepted),
        accepted_count=len(accepted),
        validation=ValidationSummary(),
    )
    store.publish(ref)
    if promote:
        store.promote(DATASET_DFON, ref.generation_id)
    return GenerationReference(ref.dataset_name, ref.generation_id, ref.path, store.load_manifest(ref.path))
