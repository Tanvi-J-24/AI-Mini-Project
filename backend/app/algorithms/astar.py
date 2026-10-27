"""A* search: f(n) = g(n) + h(n)."""
from __future__ import annotations

import heapq
import itertools
import time

from .graph import EdgeKey, Graph, SearchResult, reconstruct, validate_endpoints


def astar(
    graph: Graph,
    start: str,
    goal: str,
    blocked: "frozenset[EdgeKey] | set[EdgeKey]" = frozenset(),
    risk_weight: float = 0.0,
) -> SearchResult:
    validate_endpoints(graph, start, goal)
    t0 = time.perf_counter_ns()

    counter = itertools.count()  # tie-breaker so the heap never compares nodes
    g_cost: dict[str, float] = {start: 0.0}
    parent: dict[str, str] = {}
    closed: set[str] = set()
    explored: list[str] = []
    heap: list[tuple[float, int, str]] = [(graph.heuristic(start, goal), next(counter), start)]
    path: list[str] | None = None

    while heap:
        _, _, u = heapq.heappop(heap)
        if u in closed:
            continue  # stale heap entry
        closed.add(u)
        explored.append(u)
        if u == goal:
            path = reconstruct(parent, start, goal)
            break
        for v, c in graph.neighbors(u, blocked, risk_weight):
            if v in closed:
                continue
            new_g = g_cost[u] + c
            if new_g < g_cost.get(v, float("inf")) - 1e-12:
                g_cost[v] = new_g
                parent[v] = u
                heapq.heappush(heap, (new_g + graph.heuristic(v, goal), next(counter), v))

    elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
    if path is None:
        return SearchResult("astar", False, [], 0.0, len(explored), elapsed_ms, explored,
                            "No safe route available")
    return SearchResult("astar", True, path, graph.path_cost(path, risk_weight), len(explored),
                        elapsed_ms, explored, "Route found")
