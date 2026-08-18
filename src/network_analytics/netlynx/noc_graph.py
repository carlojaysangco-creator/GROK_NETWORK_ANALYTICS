"""Build a simple affected-link adjacency graph for NOC cases."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from network_analytics.data_platform import GenerationStore

from .cases import detect_cases
from .cohort import load_observations
from .future_contracts import TopologyCase


@dataclass(frozen=True, slots=True)
class NocGraphView:
    case: TopologyCase
    node_count: int
    edge_count: int
    edges: tuple[tuple[str, str, str], ...]  # a, z, link_id


def graph_for_case(store: GenerationStore, case_id: str) -> NocGraphView | None:
    cases = {c.case_id: c for c in detect_cases(store)}
    case = cases.get(case_id)
    if case is None:
        return None
    observations = {o.link_id: o for o in load_observations(store)}
    g = nx.Graph()
    edge_list: list[tuple[str, str, str]] = []
    for link_id in case.affected_link_ids:
        obs = observations.get(link_id)
        if obs is None or not obs.a_end or not obs.z_end:
            continue
        g.add_edge(obs.a_end, obs.z_end, link_id=link_id)
        edge_list.append((obs.a_end, obs.z_end, link_id))
    return NocGraphView(
        case=case,
        node_count=g.number_of_nodes(),
        edge_count=g.number_of_edges(),
        edges=tuple(edge_list),
    )


def summarize_all_case_graphs(store: GenerationStore) -> tuple[NocGraphView, ...]:
    out: list[NocGraphView] = []
    for case in detect_cases(store):
        view = graph_for_case(store, case.case_id)
        if view is not None:
            out.append(view)
    return tuple(out)
