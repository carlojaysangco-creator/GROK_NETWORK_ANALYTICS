"""Route Path Analysis domain – native path computation and engineering semantics."""

from .contracts import (
    AnalysisResult,
    HopMetric,
    PairResult,
    PathClass,
    PathMetric,
    PathResultType,
    RoutePair,
    RouteRequest,
    TransportFrequency,
)
from .daily import DailyUnavailable, resolve_daily_graph, resolve_weekly_graph
from .ftth import FtthMapping, destinations_for_access, load_ftth_mappings, publish_ftth_mapping
from .graph_builder import build_graph
from .link_schema import LinkRecord, LinkRole, link_record_from_mapping, link_records_from_rows
from .reference import graph_from_promoted, publish_link_topology
from .routing_policy import RoutingPolicy, default_policy
from .service import analyze, validate_request

__all__ = [
    "AnalysisResult",
    "DailyUnavailable",
    "FtthMapping",
    "HopMetric",
    "LinkRecord",
    "LinkRole",
    "PairResult",
    "PathClass",
    "PathMetric",
    "PathResultType",
    "RoutePair",
    "RouteRequest",
    "RoutingPolicy",
    "TransportFrequency",
    "analyze",
    "build_graph",
    "default_policy",
    "destinations_for_access",
    "graph_from_promoted",
    "link_record_from_mapping",
    "link_records_from_rows",
    "load_ftth_mappings",
    "publish_ftth_mapping",
    "publish_link_topology",
    "resolve_daily_graph",
    "resolve_weekly_graph",
    "validate_request",
]
