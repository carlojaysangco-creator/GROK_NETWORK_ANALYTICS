"""Local command-line entry point."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from network_analytics.data_platform import GenerationStore, SourceIdentity
from network_analytics.netlynx import publish_observations
from network_analytics.route_path_analysis import publish_ftth_mapping, publish_link_topology
from network_analytics.shared.config import ApplicationConfig
from network_analytics.ui import create_dash_app


def _store(config: ApplicationConfig) -> GenerationStore:
    return GenerationStore(config.paths.data_root / "generations")


def _read_csv(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(text.splitlines()))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GROK Network Analytics (local only)")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("serve", help="Run the Dash UI (default)")
    sub.add_parser("check", help="Validate configuration and construct the app")

    p_topo = sub.add_parser("publish-topology", help="Publish a topology CSV into GenerationStore")
    p_topo.add_argument("csv_path", type=Path)

    p_fact = sub.add_parser("publish-fact", help="Publish a FACT CSV into GenerationStore")
    p_fact.add_argument("csv_path", type=Path)

    p_ftth = sub.add_parser("publish-ftth", help="Publish FTTH mapping CSV into GenerationStore")
    p_ftth.add_argument("csv_path", type=Path)

    sub.add_parser("publish-sample", help="Publish synthetic sample cohorts")

    # backward compatible flags
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
    source = SourceIdentity(
        system="cli",
        path_or_job=str(getattr(args, "csv_path", "sample")),
        sha256="local",
    )

    if command == "publish-sample":
        from tools.publish_sample_data import main as sample_main

        return sample_main()

    rows = _read_csv(args.csv_path)
    if command == "publish-topology":
        ref = publish_link_topology(
            store, rows, producer_version="0.1.0.dev0", source=source, promote=True
        )
        print(json.dumps({"dataset": "rpa_topology", "generation_id": ref.generation_id, "status": ref.manifest.status.value}))
        return 0
    if command == "publish-fact":
        ref = publish_observations(
            store, rows, producer_version="0.1.0.dev0", source=source, promote=True
        )
        print(json.dumps({"dataset": "netlynx_fact", "generation_id": ref.generation_id, "status": ref.manifest.status.value}))
        return 0
    if command == "publish-ftth":
        ref = publish_ftth_mapping(
            store, rows, producer_version="0.1.0.dev0", source=source, promote=True
        )
        print(json.dumps({"dataset": "rpa_ftth_mapping", "generation_id": ref.generation_id, "status": ref.manifest.status.value}))
        return 0

    print(f"unknown command: {command}", file=__import__("sys").stderr)
    return 2
