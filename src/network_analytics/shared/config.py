"""Side-effect-free local application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .paths import ensure_write_path, resolved


PROJECT_MARKER = ".network-analytics-root"
PROJECT_MARKER_VALUE = "network-analytics-root-v1"

RESERVED_WRITE_ROOTS = (
    ".git",
    "docs",
    "src",
    "tests",
    "tools",
)


def _as_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean configuration value: {value!r}")


def _under_project(project_root: Path, value: str, *, name: str) -> Path:
    raw = Path(value)
    candidate = raw if raw.is_absolute() else project_root / raw
    try:
        return ensure_write_path(candidate, root=project_root)
    except ValueError as exc:
        raise ValueError(f"{name} must resolve inside the project root") from exc


def validate_project_root(project_root: Path) -> Path:
    root = resolved(project_root)
    marker = root / PROJECT_MARKER
    if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != PROJECT_MARKER_VALUE:
        raise ValueError(
            f"project root is not a Network Analytics repository (missing valid {PROJECT_MARKER})"
        )
    return root


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


@dataclass(frozen=True, slots=True)
class ApplicationPaths:
    project_root: Path
    data_root: Path
    runtime_root: Path
    artifact_root: Path
    log_root: Path

    @property
    def reference_root(self) -> Path:
        return self.data_root / "reference"

    @property
    def raw_root(self) -> Path:
        return self.data_root / "raw"

    @property
    def normalized_root(self) -> Path:
        return self.data_root / "normalized"

    @property
    def history_root(self) -> Path:
        return self.data_root / "history"

    @property
    def derived_root(self) -> Path:
        return self.data_root / "derived"

    def validate(self) -> "ApplicationPaths":
        root = validate_project_root(self.project_root)
        write_roots = (self.data_root, self.runtime_root, self.artifact_root, self.log_root)
        for path in write_roots:
            ensure_write_path(path, root=root)
            for relative in RESERVED_WRITE_ROOTS:
                reserved = resolved(root / relative)
                if path == reserved or path in reserved.parents or reserved in path.parents:
                    raise ValueError(f"write root intersects reserved project content: {path}")
        for index, left in enumerate(write_roots):
            for right in write_roots[index + 1 :]:
                if _overlaps(resolved(left), resolved(right)):
                    raise ValueError("data, runtime, artifact, and log roots must not overlap")
        return self


@dataclass(frozen=True, slots=True)
class ApplicationConfig:
    paths: ApplicationPaths
    host: str = "127.0.0.1"
    port: int = 8050
    collection_enabled: bool = False
    live_topology_enabled: bool = False
    admin_publish_token: str | None = None

    def validate(self) -> "ApplicationConfig":
        self.paths.validate()
        if self.host != "127.0.0.1":
            raise ValueError("non-loopback binding requires explicit later deployment configuration")
        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if self.live_topology_enabled and not self.collection_enabled:
            raise ValueError("live topology cannot be enabled while collection is disabled")
        return self

    @classmethod
    def from_environment(
        cls,
        project_root: Path,
        environ: Mapping[str, str] | None = None,
    ) -> "ApplicationConfig":
        values = os.environ if environ is None else environ
        root = validate_project_root(project_root)
        paths = ApplicationPaths(
            project_root=root,
            data_root=_under_project(root, values.get("NETWORK_ANALYTICS_DATA_ROOT", "data"), name="data root"),
            runtime_root=_under_project(
                root,
                values.get("NETWORK_ANALYTICS_RUNTIME_ROOT", "runtime"),
                name="runtime root",
            ),
            artifact_root=_under_project(
                root,
                values.get("NETWORK_ANALYTICS_ARTIFACT_ROOT", "artifacts"),
                name="artifact root",
            ),
            log_root=_under_project(root, values.get("NETWORK_ANALYTICS_LOG_ROOT", "logs"), name="log root"),
        )
        token = values.get("NETWORK_ANALYTICS_ADMIN_TOKEN")
        return cls(
            paths=paths,
            host=values.get("NETWORK_ANALYTICS_HOST", "127.0.0.1"),
            port=int(values.get("NETWORK_ANALYTICS_PORT", "8050")),
            collection_enabled=_as_bool(values.get("NETWORK_ANALYTICS_COLLECTION_ENABLED")),
            live_topology_enabled=_as_bool(values.get("NETWORK_ANALYTICS_LIVE_TOPOLOGY_ENABLED")),
            admin_publish_token=(token.strip() if token and token.strip() else None),
        ).validate()
