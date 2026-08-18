"""Loopback-only Dash application for GROK Network Analytics."""

from __future__ import annotations

from pathlib import Path

from dash import Dash, Input, Output, dcc, html
from flask import jsonify

from network_analytics.shared.config import ApplicationConfig
from network_analytics.ui.pages import (
    admin_layout,
    data_layout,
    netlynx_layout,
    register_admin,
    register_rpa,
    rpa_layout,
)


_NAVIGATION = (
    ("overview", "Overview", "/"),
    ("rpa", "Route Path Analysis", "/route-path-analysis"),
    ("netlynx", "NetLynx", "/netlynx"),
    ("data", "Data", "/data"),
    ("admin", "Admin", "/admin"),
)


def _navigation() -> html.Nav:
    return html.Nav(
        [
            dcc.Link(label, href=href, id=f"nav-{key}", className="nav-link")
            for key, label, href in _NAVIGATION
        ],
        className="primary-nav",
        **{"aria-label": "Primary navigation"},
    )


def _status_banner(config: ApplicationConfig) -> html.Div:
    collection = "enabled" if config.collection_enabled else "disabled"
    live = "enabled" if config.live_topology_enabled else "disabled"
    return html.Div(
        [
            html.Strong("Safe local mode"),
            html.Span(f"Collection {collection}"),
            html.Span(f"Live topology {live}"),
            html.Span("Admin publish is local GenerationStore only"),
        ],
        id="runtime-status",
        className="status-banner",
        role="status",
    )


def _placeholder(title: str, detail: str) -> html.Div:
    return html.Div(
        [
            html.H2(title),
            html.P(detail),
        ],
        className="panel",
    )


def _not_found() -> html.Div:
    return html.Div(
        [
            html.H2("Page not found"),
            html.P("Use the primary navigation to return to an available workspace."),
            dcc.Link("Return to Overview", href="/", className="action-link"),
        ],
        className="panel",
    )


def create_dash_app(config: ApplicationConfig) -> Dash:
    config.validate()
    assets = Path(__file__).resolve().parent / "assets"
    app = Dash(
        __name__,
        assets_folder=str(assets) if assets.is_dir() else None,
        suppress_callback_exceptions=True,
        title="Network Analytics",
    )

    app.layout = html.Div(
        [
            dcc.Location(id="url", refresh=False),
            html.Header(
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("PLDT Fixed Network", className="eyebrow"),
                                html.H1("Network Analytics"),
                                html.P(
                                    "Route intelligence and operational link analytics",
                                    className="subtitle",
                                ),
                            ],
                            className="brand-block",
                        ),
                        _navigation(),
                    ],
                    className="header-inner",
                ),
                className="app-header",
            ),
            html.Main(
                [
                    _status_banner(config),
                    html.Section(
                        id="page-content",
                        className="page-panel",
                        **{"aria-live": "polite"},
                    ),
                ],
                className="content-shell",
            ),
        ],
        className="app-shell",
    )

    @app.callback(Output("page-content", "children"), Input("url", "pathname"))
    def render_page(pathname: str | None):
        route = pathname or "/"
        if route == "/":
            return _placeholder(
                "Overview",
                "Unified workspace for Route Path Analysis and NetLynx. "
                "Use Admin to publish local CSV cohorts; Data shows generation lineage.",
            )
        if route == "/route-path-analysis":
            return rpa_layout(config)
        if route == "/netlynx":
            return netlynx_layout(config)
        if route == "/data":
            return data_layout(config)
        if route == "/admin":
            return admin_layout(config)
        return _not_found()

    @app.callback(
        *(Output(f"nav-{key}", "className") for key, _label, _href in _NAVIGATION),
        Input("url", "pathname"),
    )
    def mark_active_navigation(pathname: str | None):
        route = pathname or "/"
        return tuple(
            "nav-link nav-link-active" if href == route else "nav-link"
            for _key, _label, href in _NAVIGATION
        )

    register_rpa(app, config)
    register_admin(app, config)

    @app.server.get("/healthz")
    def healthz():
        return jsonify(
            status="ok",
            process_health="ok",
            collection_enabled=config.collection_enabled,
            live_topology_enabled=config.live_topology_enabled,
        )

    return app
