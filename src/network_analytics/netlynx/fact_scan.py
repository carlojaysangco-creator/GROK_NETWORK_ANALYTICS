"""Optional DuckDB scan helpers for large FACT CSV files before publish."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def preview_fact_csv(path: Path, *, limit: int = 20) -> list[dict[str, Any]]:
    """Return a small preview; prefers DuckDB when available, else csv module."""

    path = path.expanduser().resolve()
    try:
        import duckdb

        con = duckdb.connect()
        try:
            rel = con.execute(
                "SELECT * FROM read_csv_auto(?, header=true) LIMIT ?",
                [str(path), int(limit)],
            )
            cols = [d[0] for d in rel.description]
            return [dict(zip(cols, row)) for row in rel.fetchall()]
        finally:
            con.close()
    except Exception:
        import csv

        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            out = []
            for i, row in enumerate(reader):
                if i >= limit:
                    break
                out.append(dict(row))
            return out


def count_fact_csv(path: Path) -> int:
    path = path.expanduser().resolve()
    try:
        import duckdb

        con = duckdb.connect()
        try:
            row = con.execute(
                "SELECT count(*) FROM read_csv_auto(?, header=true)",
                [str(path)],
            ).fetchone()
            return int(row[0]) if row else 0
        finally:
            con.close()
    except Exception:
        import csv

        with path.open(encoding="utf-8-sig", newline="") as handle:
            return sum(1 for _ in csv.DictReader(handle))
