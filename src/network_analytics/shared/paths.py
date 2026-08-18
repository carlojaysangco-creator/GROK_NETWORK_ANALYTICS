"""Path safety helpers."""

from __future__ import annotations

from pathlib import Path


def resolved(path: Path) -> Path:
    return path.expanduser().resolve()


def ensure_write_path(path: Path, *, root: Path) -> Path:
    """Ensure path resolves inside root and is safe for writes."""
    candidate = resolved(path)
    root = resolved(root)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {candidate}") from exc
    if candidate == root:
        raise ValueError("write path must be a child of the project root")
    return candidate
