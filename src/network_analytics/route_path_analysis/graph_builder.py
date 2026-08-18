"""Build NetworkX topology graphs from normalized link records."""

from __future__ import annotations

from typing import Iterable

import networkx as nx

from .link_schema import LinkRecord, LinkRole


def build_graph(records: Iterable[LinkRecord]) -> nx.Graph:
    """Construct an undirected transport graph.

    Rules:
    - MEMBER rows never contribute capacity/traffic to topology edges.
    - Parallel PARENT/PHYSICAL edges between the same unordered pair aggregate:
      capacity sums when present; max util takes the maximum; weight takes minimum.
    - Missing capacity/util remain None (never zero-filled).
    """

    graph = nx.Graph()
    # key: frozenset({a, z}) -> aggregate state
    aggregates: dict[frozenset[str], dict] = {}

    for record in records:
        if record.role is LinkRole.MEMBER:
            # Diagnostic only — do not shape topology capacity
            continue
        a, z = record.normalized_ends()
        if a == z:
            continue
        key = frozenset({a, z})
        slot = aggregates.get(key)
        if slot is None:
            aggregates[key] = {
                "a": a,
                "z": z,
                "weight": record.weight,
                "capacity_mbps": record.capacity_mbps,
                "max_util": record.max_util_pct,
                "link_type": record.link_type,
                "member_count": record.member_count if record.member_count is not None else 1,
                "parent_count": 1,
            }
            continue

        slot["weight"] = min(float(slot["weight"]), float(record.weight))
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
            if current is None:
                slot["member_count"] = record.member_count
            else:
                slot["member_count"] = int(current) + int(record.member_count)

    for slot in aggregates.values():
        graph.add_edge(
            slot["a"],
            slot["z"],
            weight=float(slot["weight"]),
            capacity_mbps=slot["capacity_mbps"],
            max_util=slot["max_util"],
            link_type=str(slot["link_type"]),
            member_count=slot["member_count"],
            parent_count=int(slot["parent_count"]),
        )
    return graph
