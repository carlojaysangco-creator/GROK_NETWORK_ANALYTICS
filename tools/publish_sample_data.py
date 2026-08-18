#!/usr/bin/env python3
"""Publish synthetic topology + FACT cohorts for local demo only.

Does not read legacy repositories or SharePoint. Safe offline sample data.
Run from the project root after install:

    python tools/publish_sample_data.py
"""

from __future__ import annotations

from pathlib import Path

from network_analytics.data_platform import GenerationStore, SourceIdentity
from network_analytics.netlynx import publish_observations
from network_analytics.route_path_analysis import publish_ftth_mapping, publish_link_topology
from network_analytics.shared.config import ApplicationConfig


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    config = ApplicationConfig.from_environment(root)
    store = GenerationStore(config.paths.data_root / "generations")

    topology_rows = [
        {"a_end": "PE-A", "z_end": "AGG-1", "weight": "1", "capacity_mbps": "100000", "max_util": "35", "role": "parent"},
        {"a_end": "PE-A", "z_end": "AGG-2", "weight": "1", "capacity_mbps": "100000", "max_util": "42", "role": "parent"},
        {"a_end": "AGG-1", "z_end": "CORE-1", "weight": "1", "capacity_mbps": "200000", "max_util": "50", "role": "parent"},
        {"a_end": "AGG-2", "z_end": "CORE-1", "weight": "1", "capacity_mbps": "200000", "max_util": "48", "role": "parent"},
        {"a_end": "AGG-1", "z_end": "CORE-2", "weight": "2", "capacity_mbps": "100000", "max_util": "20", "role": "parent"},
        {"a_end": "AGG-2", "z_end": "CORE-2", "weight": "2", "capacity_mbps": "100000", "max_util": "22", "role": "parent"},
        {"a_end": "CORE-1", "z_end": "BNG-X", "weight": "1", "capacity_mbps": "200000", "max_util": "60", "role": "parent"},
        {"a_end": "CORE-2", "z_end": "BNG-X", "weight": "1", "capacity_mbps": "200000", "max_util": "55", "role": "parent"},
        {"a_end": "CORE-1", "z_end": "BNG-Y", "weight": "1.5", "capacity_mbps": "100000", "max_util": "30", "role": "parent"},
        {"a_end": "CORE-2", "z_end": "BNG-Y", "weight": "1", "capacity_mbps": "100000", "max_util": "28", "role": "parent"},
    ]
    topo = publish_link_topology(
        store,
        topology_rows,
        producer_version="0.1.0.dev0",
        source=SourceIdentity(system="sample", path_or_job="tools/publish_sample_data.py", sha256="synthetic"),
        promote=True,
    )
    print(f"topology promoted: {topo.generation_id}")

    fact_rows = [
        {
            "link_id": "PE-A-AGG-1",
            "snapshot_time": "2026-08-18T12:00:00Z",
            "a_end": "PE-A",
            "z_end": "AGG-1",
            "interface_type": "LAG_PARENT",
            "capacity_mbps": "100000",
            "in_util_pct": "35",
            "out_util_pct": "36",
            "state": "up",
        },
        {
            "link_id": "CORE-1-BNG-X",
            "snapshot_time": "2026-08-18T12:00:00Z",
            "a_end": "CORE-1",
            "z_end": "BNG-X",
            "interface_type": "LAG_PARENT",
            "capacity_mbps": "200000",
            "in_util_pct": "60",
            "out_util_pct": "58",
            "state": "up",
        },
        {
            "link_id": "CORE-2-BNG-Y",
            "snapshot_time": "2026-08-18T12:00:00Z",
            "a_end": "CORE-2",
            "z_end": "BNG-Y",
            "interface_type": "PHYSICAL",
            "capacity_mbps": "100000",
            "in_util_pct": "28",
            "out_util_pct": "27",
            "state": "up",
        },
    ]
    fact = publish_observations(
        store,
        fact_rows,
        producer_version="0.1.0.dev0",
        source=SourceIdentity(system="sample", path_or_job="tools/publish_sample_data.py", sha256="synthetic"),
        promote=True,
    )
    print(f"fact promoted: {fact.generation_id}")

    ftth_rows = [
        {"access_ne": "OLT-1", "homing_bng": "BNG-X", "service_class": "RES"},
        {"access_ne": "OLT-1", "homing_bng": "BNG-Y", "service_class": "RES"},
        {"access_ne": "OLT-2", "homing_bng": "BNG-X", "service_class": "BUS"},
    ]
    ftth = publish_ftth_mapping(
        store,
        ftth_rows,
        producer_version="0.1.0.dev0",
        source=SourceIdentity(system="sample", path_or_job="tools/publish_sample_data.py", sha256="synthetic"),
        promote=True,
    )
    print(f"ftth mapping promoted: {ftth.generation_id}")
    print("Sample data is under data/generations/ (gitignored). Restart the app to see NetLynx/Data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
