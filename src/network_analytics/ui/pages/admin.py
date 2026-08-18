"""Admin page – local CSV paste publish under single-writer lock."""

from __future__ import annotations

import csv
import io

from dash import Dash, Input, Output, State, dcc, html

from network_analytics.data_platform import GenerationStore, SourceIdentity
from network_analytics.netlynx import publish_observations
from network_analytics.route_path_analysis import publish_ftth_mapping, publish_link_topology
from network_analytics.shared.config import ApplicationConfig
from network_analytics.shared.locking import WriteLock, WriteLockTimeout


def _store(config: ApplicationConfig) -> GenerationStore:
    return GenerationStore(config.paths.data_root / "generations")


def _lock(config: ApplicationConfig) -> WriteLock:
    return WriteLock(config.paths.runtime_root / "write_lock.sqlite3")


def admin_layout(_config: ApplicationConfig) -> html.Div:
    return html.Div(
        [
            html.H2("Admin"),
            html.P(
                "Publish local CSV text into GenerationStore under a single-writer lock. "
                "Collection and live topology remain disabled.",
                className="muted",
            ),
            html.Div(
                [
                    html.Label("Dataset"),
                    dcc.Dropdown(
                        id="admin-dataset",
                        options=[
                            {"label": "RPA topology (rpa_topology)", "value": "topology"},
                            {"label": "NetLynx FACT (netlynx_fact)", "value": "fact"},
                            {"label": "FTTH mapping (rpa_ftth_mapping)", "value": "ftth"},
                        ],
                        value="topology",
                        clearable=False,
                    ),
                ],
                className="field",
                style={"maxWidth": "28rem", "marginBottom": "1rem"},
            ),
            html.Label("CSV text (header row required)"),
            dcc.Textarea(
                id="admin-csv",
                style={"width": "100%", "height": "180px", "fontFamily": "ui-monospace, monospace"},
                placeholder="AEnd_NE,ZEnd_NE,Capacity,InUti,OutUti,Interface_Type\nPE-A,CORE-1,100000,0.4,0.35,LAG_PARENT",
            ),
            html.Button(
                "Publish & promote",
                id="admin-publish",
                n_clicks=0,
                className="primary-btn",
                style={"marginTop": "0.75rem"},
            ),
            html.Div(id="admin-result", className="admin-result", style={"marginTop": "1rem"}),
        ],
        className="panel",
    )


def register_admin(app: Dash, config: ApplicationConfig) -> None:
    @app.callback(
        Output("admin-result", "children"),
        Input("admin-publish", "n_clicks"),
        State("admin-dataset", "value"),
        State("admin-csv", "value"),
        prevent_initial_call=True,
    )
    def _publish(n_clicks, dataset, csv_text):
        if not n_clicks:
            return ""
        if not csv_text or not str(csv_text).strip():
            return html.P("Paste CSV text with a header row.", className="error")
        try:
            rows = list(csv.DictReader(io.StringIO(str(csv_text).strip())))
        except Exception as exc:  # noqa: BLE001
            return html.P(f"CSV parse error: {exc}", className="error")
        if not rows:
            return html.P("No data rows found.", className="error")

        store = _store(config)
        source = SourceIdentity(system="admin-ui", path_or_job="paste", sha256="local")
        try:
            with _lock(config).exclusive(timeout_seconds=15):
                if dataset == "topology":
                    ref = publish_link_topology(
                        store, rows, producer_version="0.1.0.dev0", source=source, promote=True
                    )
                    name = "rpa_topology"
                elif dataset == "fact":
                    ref = publish_observations(
                        store, rows, producer_version="0.1.0.dev0", source=source, promote=True
                    )
                    name = "netlynx_fact"
                elif dataset == "ftth":
                    ref = publish_ftth_mapping(
                        store, rows, producer_version="0.1.0.dev0", source=source, promote=True
                    )
                    name = "rpa_ftth_mapping"
                else:
                    return html.P("Unknown dataset.", className="error")
        except WriteLockTimeout:
            return html.P("Another publish is in progress; try again shortly.", className="error")
        except Exception as exc:  # noqa: BLE001
            return html.P(f"Publish failed: {exc}", className="error")

        return html.Div(
            [
                html.P(
                    f"Published {name} generation {ref.generation_id} "
                    f"(status={ref.manifest.status.value}, accepted={ref.manifest.accepted_count}, "
                    f"rejected={ref.manifest.rejected_count})."
                ),
                html.P("Open Data or NetLynx / RPA to read the promoted generation.", className="muted"),
            ]
        )
