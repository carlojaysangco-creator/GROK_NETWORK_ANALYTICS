"""Normalized link records for graph construction.

Field aliases aligned with Fixed_Network_Analytics link_ip_schema /
native_graph column detection (AEnd_NE, ZEnd_NE, Capacity, InUti, …).
Missing numeric values remain None. LAG_MEMBER never shapes topology capacity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable, Mapping

from network_analytics.shared.numbers import optional_float, optional_int, utilization_to_percent


class LinkRole(StrEnum):
    PARENT = "parent"
    MEMBER = "member"
    PHYSICAL = "physical"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class LinkRecord:
    a_end: str
    z_end: str
    weight: float = 1.0
    capacity_mbps: float | None = None
    max_util_pct: float | None = None
    in_util_pct: float | None = None
    out_util_pct: float | None = None
    link_type: str = "TRANSPORT"
    role: LinkRole = LinkRole.PHYSICAL
    link_id: str | None = None
    parent_link_id: str | None = None
    member_count: int | None = None

    def normalized_ends(self) -> tuple[str, str]:
        return self.a_end.strip().upper(), self.z_end.strip().upper()


def _as_role(value: Any) -> LinkRole:
    if value is None:
        return LinkRole.PHYSICAL
    text = str(value).strip().lower().replace("-", "_")
    if text in {"parent", "lag_parent"} or "parent" in text:
        return LinkRole.PARENT
    if text in {"member", "lag_member"} or "member" in text:
        return LinkRole.MEMBER
    if text in {"physical", "phy"}:
        return LinkRole.PHYSICAL
    return LinkRole.UNKNOWN


def link_record_from_mapping(row: Mapping[str, Any]) -> LinkRecord | None:
    def pick(*keys: str) -> Any:
        lower = {str(k).strip().lower().replace(" ", "_"): v for k, v in row.items()}
        for key in keys:
            k = key.lower().replace(" ", "_")
            if k in lower and lower[k] not in (None, ""):
                return lower[k]
        # substring fallback for headers like "Capacity (Mbps)"
        for key in keys:
            token = key.lower().replace(" ", "_")
            for lk, lv in lower.items():
                if token in lk and lv not in (None, ""):
                    return lv
        return None

    a_raw = pick(
        "a_end", "aend", "a_end_ne", "aend_ne", "source", "router",
        "node_a", "from", "from_node",
    )
    z_raw = pick(
        "z_end", "zend", "z_end_ne", "zend_ne", "destination", "dest",
        "node_b", "to", "to_node",
    )
    a_end = str(a_raw or "").strip().upper()
    z_end = str(z_raw or "").strip().upper()
    if not a_end or not z_end:
        return None

    weight = optional_float(pick("weight", "metric", "cost"))
    if weight is None:
        weight = 1.0

    capacity = optional_float(
        pick("capacity_mbps", "capacity", "capacity_(mbps)", "bw_mbps", "bandwidth_mbps")
    )
    in_util = utilization_to_percent(pick("in_util_pct", "in_util", "inuti", "in_uti", "rx_pct", "pct_in"))
    out_util = utilization_to_percent(pick("out_util_pct", "out_util", "oututi", "out_uti", "tx_pct", "pct_out"))
    max_util = utilization_to_percent(
        pick("max_util_pct", "max_util", "max_util_(%)", "util_pct", "utilization")
    )
    if max_util is None:
        candidates = [v for v in (in_util, out_util) if v is not None]
        max_util = max(candidates) if candidates else None

    link_id = pick("link_id", "linkid", "link", "moentity")
    parent_id = pick("parent_link_id", "parent_id", "lag_parent")
    member_count = optional_int(pick("member_count", "members"))
    link_type = str(pick("link_type", "linktype", "type") or "TRANSPORT").strip() or "TRANSPORT"
    role = _as_role(pick("role", "interface_type", "lag_role"))

    return LinkRecord(
        a_end=a_end,
        z_end=z_end,
        weight=float(weight),
        capacity_mbps=capacity,
        max_util_pct=max_util,
        in_util_pct=in_util,
        out_util_pct=out_util,
        link_type=link_type,
        role=role,
        link_id=str(link_id).strip() if link_id is not None else None,
        parent_link_id=str(parent_id).strip() if parent_id is not None else None,
        member_count=member_count,
    )


def link_records_from_rows(rows: Iterable[Mapping[str, Any]]) -> tuple[list[LinkRecord], int]:
    accepted: list[LinkRecord] = []
    rejected = 0
    for row in rows:
        record = link_record_from_mapping(row)
        if record is None:
            rejected += 1
            continue
        accepted.append(record)
    return accepted, rejected
