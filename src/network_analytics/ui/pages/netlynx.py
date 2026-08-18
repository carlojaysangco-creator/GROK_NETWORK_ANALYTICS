"""NetLynx monitoring + NOC case summary from promoted FACT."""

from __future__ import annotations

from dash import html

from network_analytics.data_platform import GenerationStore
from network_analytics.netlynx import load_observations
from network_analytics.netlynx.cases import detect_cases
from network_analytics.shared.config import ApplicationConfig


def netlynx_layout(config: ApplicationConfig) -> html.Div:
    store = GenerationStore(config.paths.data_root / "generations")
    observations = load_observations(store)
    cases = detect_cases(store)

    case_block: list = []
    if cases:
        case_rows = []
        for case in cases:
            case_rows.append(
                html.Tr(
                    [
                        html.Td(case.case_id),
                        html.Td(case.kind.value),
                        html.Td(str(len(case.affected_link_ids))),
                        html.Td(case.fact_generation_id or "—"),
                    ]
                )
            )
        case_block = [
            html.H3("NOC cases (derived, read-only)"),
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [html.Th("CaseId"), html.Th("Kind"), html.Th("Links"), html.Th("FACT gen")]
                        )
                    ),
                    html.Tbody(case_rows),
                ],
                className="data-table",
            ),
        ]

    if not observations:
        return html.Div(
            [
                html.H2("NetLynx"),
                html.P(
                    "No promoted FACT generation is available. "
                    "Collection remains disabled; publish an offline cohort to populate this view.",
                    className="muted",
                ),
                *case_block,
            ],
            className="panel",
        )

    parents = [
        o
        for o in observations
        if o.interface_type.value in {"LAG_PARENT", "PHYSICAL"}
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
                f"Showing up to 100 parent/physical rows from promoted generation "
                f"({observations[0].source_generation_id}). Collection is disabled.",
                className="muted",
            ),
            *case_block,
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
