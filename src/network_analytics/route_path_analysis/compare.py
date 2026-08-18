"""Weekly vs Daily compare – dual graph analysis, no silent fallback."""

from __future__ import annotations

from dataclasses import dataclass

from network_analytics.data_platform import GenerationStore

from .contracts import AnalysisResult, RoutePair, RouteRequest, TransportFrequency
from .daily import DailyUnavailable, resolve_daily_graph, resolve_weekly_graph
from .service import analyze


@dataclass(frozen=True, slots=True)
class CompareResult:
    source: str
    destination: str
    weekly: AnalysisResult | None
    daily: AnalysisResult | None
    weekly_generation_id: str | None
    daily_generation_id: str | None
    warnings: tuple[str, ...] = ()


def compare_pair(
    store: GenerationStore,
    source: str,
    destination: str,
) -> CompareResult:
    warnings: list[str] = []
    weekly_result = None
    weekly_gen = None
    weekly = resolve_weekly_graph(store)
    if weekly is None:
        warnings.append("No promoted weekly topology.")
    else:
        weekly_gen = weekly.generation_id
        weekly_result = analyze(
            weekly.graph,
            RouteRequest(
                pairs=(RoutePair(source, destination, 0.0),),
                frequency=TransportFrequency.WEEKLY,
                alternate_branches=0,
            ),
        )

    daily_result = None
    daily_gen = None
    try:
        daily = resolve_daily_graph(store)
        daily_gen = daily.generation_id
        daily_result = analyze(
            daily.graph,
            RouteRequest(
                pairs=(RoutePair(source, destination, 0.0),),
                frequency=TransportFrequency.DAILY,
                alternate_branches=0,
            ),
        )
    except DailyUnavailable as exc:
        warnings.append(str(exc))

    return CompareResult(
        source=source.strip().upper(),
        destination=destination.strip().upper(),
        weekly=weekly_result,
        daily=daily_result,
        weekly_generation_id=weekly_gen,
        daily_generation_id=daily_gen,
        warnings=tuple(warnings),
    )
