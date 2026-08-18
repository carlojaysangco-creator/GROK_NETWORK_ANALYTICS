"""Normalized link records for graph construction.

Missing numeric values remain None. They are never coerced to zero.
LAG_PARENT is the logical topology authority; LAG_MEMBER is diagnostic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable, Mapping


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


def _as_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed or parsed in {float("inf"), float("-inf")}:  # NaN / inf
        return None
    return parsed


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_role(value: Any) -> LinkRole:
    if value is None:
        return LinkRole.PHYSICAL
    text = str(value).strip().lower()
    if text in {"parent", "lag_parent", "lag-parent"}:
        return LinkRole.PARENT
    if text in {"member", "lag_member", "lag-member"}:
        return LinkRole.MEMBER
    if text in {"physical", "phy"}:
        return LinkRole.PHYSICAL
    return LinkRole.UNKNOWN


def link_record_from_mapping(row: Mapping[str, Any]) -> LinkRecord | None:
    """Build a LinkRecord from a loose tabular row.

    Returns None when endpoints are missing (row is rejected, not zero-filled).
    """

    def pick(*keys: str) -> Any:
        lower = {str(k).strip().lower(): v for k, v in row.items()}
        for key in keys:
            if key.lower() in lower:
                return lower[key.lower()]
        return None

    a_raw = pick("a_end", "aend", "source", "a_end_ne", "aend_ne")
    z_raw = pick("z_end", "zend", "destination", "z_end_ne", "zend_ne")
    a_end = str(a_raw or "").strip().upper()
    z_end = str(z_raw or "").strip().upper()
    if not a_end or not z_end:
        return None

    weight = _as_optional_float(pick("weight", "metric", "cost"))
    if weight is None:
        weight = 1.0

    capacity = _as_optional_float(pick("capacity_mbps", "capacity", "bw_mbps", "bandwidth_mbps"))
    max_util = _as_optional_float(pick("max_util_pct", "max_util", "util_pct", "utilization"))
    in_util = _as_optional_float(pick("in_util_pct", "in_util", "inuti"))
    out_util = _as_optional_float(pick("out_util_pct", "out_util", "oututi"))
    if max_util is None:
        candidates = [v for v in (in_util, out_util) if v is not None]
        max_util = max(candidates) if candidates else None

    link_id = pick("link_id", "linkid", "id")
    parent_id = pick("parent_link_id", "parent_id", "lag_parent")
    member_count = _as_optional_int(pick("member_count", "members"))
    link_type = str(pick("link_type", "type") or "TRANSPORT").strip() or "TRANSPORT"
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
    """Return accepted records and rejected row count."""
    accepted: list[LinkRecord] = []
    rejected = 0
    for row in rows:
        record = link_record_from_mapping(row)
        if record is None:
            rejected += 1
            continue
        accepted.append(record)
    return accepted, rejected
