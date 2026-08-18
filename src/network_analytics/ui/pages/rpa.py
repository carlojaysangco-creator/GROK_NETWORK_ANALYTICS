"""Route Path Analysis page – native engine, offline demo graph."""

from __future__ import annotations

from dash import Dash, Input, Output, State, dcc, html
import dash

from network_analytics.route_path_analysis import (
    RoutePair,
    RouteRequest,
    TransportFrequency,
    analyze,
)
from network_analytics.route_path_analysis.demo_graph import build_demo_graph, demo_nodes
from network_analytics.shared.config import ApplicationConfig


def rpa_layout(_config: ApplicationConfig) -> html.Div:
    nodes = list(demo_nodes())
    return html.Div(
        [
            html.H2("Route Path Analysis"),
            html.P(
                "Native path engine on a synthetic offline topology. "
                "Equal-cost defaults are canonical; alternates are display-only.",
                className="muted",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Source"),
                            dcc.Dropdown(
                                id="rpa-source",
                                options=[{"label": n, "value": n} for n in nodes],
                                value="PE-A",
                                clearable=False,
                            ),
                        ],
                        className="field",
                    ),
                    html.Div(
                        [
                            html.Label("Destination"),
                            dcc.Dropdown(
                                id="rpa-destination",
                                options=[{"label": n, "value": n} for n in nodes],
                                value="BNG-X",
                                clearable=False,
                            ),
                        ],
                        className="field",
                    ),
                    html.Div(
                        [
                            html.Label("Alternate branches"),
                            dcc.Input(
                                id="rpa-alternates",
                                type="number",
                                min=0,
                                max=10,
                                step=1,
                                value=2,
                            ),
                        ],
                        className="field",
                    ),
                    html.Button("Analyze", id="rpa-run", n_clicks=0, className="primary-btn"),
                ],
                className="rpa-controls",
            ),
            html.Div(id="rpa-results", className="rpa-results"),
        ],
        className="panel",
    )


def register_rpa(app: Dash, _config: ApplicationConfig) -> None:
    @app.callback(
        Output("rpa-results", "children"),
        Input("rpa-run", "n_clicks"),
        State("rpa-source", "value"),
        State("rpa-destination", "value"),
        State("rpa-alternates", "value"),
        prevent_initial_call=False,
    )
    def _run(n_clicks, source, destination, alternates):
        if not source or not destination:
            return html.P("Select source and destination.", className="muted")
        try:
            alt = int(alternates if alternates is not None else 2)
        except (TypeError, ValueError):
            return html.P("Alternate branches must be an integer 0–10.", className="error")

        graph = build_demo_graph()
        request = RouteRequest(
            pairs=(RoutePair(str(source), str(destination), 0.0),),
            frequency=TransportFrequency.WEEKLY,
            alternate_branches=max(0, min(10, alt)),
        )
        try:
            result = analyze(graph, request)
        except ValueError as exc:
            return html.P(str(exc), className="error")

        pair = result.pairs[0]
        cards = []
        if pair.min_weight is None:
            cards.append(html.P("No path found.", className="error"))
        else:
            cards.append(
                html.P(
                    f"Minimum weight: {pair.min_weight:g} · "
                    f"Defaults: {sum(1 for p in pair.paths if p.path_class.value == 'Default')} · "
                    f"Alternates: {sum(1 for p in pair.paths if p.path_class.value == 'Alternate')}"
                )
            )
        for path in pair.paths:
            hop_text = " → ".join(path.nodes)
            util = path.maximum_utilization_pct
            cap = path.bottleneck_capacity_mbps
            meta = []
            if cap is not None:
                meta.append(f"bottleneck {cap:g} Mbps")
            if util is not None:
                meta.append(f"max util {util:g}%")
            cards.append(
                html.Div(
                    [
                        html.Strong(f"#{path.order} {path.path_class.value} (weight {path.weight:g})"),
                        html.Div(hop_text, className="path-nodes"),
                        html.Div(" · ".join(meta), className="muted") if meta else None,
                    ],
                    className="path-card",
                )
            )
        for w in pair.warnings:
            cards.append(html.P(w, className="muted"))
        return html.Div(cards)
