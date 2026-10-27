"""Pure routing computations (no shared state): single route, comparison, risk comparison."""
from __future__ import annotations

import statistics
from typing import Iterable

from ..algorithms import ALGORITHMS, ALGORITHM_LABELS, Graph, SearchResult, edge_id, edge_key
from ..algorithms.graph import EdgeKey

# Simulation assumption used only for the displayed time estimate.
ASSUMED_SPEED_KMH = 40.0
COST_TOLERANCE = 1e-6


def result_to_dict(graph: Graph, res: SearchResult, source: str, destination: str,
                   risk_weight: float) -> dict:
    path = res.path
    travel = graph.path_travel_cost(path) if res.success else 0.0
    return {
        "algorithm": res.algorithm,
        "algorithm_label": ALGORITHM_LABELS[res.algorithm],
        "source": source,
        "destination": destination,
        "success": res.success,
        "path": path,
        "path_edges": [edge_id(a, b) for a, b in zip(path, path[1:])],
        "cost": round(res.cost, 4),
        "travel_cost": round(travel, 4),
        "risk_total": round(graph.path_risk(path), 4) if res.success else 0.0,
        "risk_weight": risk_weight,
        "segments": max(len(path) - 1, 0),
        "nodes_explored": res.nodes_explored,
        "explored": res.explored,
        "execution_time_ms": round(res.execution_time_ms, 4),
        # Simulation estimate: travel cost (km-equivalent) at an assumed constant speed.
        "estimated_minutes": round(travel / ASSUMED_SPEED_KMH * 60, 1) if res.success else None,
        "message": res.message if res.success else "No safe route available",
    }


def run_route(graph: Graph, blocked: Iterable[EdgeKey], source: str, destination: str,
              algorithm: str = "astar", risk_weight: float = 0.0) -> dict:
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm: {algorithm!r}")
    blocked_set = frozenset(blocked)
    res = ALGORITHMS[algorithm](graph, source, destination, blocked_set, risk_weight)
    return result_to_dict(graph, res, source, destination, risk_weight)


def compare_algorithms(graph: Graph, blocked: Iterable[EdgeKey], source: str, destination: str,
                       risk_weight: float = 0.0, repeats: int = 25) -> dict:
    """Run BFS, Greedy and A* on identical inputs.

    Cost and nodes explored are deterministic. Execution time is the MEDIAN of
    `repeats` runs with a monotonic high-resolution timer; on a graph this small the
    differences are dominated by measurement noise.
    """
    blocked_set = frozenset(blocked)
    rows: list[dict] = []
    for key in ("bfs", "greedy", "astar"):
        fn = ALGORITHMS[key]
        times: list[float] = []
        first: SearchResult | None = None
        for _ in range(repeats):
            r = fn(graph, source, destination, blocked_set, risk_weight)
            times.append(r.execution_time_ms)
            first = first or r
        assert first is not None
        d = result_to_dict(graph, first, source, destination, risk_weight)
        d["execution_time_ms"] = round(statistics.median(times), 4)
        d["timing_runs"] = repeats
        rows.append(d)

    astar_row = next(r for r in rows if r["algorithm"] == "astar")
    optimal_cost = astar_row["cost"] if astar_row["success"] else None
    for r in rows:
        if optimal_cost is None:
            r["is_optimal"] = None  # nothing to compare against: no route exists
        else:
            r["is_optimal"] = bool(r["success"] and r["cost"] <= optimal_cost + COST_TOLERANCE)
    return {"optimal_cost": optimal_cost, "results": rows}


def risk_compare(graph: Graph, blocked: Iterable[EdgeKey], source: str, destination: str,
                 risk_weight: float) -> dict:
    """Shortest-cost route (risk_weight=0) versus risk-aware route (risk_weight>0), both via A*."""
    shortest = run_route(graph, blocked, source, destination, "astar", 0.0)
    aware = run_route(graph, blocked, source, destination, "astar", risk_weight)
    return {"shortest": shortest, "risk_aware": aware, "risk_weight": risk_weight,
            "note": "Risk scores are simulated values, not real-world hazard measurements."}
