"""NetLynx monitoring page – offline promoted observations only."""

from __future__ import annotations

from dash import html

from network_analytics.data_platform import GenerationStore
from network_analytics.netlynx import load_observations
from network_analytics.shared.config import ApplicationConfig


def netlynx_layout(config: ApplicationConfig) -> html.Div:
    store = GenerationStore(config.paths.data_root / "generations")
    observations = load_observations(store)

    if not observations:
        return html.Div(
            [
                html.H2("NetLynx"),
                html.P(
                    "No promoted FACT generation is available. "
                    "Collection remains disabled; publish an offline cohort to populate this view.",
                    className="muted",
                ),
            ],
            className="panel",
        )

    # Parent-only summary for display (members diagnostic)
    parents = [o for o in observations if o.interface_type.value == "LAG_PARENT" or o.interface_type.value == "PHYSICAL"]
    if not parents:
        parents = observations

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
