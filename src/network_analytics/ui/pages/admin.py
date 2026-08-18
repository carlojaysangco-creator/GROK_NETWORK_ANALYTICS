"""Admin page – local CSV publish under write lock with optional token and audit."""

from __future__ import annotations

import csv
import io

from dash import Dash, Input, Output, State, dcc, html

from network_analytics.data_platform import GenerationStore, SourceIdentity
from network_analytics.netlynx import publish_observations
from network_analytics.netlynx.live_registry import LiveJobRegistry
from network_analytics.route_path_analysis import publish_ftth_mapping, publish_link_topology
from network_analytics.shared.audit import PublishAuditLog, audit_event
from network_analytics.shared.config import ApplicationConfig
from network_analytics.shared.locking import WriteLock, WriteLockTimeout


def _store(config: ApplicationConfig) -> GenerationStore:
    return GenerationStore(config.paths.data_root / "generations")


def _lock(config: ApplicationConfig) -> WriteLock:
    return WriteLock(config.paths.runtime_root / "write_lock.sqlite3")


def _audit(config: ApplicationConfig) -> PublishAuditLog:
    return PublishAuditLog(config.paths.runtime_root / "publish_audit.jsonl")


def admin_layout(config: ApplicationConfig) -> html.Div:
    recent = _audit(config).list_recent(limit=15)
    audit_rows = [
        html.Tr(
            [
                html.Td(e.at),
                html.Td(e.dataset),
                html.Td(e.generation_id),
                html.Td(e.status),
                html.Td(f"{e.accepted}/{e.rejected}"),
            ]
        )
        for e in recent
    ]
    jobs = LiveJobRegistry(config.paths.runtime_root / "live").list_jobs(limit=10)
    job_rows = [
        html.Tr(
            [
                html.Td(j.get("job_id", "—")),
                html.Td(j.get("state", "—")),
                html.Td(str(j.get("live_validation_pending", ""))),
                html.Td(j.get("error") or "—"),
            ]
        )
        for j in jobs
    ]
    token_note = (
        "Admin token is configured (NETWORK_ANALYTICS_ADMIN_TOKEN)."
        if config.admin_publish_token
        else "No admin token configured (publish allowed locally)."
    )
    return html.Div(
        [
            html.H2("Admin"),
            html.P(
                "Publish local CSV under a single-writer lock. Live jobs list is registry-only (no device I/O).",
                className="muted",
            ),
            html.P(token_note, className="muted"),
            html.Div(
                [
                    html.Label("Dataset"),
                    dcc.Dropdown(
                        id="admin-dataset",
                        options=[
                            {"label": "RPA topology", "value": "topology"},
                            {"label": "NetLynx FACT", "value": "fact"},
                            {"label": "FTTH mapping", "value": "ftth"},
                        ],
                        value="topology",
                        clearable=False,
                    ),
                ],
                className="field",
                style={"maxWidth": "28rem", "marginBottom": "0.75rem"},
            ),
            html.Div(
                [
                    html.Label("Admin token (if configured)"),
                    dcc.Input(id="admin-token", type="password", placeholder="optional", style={"width": "100%"}),
                ],
                className="field",
                style={"maxWidth": "28rem", "marginBottom": "0.75rem"},
            ),
            html.Label("CSV text (header row required)"),
            dcc.Textarea(
                id="admin-csv",
                style={"width": "100%", "height": "160px", "fontFamily": "ui-monospace, monospace"},
                placeholder="AEnd_NE,ZEnd_NE,Capacity,InUti,OutUti,Interface_Type\nPE-A,CORE-1,100000,0.4,0.35,LAG_PARENT",
            ),
            html.Button(
                "Publish & promote",
                id="admin-publish",
                n_clicks=0,
                className="primary-btn",
                style={"marginTop": "0.75rem"},
            ),
            html.Div(id="admin-result", style={"marginTop": "1rem"}),
            html.H3("Recent publish audit"),
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("At"),
                                html.Th("Dataset"),
                                html.Th("Generation"),
                                html.Th("Status"),
                                html.Th("acc/rej"),
                            ]
                        )
                    ),
                    html.Tbody(audit_rows or [html.Tr([html.Td("No events", colSpan=5)])]),
                ],
                className="data-table",
            ),
            html.H3("Live topology jobs (registry)"),
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [html.Th("Job"), html.Th("State"), html.Th("Validation pending"), html.Th("Error")]
                        )
                    ),
                    html.Tbody(job_rows or [html.Tr([html.Td("No jobs", colSpan=4)])]),
                ],
                className="data-table",
            ),
        ],
        className="panel",
    )


def register_admin(app: Dash, config: ApplicationConfig) -> None:
    @app.callback(
        Output("admin-result", "children"),
        Input("admin-publish", "n_clicks"),
        State("admin-dataset", "value"),
        State("admin-csv", "value"),
        State("admin-token", "value"),
        prevent_initial_call=True,
    )
    def _publish(n_clicks, dataset, csv_text, token):
        if not n_clicks:
            return ""
        if config.admin_publish_token:
            if not token or str(token) != config.admin_publish_token:
                return html.P("Admin token required or invalid.", className="error")
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
                _audit(config).append(
                    audit_event(
                        actor="admin-ui",
                        dataset=name,
                        generation_id=ref.generation_id,
                        status=ref.manifest.status.value,
                        accepted=ref.manifest.accepted_count,
                        rejected=ref.manifest.rejected_count,
                        source="paste",
                    )
                )
        except WriteLockTimeout:
            return html.P("Another publish is in progress; try again shortly.", className="error")
        except Exception as exc:  # noqa: BLE001
            return html.P(f"Publish failed: {exc}", className="error")

        return html.P(
            f"Published {name} generation {ref.generation_id} "
            f"(status={ref.manifest.status.value}, accepted={ref.manifest.accepted_count}, "
            f"rejected={ref.manifest.rejected_count})."
        )
