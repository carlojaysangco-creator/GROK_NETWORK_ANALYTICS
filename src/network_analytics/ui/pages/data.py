"""Data lineage and generation status page."""

from __future__ import annotations

from dash import html

from network_analytics.data_platform import GenerationStore
from network_analytics.shared.config import ApplicationConfig

KNOWN_DATASETS = (
    "rpa_topology",
    "rpa_daily_topology",
    "rpa_ftth_mapping",
    "netlynx_fact",
)


def _store(config: ApplicationConfig) -> GenerationStore:
    return GenerationStore(config.paths.data_root / "generations")


def data_layout(config: ApplicationConfig) -> html.Div:
    store = _store(config)
    sections: list = []
    for dataset in KNOWN_DATASETS:
        promoted = store.get_pointer(dataset, "promoted")
        lkg = store.get_pointer(dataset, "lkg")
        gens = store.list_generations(dataset)
        rows = []
        for g in gens[:20]:
            rows.append(
                html.Tr(
                    [
                        html.Td(g["generation_id"]),
                        html.Td(g["status"]),
                        html.Td(g["created_at"]),
                    ]
                )
            )
        sections.append(
            html.Div(
                [
                    html.H3(dataset),
                    html.P(
                        f"Promoted: {promoted or '—'} · LKG: {lkg or '—'}",
                        className="muted",
                    ),
                    html.Table(
                        [
                            html.Thead(
                                html.Tr(
                                    [html.Th("Generation"), html.Th("Status"), html.Th("Created")]
                                )
                            ),
                            html.Tbody(rows or [html.Tr([html.Td("No generations", colSpan=3)])]),
                        ],
                        className="data-table",
                    ),
                ],
                className="dataset-block",
            )
        )

    return html.Div(
        [
            html.H2("Data"),
            html.P(
                "Readers resolve only promoted or last-known-good generations. "
                "Newest directory or mtime is never authoritative. "
                "Use tools/publish_sample_data.py for synthetic local demo data only.",
                className="muted",
            ),
            *sections,
        ],
        className="panel",
    )
