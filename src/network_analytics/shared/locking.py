"""Single-writer coordination for generation promotion."""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class WriteLockTimeout(RuntimeError):
    """Could not acquire the exclusive write lock in time."""


class WriteLock:
    """Process-local exclusive lock backed by SQLite."""

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def exclusive(self, *, timeout_seconds: float = 30.0) -> Iterator[None]:
        deadline = time.monotonic() + timeout_seconds
        conn = sqlite3.connect(self.path, timeout=timeout_seconds)
        try:
            while True:
                try:
                    conn.execute("BEGIN EXCLUSIVE")
                    conn.execute(
                        "CREATE TABLE IF NOT EXISTS write_lock (id INTEGER PRIMARY KEY, holder TEXT, at TEXT)"
                    )
                    conn.execute(
                        "INSERT OR REPLACE INTO write_lock(id, holder, at) VALUES (1, 'network-analytics', datetime('now'))"
                    )
                    break
                except sqlite3.OperationalError:
                    if time.monotonic() >= deadline:
                        raise WriteLockTimeout(f"could not acquire write lock: {self.path}") from None
                    time.sleep(0.05)
            try:
                yield
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        finally:
            conn.close()
