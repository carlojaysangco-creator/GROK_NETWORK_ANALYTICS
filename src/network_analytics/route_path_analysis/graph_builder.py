"""Build NetworkX topology graphs from normalized link records."""

from __future__ import annotations

from typing import Iterable

import networkx as nx

from .gold_roles import GoldDevice
from .link_schema import LinkRecord, LinkRole
from .routing_policy import RoutingPolicy, default_policy


def build_graph(
    records: Iterable[LinkRecord],
    policy: RoutingPolicy | None = None,
    *,
    prefer_explicit_weight: bool = True,
    gold_lookup: dict[str, GoldDevice] | None = None,
) -> nx.Graph:
    active = policy or default_policy()
    gold = gold_lookup or {}
    graph = nx.Graph()
    aggregates: dict[frozenset[str], dict] = {}
    audit: list[dict] = []

    for record in records:
        if record.role is LinkRole.MEMBER:
            continue
        a, z = record.normalized_ends()
        if a == z:
            continue

        a_gold = gold.get(a)
        z_gold = gold.get(z)
        if (a_gold and a_gold.excluded) or (z_gold and z_gold.excluded):
            audit.append(
                {
                    "reason": "excluded_gold_device",
                    "a_end": a,
                    "z_end": z,
                    "link_id": record.link_id,
                }
            )
            continue

        explicit = record.weight if prefer_explicit_weight and record.weight != 1.0 else None
        resolved = active.edge_weight(
            a_end=a,
            z_end=z,
            link_type=record.link_type,
            explicit_weight=explicit,
        )

        key = frozenset({a, z})
        slot = aggregates.get(key)
        if slot is None:
            aggregates[key] = {
                "a": a,
                "z": z,
                "weight": resolved,
                "capacity_mbps": record.capacity_mbps,
                "max_util": record.max_util_pct,
                "link_type": record.link_type,
                "member_count": record.member_count if record.member_count is not None else 1,
                "parent_count": 1,
            }
            continue

        slot["weight"] = min(float(slot["weight"]), float(resolved))
        slot["parent_count"] = int(slot["parent_count"]) + 1
        if record.capacity_mbps is not None:
            if slot["capacity_mbps"] is None:
                slot["capacity_mbps"] = record.capacity_mbps
            else:
                slot["capacity_mbps"] = float(slot["capacity_mbps"]) + float(record.capacity_mbps)
        if record.max_util_pct is not None:
            if slot["max_util"] is None:
                slot["max_util"] = record.max_util_pct
            else:
                slot["max_util"] = max(float(slot["max_util"]), float(record.max_util_pct))
        if record.member_count is not None:
            current = slot["member_count"]
            slot["member_count"] = (
                record.member_count if current is None else int(current) + int(record.member_count)
            )

    for slot in aggregates.values():
        a, z = slot["a"], slot["z"]
        attrs = {
            "weight": float(slot["weight"]),
            "capacity_mbps": slot["capacity_mbps"],
            "max_util": slot["max_util"],
            "link_type": str(slot["link_type"]),
            "member_count": slot["member_count"],
            "parent_count": int(slot["parent_count"]),
        }
        if a in gold:
            attrs["a_role"] = gold[a].role
        if z in gold:
            attrs["z_role"] = gold[z].role
        graph.add_edge(a, z, **attrs)

    graph.graph["routing_policy_version"] = active.version
    graph.graph["gold_exclusion_audit"] = audit
    return graph
