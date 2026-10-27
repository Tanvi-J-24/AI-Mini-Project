"""Greedy Best-First Search: expands the node with the smallest h(n) only.

It ignores the cost already paid, so it is fast but NOT guaranteed to be optimal.
"""
from __future__ import annotations

import heapq
import itertools
import time

from .graph import EdgeKey, Graph, SearchResult, reconstruct, validate_endpoints


def greedy_best_first(
    graph: Graph,
    start: str,
    goal: str,
    blocked: "frozenset[EdgeKey] | set[EdgeKey]" = frozenset(),
    risk_weight: float = 0.0,
) -> SearchResult:
    validate_endpoints(graph, start, goal)
    t0 = time.perf_counter_ns()

    counter = itertools.count()
    heap: list[tuple[float, int, str]] = [(graph.heuristic(start, goal), next(counter), start)]
    seen = {start}  # nodes ever pushed; each node is pushed once, so no loops
    parent: dict[str, str] = {}
    explored: list[str] = []
    path: list[str] | None = None

    while heap:
        _, _, u = heapq.heappop(heap)
        explored.append(u)
        if u == goal:
            path = reconstruct(parent, start, goal)
            break
        for v, _ in graph.neighbors(u, blocked, risk_weight):
            if v not in seen:
                seen.add(v)
                parent[v] = u
                heapq.heappush(heap, (graph.heuristic(v, goal), next(counter), v))

    elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
    if path is None:
        return SearchResult("greedy", False, [], 0.0, len(explored), elapsed_ms, explored,
                            "No safe route available")
    return SearchResult("greedy", True, path, graph.path_cost(path, risk_weight), len(explored),
                        elapsed_ms, explored, "Route found (not guaranteed optimal)")
