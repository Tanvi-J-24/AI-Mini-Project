"""Road-network graph shared by every search algorithm.

Nodes are intersections identified by unique strings. Edges are undirected road
segments with a non-negative travel cost and a simulated risk score.

Cost model (kilometre-equivalent units):
    edge_cost = travel_cost + risk_weight * risk_score

The heuristic is the straight-line (haversine) distance in km. Every edge's
``travel_cost`` is built as ``distance * multiplier`` with multiplier >= 1, so
the heuristic never over-estimates the true cost -> it is admissible (and also
consistent, by the triangle inequality). Adding a non-negative risk term can only
increase edge costs, so admissibility is preserved in risk-aware mode too.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Iterator

EdgeKey = tuple[str, str]


def edge_key(u: str, v: str) -> EdgeKey:
    """Canonical (sorted) key for an undirected edge."""
    return (u, v) if u <= v else (v, u)


def edge_id(u: str, v: str) -> str:
    a, b = edge_key(u, v)
    return f"{a}-{b}"


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class Edge:
    u: str
    v: str
    travel_cost: float
    risk: float = 0.0


@dataclass
class SearchResult:
    algorithm: str
    success: bool
    path: list[str] = field(default_factory=list)
    cost: float = 0.0  # total cost under the requested cost model
    nodes_explored: int = 0
    execution_time_ms: float = 0.0
    explored: list[str] = field(default_factory=list)
    message: str = ""


class Graph:
    def __init__(self, nodes: dict[str, tuple[float, float]], edges: Iterable[Edge]):
        self.nodes = dict(nodes)
        self.edges: dict[EdgeKey, Edge] = {}
        self.adj: dict[str, list[str]] = {n: [] for n in self.nodes}
        for e in edges:
            if e.u not in self.nodes or e.v not in self.nodes:
                raise ValueError(f"Edge references unknown node: {e.u}-{e.v}")
            if e.travel_cost < 0 or e.risk < 0:
                raise ValueError("Edge costs and risks must be non-negative")
            key = edge_key(e.u, e.v)
            if key in self.edges:
                raise ValueError(f"Duplicate edge {key}")
            self.edges[key] = e
            self.adj[e.u].append(e.v)
            self.adj[e.v].append(e.u)

    # -- queries ---------------------------------------------------------
    def has_node(self, n: str) -> bool:
        return n in self.nodes

    def has_edge(self, u: str, v: str) -> bool:
        return edge_key(u, v) in self.edges

    def edge(self, u: str, v: str) -> Edge:
        return self.edges[edge_key(u, v)]

    def edge_cost(self, u: str, v: str, risk_weight: float = 0.0) -> float:
        e = self.edge(u, v)
        return e.travel_cost + risk_weight * e.risk

    def neighbors(
        self, node: str, blocked: "frozenset[EdgeKey] | set[EdgeKey]", risk_weight: float = 0.0
    ) -> Iterator[tuple[str, float]]:
        """Yield (neighbor, cost) pairs, skipping blocked edges."""
        for nb in self.adj[node]:
            if edge_key(node, nb) in blocked:
                continue
            yield nb, self.edge_cost(node, nb, risk_weight)

    def heuristic(self, a: str, b: str) -> float:
        la, ga = self.nodes[a]
        lb, gb = self.nodes[b]
        return haversine_km(la, ga, lb, gb)

    # -- path helpers ------------------------------------------------------
    def path_cost(self, path: list[str], risk_weight: float = 0.0) -> float:
        return sum(self.edge_cost(a, b, risk_weight) for a, b in zip(path, path[1:]))

    def path_travel_cost(self, path: list[str]) -> float:
        return self.path_cost(path, 0.0)

    def path_risk(self, path: list[str]) -> float:
        return sum(self.edge(a, b).risk for a, b in zip(path, path[1:]))

    def heuristic_is_admissible(self) -> bool:
        """Every edge must cost at least the straight-line distance between its ends."""
        return all(e.travel_cost + 1e-9 >= self.heuristic(e.u, e.v) for e in self.edges.values())

    def reachable(self, start: str, blocked: "frozenset[EdgeKey] | set[EdgeKey]") -> set[str]:
        seen = {start}
        stack = [start]
        while stack:
            u = stack.pop()
            for nb, _ in self.neighbors(u, blocked):
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        return seen


def validate_endpoints(graph: Graph, start: str, goal: str) -> None:
    if not graph.has_node(start):
        raise ValueError(f"Unknown source node: {start!r}")
    if not graph.has_node(goal):
        raise ValueError(f"Unknown destination node: {goal!r}")


def reconstruct(parent: dict[str, str], start: str, goal: str) -> list[str]:
    path = [goal]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return path
