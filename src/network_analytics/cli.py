"""Local command-line entry point."""

from __future__ import annotations

import argparse
import csv
import json
import runpy
from pathlib import Path

from network_analytics.data_platform import GenerationStore, SourceIdentity
from network_analytics.netlynx import publish_observations
from network_analytics.route_path_analysis import publish_ftth_mapping, publish_link_topology
from network_analytics.route_path_analysis.loaders import (
    publish_daily_topology_from_fact,
    publish_ftth_file,
    publish_topology_file,
)
from network_analytics.shared.config import ApplicationConfig
from network_analytics.shared.locking import WriteLock
from network_analytics.ui import create_dash_app


def _store(config: ApplicationConfig) -> GenerationStore:
    return GenerationStore(config.paths.data_root / "generations")


def _lock(config: ApplicationConfig) -> WriteLock:
    return WriteLock(config.paths.runtime_root / "write_lock.sqlite3")


def _read_csv(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(text.splitlines()))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GROK Network Analytics (local only)")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("serve", help="Run the Dash UI (default)")
    sub.add_parser("check", help="Validate configuration and construct the app")

    p_topo = sub.add_parser("publish-topology", help="Publish topology CSV/XLSX")
    p_topo.add_argument("path", type=Path)
    p_topo.add_argument("--sheet", default=None)

    p_fact = sub.add_parser("publish-fact", help="Publish FACT CSV")
    p_fact.add_argument("path", type=Path)

    p_ftth = sub.add_parser("publish-ftth", help="Publish FTTH mapping CSV/XLSX")
    p_ftth.add_argument("path", type=Path)
    p_ftth.add_argument("--sheet", default=None)

    sub.add_parser("build-daily", help="Build daily topology generation from promoted FACT")
    sub.add_parser("publish-sample", help="Publish synthetic sample cohorts")

    parser.add_argument("--check", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = ApplicationConfig.from_environment(args.project_root)
    command = args.command
    if args.check:
        command = "check"
    if command is None:
        command = "serve"

    if command == "check":
        app = create_dash_app(config)
        print(
            json.dumps(
                {
                    "status": "ok",
                    "host": config.host,
                    "port": config.port,
                    "collection_enabled": config.collection_enabled,
                    "live_topology_enabled": config.live_topology_enabled,
                    "title": app.title,
                },
                sort_keys=True,
            )
        )
        return 0

    if command == "serve":
        app = create_dash_app(config)
        app.run(host=config.host, port=config.port, debug=False)
        return 0

    store = _store(config)

    if command == "publish-sample":
        script = args.project_root / "tools" / "publish_sample_data.py"
        if not script.is_file():
            script = Path(__file__).resolve().parents[2] / "tools" / "publish_sample_data.py"
        runpy.run_path(str(script), run_name="__main__")
        return 0

    with _lock(config).exclusive(timeout_seconds=60):
        if command == "build-daily":
            ref = publish_daily_topology_from_fact(store, producer_version="0.1.0.dev0", promote=True)
            print(
                json.dumps(
                    {
                        "dataset": "rpa_daily_topology",
                        "generation_id": ref.generation_id,
                        "status": ref.manifest.status.value,
                    }
                )
            )
            return 0

        if command == "publish-topology":
            ref = publish_topology_file(
                store,
                args.path,
                producer_version="0.1.0.dev0",
                sheet=args.sheet,
                promote=True,
            )
            print(
                json.dumps(
                    {
                        "dataset": "rpa_topology",
                        "generation_id": ref.generation_id,
                        "status": ref.manifest.status.value,
                    }
                )
            )
            return 0

        if command == "publish-ftth":
            ref = publish_ftth_file(
                store,
                args.path,
                producer_version="0.1.0.dev0",
                sheet=args.sheet,
                promote=True,
            )
            print(
                json.dumps(
                    {
                        "dataset": "rpa_ftth_mapping",
                        "generation_id": ref.generation_id,
                        "status": ref.manifest.status.value,
                    }
                )
            )
            return 0

        if command == "publish-fact":
            rows = _read_csv(args.path)
            source = SourceIdentity(system="cli", path_or_job=str(args.path), sha256="local")
            ref = publish_observations(
                store, rows, producer_version="0.1.0.dev0", source=source, promote=True
            )
            print(
                json.dumps(
                    {
                        "dataset": "netlynx_fact",
                        "generation_id": ref.generation_id,
                        "status": ref.manifest.status.value,
                    }
                )
            )
            return 0

    print(f"unknown command: {command}", file=__import__("sys").stderr)
    return 2
