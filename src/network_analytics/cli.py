"""Local command-line entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from network_analytics.shared.config import ApplicationConfig
from network_analytics.ui import create_dash_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run GROK Network Analytics (local only)")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate configuration and construct the app without opening a listener",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = ApplicationConfig.from_environment(args.project_root)
    app = create_dash_app(config)
    if args.check:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "host": config.host,
                    "port": config.port,
                    "collection_enabled": config.collection_enabled,
                    "live_topology_enabled": config.live_topology_enabled,
                },
                sort_keys=True,
            )
        )
        return 0
    app.run(host=config.host, port=config.port, debug=False)
    return 0
