"""Strict status and state vocabulary.

Missing numeric values remain null / unavailable. They are never silently
coerced to zero. Planning truth and observed operational truth may disagree;
both provenance records survive.
"""

from __future__ import annotations

from enum import StrEnum


class DataState(StrEnum):
    """Freshness / availability of a data generation or snapshot."""

    FRESH = "fresh"
    DELAYED = "delayed"
    STALE = "stale"
    MISSING = "missing"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class LinkState(StrEnum):
    """Operational state of a link or interface."""

    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
