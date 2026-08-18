"""Route Path Analysis page – native engine; promoted topology preferred."""

from __future__ import annotations

from dash import Dash, Input, Output, State, dcc, html

from network_analytics.data_platform import GenerationStore
from network_analytics.route_path_analysis import (
    DailyUnavailable,
    RoutePair,
    RouteRequest,
    TransportFrequency,
    analyze,
    resolve_daily_graph,
    resolve_weekly_graph,
)
from network_analytics.route_path_analysis.demo_graph import build_demo_graph, demo_nodes
from network_analytics.shared.config import ApplicationConfig


def _store(config: ApplicationConfig) -> GenerationStore:
    return GenerationStore(config.paths.data_root / "generations")


def rpa_layout(config: ApplicationConfig) -> html.Div:
    store = _store(config)
    weekly = resolve_weekly_graph(store)
    if weekly is not None:
        nodes = sorted(weekly.graph.nodes)
        source_label = f"Promoted topology ({weekly.generation_id})"
    else:
        nodes = list(demo_nodes())
        source_label = "Synthetic demo graph (no promoted rpa_topology generation)"

    return html.Div(
        [
            html.H2("Route Path Analysis"),
            html.P(
                "Native path engine. Equal-cost defaults are canonical; alternates are display-only. "
                "Daily never falls back to Weekly.",
                className="muted",
            ),
            html.P(f"Topology source: {source_label}", className="muted"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Frequency"),
                            dcc.Dropdown(
                                id="rpa-frequency",
                                options=[
                                    {"label": "Weekly", "value": "weekly"},
                                    {"label": "Daily", "value": "daily"},
                                ],
                                value="weekly",
                                clearable=False,
                            ),
                        ],
                        className="field",
                    ),
                    html.Div(
                        [
                            html.Label("Source"),
                            dcc.Dropdown(
                                id="rpa-source",
                                options=[{"label": n, "value": n} for n in nodes],
                                value=nodes[0] if nodes else None,
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
                                value=nodes[-1] if nodes else None,
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
                    html.Div(
                        [
                            html.Label("Additional BW (Mbps)"),
                            dcc.Input(
                                id="rpa-bw",
                                type="number",
                                step=1,
                                value=0,
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


def register_rpa(app: Dash, config: ApplicationConfig) -> None:
    @app.callback(
        Output("rpa-results", "children"),
        Input("rpa-run", "n_clicks"),
        State("rpa-frequency", "value"),
        State("rpa-source", "value"),
        State("rpa-destination", "value"),
        State("rpa-alternates", "value"),
        State("rpa-bw", "value"),
        prevent_initial_call=False,
    )
    def _run(_n, frequency, source, destination, alternates, bw):
        if not source or not destination:
            return html.P("Select source and destination.", className="muted")

        freq = TransportFrequency.WEEKLY
        try:
            freq = TransportFrequency(str(frequency or "weekly").lower())
        except ValueError:
            return html.P("Invalid frequency.", className="error")

        try:
            alt = int(alternates if alternates is not None else 2)
        except (TypeError, ValueError):
            return html.P("Alternate branches must be an integer 0–10.", className="error")
        try:
            additional = float(bw if bw is not None else 0)
        except (TypeError, ValueError):
            return html.P("Additional BW must be numeric.", className="error")

        store = _store(config)
        try:
            if freq is TransportFrequency.DAILY:
                topo = resolve_daily_graph(store)
                alt = 0
                additional = 0.0
            else:
                weekly = resolve_weekly_graph(store)
                if weekly is not None:
                    topo_graph = weekly.graph
                    source_note = f"Using promoted topology {weekly.generation_id}"
                else:
                    topo_graph = build_demo_graph()
                    source_note = "Using synthetic demo graph"
                class _T:
                    graph = topo_graph
                topo = _T()
        except DailyUnavailable as exc:
            return html.P(str(exc), className="error")

        request = RouteRequest(
            pairs=(RoutePair(str(source), str(destination), additional),),
            frequency=freq,
            alternate_branches=max(0, min(10, alt)),
        )
        try:
            result = analyze(topo.graph, request)
        except ValueError as exc:
            return html.P(str(exc), className="error")

        pair = result.pairs[0]
        cards = []
        if freq is TransportFrequency.WEEKLY:
            cards.append(html.P(source_note, className="muted"))
        if pair.min_weight is None:
            cards.append(html.P("No path found.", className="error"))
        else:
            cards.append(
                html.P(
                    f"Minimum weight: {pair.min_weight:g} · "
                    f"Defaults: {sum(1 for p in pair.paths if p.path_class.value == 'Default')} · "
                    f"Alternates: {sum(1 for p in pair.paths if p.path_class.value == 'Alternate')} · "
                    f"Additional BW: {pair.additional_bw_mbps:g} Mbps"
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
