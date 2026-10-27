"""Breadth-First Search.

BFS explores level by level, so it minimises the NUMBER OF EDGES (road segments),
not total travel cost. When edge weights differ, the BFS route may be more
expensive than the A* route.
"""
from __future__ import annotations

import time
from collections import deque

from .graph import EdgeKey, Graph, SearchResult, reconstruct, validate_endpoints


def bfs(
    graph: Graph,
    start: str,
    goal: str,
    blocked: "frozenset[EdgeKey] | set[EdgeKey]" = frozenset(),
    risk_weight: float = 0.0,
) -> SearchResult:
    validate_endpoints(graph, start, goal)
    t0 = time.perf_counter_ns()

    queue: deque[str] = deque([start])
    visited = {start}
    parent: dict[str, str] = {}
    explored: list[str] = []
    path: list[str] | None = None

    while queue:
        u = queue.popleft()
        explored.append(u)
        if u == goal:
            path = reconstruct(parent, start, goal)
            break
        for v, _ in graph.neighbors(u, blocked, risk_weight):
            if v not in visited:
                visited.add(v)
                parent[v] = u
                queue.append(v)

    elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
    if path is None:
        return SearchResult("bfs", False, [], 0.0, len(explored), elapsed_ms, explored,
                            "No safe route available")
    return SearchResult("bfs", True, path, graph.path_cost(path, risk_weight), len(explored),
                        elapsed_ms, explored, "Route found (fewest segments)")
