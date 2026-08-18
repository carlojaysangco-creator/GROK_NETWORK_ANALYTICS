"""Streaming FACT publish and NOC graph tests."""

from __future__ import annotations

from pathlib import Path

from network_analytics.data_platform import GenerationStore
from network_analytics.netlynx.noc_graph import summarize_all_case_graphs
from network_analytics.netlynx.stream_publish import publish_fact_csv_streaming


def test_stream_publish_and_graph(tmp_path: Path) -> None:
    csv_path = tmp_path / "fact.csv"
    csv_path.write_text(
        "LinkID,SnapshotTime,AEnd_NE,ZEnd_NE,Interface_Type,Capacity,InUti,OutUti,State\n"
        "L1,2026-08-18T12:00:00Z,A,B,LAG_PARENT,10000,0.9,0.85,up\n"
        "L2,2026-08-18T12:00:00Z,C,D,PHYSICAL,10000,0.1,0.1,down\n",
        encoding="utf-8",
    )
    store = GenerationStore(tmp_path / "gens")
    ref = publish_fact_csv_streaming(store, csv_path, producer_version="0.1.0.dev0", promote=True)
    assert ref.manifest.accepted_count == 2
    graphs = summarize_all_case_graphs(store)
    assert graphs  # down and/or high util cases produce adjacency
