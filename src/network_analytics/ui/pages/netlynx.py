"""NetLynx monitoring + NOC cases with Pyvis topology links."""

from __future__ import annotations

from dash import html

from network_analytics.data_platform import GenerationStore
from network_analytics.netlynx import load_observations
from network_analytics.netlynx.cases import detect_cases
from network_analytics.netlynx.noc_graph import summarize_all_case_graphs
from network_analytics.netlynx.viz import write_case_artifact
from network_analytics.shared.config import ApplicationConfig


def netlynx_layout(config: ApplicationConfig) -> html.Div:
    store = GenerationStore(config.paths.data_root / "generations")
    observations = load_observations(store)
    cases = detect_cases(store)
    graphs = summarize_all_case_graphs(store)

    case_block: list = []
    if cases:
        case_rows = []
        for case in cases:
            viz = None
            try:
                path = write_case_artifact(store, case.case_id, config.paths.artifact_root / "noc")
                if path is not None:
                    rel = path.relative_to(config.paths.artifact_root.resolve()).as_posix()
                    viz = html.A("Topology", href=f"/artifacts/{rel}", target="_blank", className="action-link")
            except Exception:
                viz = html.Span("—", className="muted")
            case_rows.append(
                html.Tr(
                    [
                        html.Td(case.case_id),
                        html.Td(case.kind.value),
                        html.Td(str(len(case.affected_link_ids))),
                        html.Td(case.fact_generation_id or "—"),
                        html.Td(viz or "—"),
                    ]
                )
            )
        case_block = [
            html.H3("NOC cases (derived, read-only)"),
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("CaseId"),
                                html.Th("Kind"),
                                html.Th("Links"),
                                html.Th("FACT gen"),
                                html.Th("View"),
                            ]
                        )
                    ),
                    html.Tbody(case_rows),
                ],
                className="data-table",
            ),
        ]

    graph_block: list = []
    if graphs:
        g_rows = []
        for view in graphs:
            sample = ", ".join(f"{a}-{z}" for a, z, _lid in view.edges[:5])
            if len(view.edges) > 5:
                sample += ", …"
            g_rows.append(
                html.Tr(
                    [
                        html.Td(view.case.case_id),
                        html.Td(str(view.node_count)),
                        html.Td(str(view.edge_count)),
                        html.Td(sample or "—"),
                    ]
                )
            )
        graph_block = [
            html.H3("Affected adjacency summary"),
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [html.Th("CaseId"), html.Th("Nodes"), html.Th("Edges"), html.Th("Sample")]
                        )
                    ),
                    html.Tbody(g_rows),
                ],
                className="data-table",
            ),
        ]

    if not observations:
        return html.Div(
            [
                html.H2("NetLynx"),
                html.P(
                    "No promoted FACT generation. Collection disabled. "
                    "Use: network-analytics publish-fact path/to/FACT.csv",
                    className="muted",
                ),
                *case_block,
                *graph_block,
            ],
            className="panel",
        )

    parents = [
        o for o in observations if o.interface_type.value in {"LAG_PARENT", "PHYSICAL"}
    ] or observations

    rows = []
    for obs in parents[:100]:
        util = obs.max_util_pct()
        util_text = f"{util:g}%" if util is not None else "—"
        cap_text = f"{obs.capacity_mbps:g}" if obs.capacity_mbps is not None else "—"
        rows.append(
            html.Tr(
                [
                    html.Td(obs.link_id),
                    html.Td(f"{(obs.a_end or '—')} → {(obs.z_end or '—')}"),
                    html.Td(obs.interface_type.value),
                    html.Td(cap_text),
                    html.Td(util_text),
                    html.Td(obs.state.value),
                    html.Td(obs.snapshot_time),
                ]
            )
        )

    return html.Div(
        [
            html.H2("NetLynx"),
            html.P(
                f"Promoted generation {observations[0].source_generation_id}. Collection disabled.",
                className="muted",
            ),
            *case_block,
            *graph_block,
            html.H3("Observations"),
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Link"),
                                html.Th("Ends"),
                                html.Th("Type"),
                                html.Th("Capacity"),
                                html.Th("Max util"),
                                html.Th("State"),
                                html.Th("Snapshot"),
                            ]
                        )
                    ),
                    html.Tbody(rows),
                ],
                className="data-table",
            ),
        ],
        className="panel",
    )
