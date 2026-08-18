"""Export analysis results to credential-free JSON."""

from __future__ import annotations

import json
from pathlib import Path

from .contracts import AnalysisResult, PathClass


def analysis_to_dict(result: AnalysisResult) -> dict:
    pairs = []
    for pair in result.pairs:
        paths = []
        for path in pair.paths:
            paths.append(
                {
                    "order": path.order,
                    "path_class": path.path_class.value,
                    "nodes": list(path.nodes),
                    "weight": path.weight,
                    "result_type": path.result_type.value,
                    "bottleneck_capacity_mbps": path.bottleneck_capacity_mbps,
                    "maximum_utilization_pct": path.maximum_utilization_pct,
                    "minimum_remaining_mbps": path.minimum_remaining_mbps,
                    "hops": [
                        {
                            "source": h.source,
                            "destination": h.destination,
                            "weight": h.weight,
                            "capacity_mbps": h.capacity_mbps,
                            "utilization_pct": h.utilization_pct,
                            "remaining_mbps": h.remaining_mbps,
                            "link_type": h.link_type,
                        }
                        for h in path.hops
                    ],
                }
            )
        pairs.append(
            {
                "source": pair.source,
                "destination": pair.destination,
                "min_weight": pair.min_weight,
                "additional_bw_mbps": pair.additional_bw_mbps,
                "paths": paths,
                "warnings": list(pair.warnings),
            }
        )
    return {
        "frequency": result.frequency.value,
        "pairing_mode": result.pairing_mode,
        "alternate_branches": result.alternate_branches,
        "pairs": pairs,
        "warnings": list(result.warnings),
    }


def write_analysis_json(result: AnalysisResult, path: Path) -> Path:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(analysis_to_dict(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
