"""Routing policy – link-type weights and N4I floor.

Weights are planning metrics, not engineering cost. Unknown link types get a
high default rather than inventing a preferential low cost.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_LINK_WEIGHT = 1000.0
N4I_LINK_WEIGHT = 100_000.0

# Conservative defaults inspired by protected native behaviour; operators may
# publish a policy generation later without changing calculation contracts.
BUILTIN_LINKTYPE_WEIGHTS: dict[str, float] = {
    "CORE": 1.0,
    "AGG": 1.0,
    "ACCESS": 5.0,
    "PE": 2.0,
    "TRANSPORT": 1.0,
    "BACKBONE": 1.0,
    "METRO": 2.0,
    "UNKNOWN": DEFAULT_LINK_WEIGHT,
    "-": DEFAULT_LINK_WEIGHT,
    "MIXED": DEFAULT_LINK_WEIGHT,
}


def normalize_link_type(value: object) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return "UNKNOWN"
    text = text.replace("-", "_").replace(" ", "_")
    return text


def is_n4i_node(node: object) -> bool:
    s = str(node or "").strip().upper()
    return ("N4I" in s) or ("HUN4" in s) or ("CIN4" in s)


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    version: str = "builtin-v1"
    linktype_weights: dict[str, float] | None = None
    default_weight: float = DEFAULT_LINK_WEIGHT
    n4i_floor: float = N4I_LINK_WEIGHT

    def weight_for_link_type(self, link_type: object) -> float:
        table = self.linktype_weights or BUILTIN_LINKTYPE_WEIGHTS
        key = normalize_link_type(link_type)
        if key in table:
            return float(table[key])
        # try coarse tokens
        for token, weight in table.items():
            if token and token in key:
                return float(weight)
        return float(self.default_weight)

    def edge_weight(
        self,
        *,
        a_end: str,
        z_end: str,
        link_type: object,
        explicit_weight: float | None,
    ) -> float:
        if explicit_weight is not None:
            base = float(explicit_weight)
        else:
            base = self.weight_for_link_type(link_type)
        if is_n4i_node(a_end) or is_n4i_node(z_end):
            return max(base, float(self.n4i_floor))
        return base


def default_policy() -> RoutingPolicy:
    return RoutingPolicy()
