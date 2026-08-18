"""Configuration and path safety tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from network_analytics.shared.config import ApplicationConfig, validate_project_root


def test_project_root_marker_is_valid(project_root: Path) -> None:
    root = validate_project_root(project_root)
    assert root == project_root.resolve()


def test_default_config_is_loopback_and_collection_disabled(config: ApplicationConfig) -> None:
    assert config.host == "127.0.0.1"
    assert config.port == 8050
    assert config.collection_enabled is False
    assert config.live_topology_enabled is False


def test_write_roots_are_inside_project(config: ApplicationConfig) -> None:
    root = config.paths.project_root
    for path in (
        config.paths.data_root,
        config.paths.runtime_root,
        config.paths.artifact_root,
        config.paths.log_root,
    ):
        path.relative_to(root)


def test_live_topology_requires_collection(project_root: Path) -> None:
    with pytest.raises(ValueError, match="live topology cannot be enabled"):
        ApplicationConfig.from_environment(
            project_root,
            {
                "NETWORK_ANALYTICS_COLLECTION_ENABLED": "false",
                "NETWORK_ANALYTICS_LIVE_TOPOLOGY_ENABLED": "true",
            },
        )
