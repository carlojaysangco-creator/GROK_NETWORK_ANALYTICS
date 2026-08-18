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
from .graph_builder import build_graph
from .link_schema import LinkRecord, LinkRole, link_record_from_mapping, link_records_from_rows
from .reference import graph_from_promoted, publish_link_topology
from .service import analyze, validate_request

__all__ = [
    "AnalysisResult",
    "HopMetric",
    "LinkRecord",
    "LinkRole",
    "PairResult",
    "PathClass",
    "PathMetric",
    "PathResultType",
    "RoutePair",
    "RouteRequest",
    "TransportFrequency",
    "analyze",
    "build_graph",
    "graph_from_promoted",
    "link_record_from_mapping",
    "link_records_from_rows",
    "publish_link_topology",
    "validate_request",
]
