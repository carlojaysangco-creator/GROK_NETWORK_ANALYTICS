"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from network_analytics.shared.config import ApplicationConfig


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def config(project_root: Path) -> ApplicationConfig:
    return ApplicationConfig.from_environment(project_root)
