"""Route Path Analysis – P2P, FTTH, Compare + Pyvis path artifacts."""

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
from network_analytics.route_path_analysis.compare import compare_pair
from network_analytics.route_path_analysis.demo_graph import build_demo_graph, demo_nodes
from network_analytics.route_path_analysis.ftth_analysis import analyze_ftth_access
from network_analytics.route_path_analysis.history import append_run
from network_analytics.route_path_analysis.viz import write_path_artifact
from network_analytics.shared.config import ApplicationConfig


def _store(config: ApplicationConfig) -> GenerationStore:
    return GenerationStore(config.paths.data_root / "generations")


def _path_cards(pair, graph, config: ApplicationConfig) -> list:
    cards = []
    if pair.min_weight is None:
        cards.append(html.P("No path found.", className="error"))
        return cards
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
        meta = []
        if path.bottleneck_capacity_mbps is not None:
            meta.append(f"bottleneck {path.bottleneck_capacity_mbps:g} Mbps")
        if path.maximum_utilization_pct is not None:
            meta.append(f"max util {path.maximum_utilization_pct:g}%")
        if path.minimum_remaining_mbps is not None:
            meta.append(f"min remaining {path.minimum_remaining_mbps:g} Mbps")

        viz_link = None
        if path.nodes:
            try:
                out = write_path_artifact(
                    graph,
                    path,
                    config.paths.artifact_root / "rpa",
                    run_prefix=f"{pair.source}_{pair.destination}",
                )
                rel = out.relative_to(config.paths.artifact_root.resolve()).as_posix()
                viz_link = html.A(
                    "Open topology view",
                    href=f"/artifacts/{rel}",
                    target="_blank",
                    className="action-link",
                )
            except Exception as exc:  # noqa: BLE001
                viz_link = html.Span(f"Topology view unavailable: {exc}", className="muted")

        cards.append(
            html.Div(
                [
                    html.Strong(f"#{path.order} {path.path_class.value} (weight {path.weight:g})"),
                    html.Div(hop_text, className="path-nodes"),
                    html.Div(" · ".join(meta), className="muted") if meta else None,
                    html.Div(viz_link, style={"marginTop": "0.35rem"}) if viz_link else None,
                ],
                className="path-card",
            )
        )
    for w in pair.warnings:
        cards.append(html.P(w, className="muted"))
    return cards


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
                "Native engine + Pyvis path topology artifacts. Daily never falls back to Weekly.",
                className="muted",
            ),
            html.P(f"Topology source: {source_label}", className="muted"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Mode"),
                            dcc.Dropdown(
                                id="rpa-mode",
                                options=[
                                    {"label": "Point to point", "value": "ptp"},
                                    {"label": "FTTH Access NE", "value": "ftth"},
                                    {"label": "Compare Weekly/Daily", "value": "compare"},
                                ],
                                value="ptp",
                                clearable=False,
                            ),
                        ],
                        className="field",
                    ),
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
                            html.Label("Source / Access NE"),
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
                            dcc.Input(id="rpa-alternates", type="number", min=0, max=10, step=1, value=2),
                        ],
                        className="field",
                    ),
                    html.Div(
                        [
                            html.Label("Additional BW (Mbps)"),
                            dcc.Input(id="rpa-bw", type="number", step=1, value=0),
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
        State("rpa-mode", "value"),
        State("rpa-frequency", "value"),
        State("rpa-source", "value"),
        State("rpa-destination", "value"),
        State("rpa-alternates", "value"),
        State("rpa-bw", "value"),
        prevent_initial_call=False,
    )
    def _run(_n, mode, frequency, source, destination, alternates, bw):
        if not source:
            return html.P("Select source / Access NE.", className="muted")
        try:
            alt = int(alternates if alternates is not None else 2)
            additional = float(bw if bw is not None else 0)
        except (TypeError, ValueError):
            return html.P("Alternates must be int 0–10; BW must be numeric.", className="error")

        store = _store(config)

        if mode == "compare":
            if not destination:
                return html.P("Select destination for Compare.", className="muted")
            cmp = compare_pair(store, str(source), str(destination))
            blocks = [html.P(w, className="muted") for w in cmp.warnings]
            weekly_graph = None
            daily_graph = None
            try:
                w = resolve_weekly_graph(store)
                weekly_graph = w.graph if w else None
            except Exception:
                pass
            try:
                d = resolve_daily_graph(store)
                daily_graph = d.graph
            except DailyUnavailable:
                pass
            if cmp.weekly is not None and weekly_graph is not None:
                blocks.append(html.H3(f"Weekly ({cmp.weekly_generation_id})"))
                blocks.extend(_path_cards(cmp.weekly.pairs[0], weekly_graph, config))
            if cmp.daily is not None and daily_graph is not None:
                blocks.append(html.H3(f"Daily ({cmp.daily_generation_id})"))
                blocks.extend(_path_cards(cmp.daily.pairs[0], daily_graph, config))
            if cmp.weekly is None and cmp.daily is None:
                blocks.append(html.P("No topology available for Compare.", className="error"))
            return html.Div(blocks)

        freq = TransportFrequency.WEEKLY
        try:
            freq = TransportFrequency(str(frequency or "weekly").lower())
        except ValueError:
            return html.P("Invalid frequency.", className="error")

        try:
            if freq is TransportFrequency.DAILY:
                topo = resolve_daily_graph(store)
                graph = topo.graph
                source_note = f"Daily topology {topo.generation_id}"
                gen_id = topo.generation_id
                alt = 0
                additional = 0.0
            else:
                weekly = resolve_weekly_graph(store)
                if weekly is not None:
                    graph = weekly.graph
                    source_note = f"Using promoted topology {weekly.generation_id}"
                    gen_id = weekly.generation_id
                else:
                    graph = build_demo_graph()
                    source_note = "Using synthetic demo graph"
                    gen_id = None
        except DailyUnavailable as exc:
            return html.P(str(exc), className="error")

        if mode == "ftth":
            result = analyze_ftth_access(
                graph,
                store,
                str(source),
                alternate_branches=max(0, min(10, alt)),
                additional_bw_mbps=additional,
            )
            blocks = [html.P(source_note, className="muted")]
            blocks.append(
                html.P(f"Access NE {result.access_ne} → Homing BNGs: {', '.join(result.homing_bngs) or '—'}")
            )
            for w in result.warnings:
                blocks.append(html.P(w, className="muted"))
            for bng, analysis in result.per_bng:
                blocks.append(html.H3(f"To {bng}"))
                blocks.extend(_path_cards(analysis.pairs[0], graph, config))
            return html.Div(blocks)

        if not destination:
            return html.P("Select destination.", className="muted")

        request = RouteRequest(
            pairs=(RoutePair(str(source), str(destination), additional),),
            frequency=freq,
            alternate_branches=max(0, min(10, alt)),
        )
        try:
            result = analyze(graph, request)
        except ValueError as exc:
            return html.P(str(exc), className="error")

        try:
            append_run(config.paths.data_root / "history", result, topology_generation_id=gen_id)
        except Exception:
            pass

        cards = [html.P(source_note, className="muted")]
        cards.extend(_path_cards(result.pairs[0], graph, config))
        return html.Div(cards)
