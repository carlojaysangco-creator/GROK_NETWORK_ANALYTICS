"""Shared platform infrastructure."""

from .config import ApplicationConfig, ApplicationPaths
from .status import DataState, LinkState

__all__ = [
    "ApplicationConfig",
    "ApplicationPaths",
    "DataState",
    "LinkState",
]
