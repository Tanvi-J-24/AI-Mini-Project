"""Reproducible experiment: BFS vs Greedy Best-First vs A* on generated road networks.

Usage (from the repository root, venv active):
    python experiments/run_experiments.py                 # default grid
    python experiments/run_experiments.py --trials 30 --out experiments/results/run1.csv

Every trial uses ONE graph, ONE blockage set and ONE (source, destination) pair for
all three algorithms. Randomness comes only from `random.Random(seed)` instances
derived from fixed seeds, so the same command yields the same graphs, endpoints
and blockages (execution times still vary slightly between machines/runs).

Output: one CSV row per (trial, algorithm). Unreachable destinations are recorded
with success=False; nothing is invented or filtered out.
"""
from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.algorithms import ALGORITHMS  # noqa: E402
from app.algorithms.graph import edge_key  # noqa: E402
from app.data.scenarios import generate_grid, nid  # noqa: E402

FIELDS = ["trial", "seed", "map_size", "blockage_density", "dynamic", "source", "destination",
          "algorithm", "success", "cost", "optimal_cost", "cost_ratio", "segments",
          "nodes_explored", "time_ms_median", "timing_repeats", "replan_time_ms"]


def timed(fn, graph, s, g, blocked, repeats):
    """Return (first_result, median_time_ms) using the monotonic ns timer inside the algorithms."""
    times, first = [], None
    for _ in range(repeats):
        res = fn(graph, s, g, blocked)
        times.append(res.execution_time_ms)
        first = first or res
    return first, statistics.median(times)


def run_trial(trial: int, seed: int, size: int, density: float, dynamic: bool, repeats: int):
    rng = random.Random(seed)
    graph = generate_grid(size, size, seed=seed, removal_rate=0.05, diagonal_rate=0.1)
    edges = sorted(graph.edges)
    blocked = {e for e in edges if rng.random() < density}
    nodes = sorted(graph.nodes)
    s, g = rng.sample(nodes, 2)
    rows = []
    astar_cost = None
    results = {}
    for name in ("bfs", "greedy", "astar"):
        res, med = timed(ALGORITHMS[name], graph, s, g, frozenset(blocked), repeats)
        results[name] = (res, med)
    if results["astar"][0].success:
        astar_cost = results["astar"][0].cost

    # Dynamic scenario: block one edge of the A* route, then measure A* replanning time.
    replan_ms = ""
    if dynamic and results["astar"][0].success and len(results["astar"][0].path) > 1:
        p = results["astar"][0].path
        a, b = p[len(p) // 2 - 1], p[len(p) // 2]
        new_blocked = frozenset(blocked | {edge_key(a, b)})
        _, med = timed(ALGORITHMS["astar"], graph, s, g, new_blocked, repeats)
        replan_ms = round(med, 5)

    for name in ("bfs", "greedy", "astar"):
        res, med = results[name]
        ratio = (res.cost / astar_cost) if (res.success and astar_cost) else ""
        rows.append({
            "trial": trial, "seed": seed, "map_size": f"{size}x{size}", "blockage_density": density,
            "dynamic": dynamic, "source": s, "destination": g, "algorithm": name,
            "success": res.success, "cost": round(res.cost, 5) if res.success else "",
            "optimal_cost": round(astar_cost, 5) if astar_cost is not None else "",
            "cost_ratio": round(ratio, 5) if ratio != "" else "",
            "segments": max(len(res.path) - 1, 0) if res.success else "",
            "nodes_explored": res.nodes_explored, "time_ms_median": round(med, 5),
            "timing_repeats": repeats,
            "replan_time_ms": replan_ms if name == "astar" else "",
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trials", type=int, default=20, help="trials per (size, density) cell")
    ap.add_argument("--sizes", type=int, nargs="+", default=[6, 10, 16])
    ap.add_argument("--densities", type=float, nargs="+", default=[0.0, 0.1, 0.25, 0.4])
    ap.add_argument("--repeats", type=int, default=15, help="timing repetitions per run (median kept)")
    ap.add_argument("--base-seed", type=int, default=12345)
    ap.add_argument("--out", default=str(ROOT / "experiments" / "results" / "results.csv"))
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    trial = 0
    t0 = time.perf_counter()
    for size in args.sizes:
        for density in args.densities:
            for k in range(args.trials):
                seed = args.base_seed + size * 10_000 + int(density * 1000) * 100 + k
                # dynamic=True rows measure A* replanning after blocking a route edge
                rows += run_trial(trial, seed, size, density, True, args.repeats)
                trial += 1
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    # Console summary computed from the rows just written (no hard-coded values).
    print(f"Wrote {len(rows)} rows ({trial} trials) to {out} in {time.perf_counter() - t0:.1f}s")
    for name in ("bfs", "greedy", "astar"):
        rs = [r for r in rows if r["algorithm"] == name]
        ok = [r for r in rs if r["success"]]
        print(f"{name:7s} success {len(ok)}/{len(rs)}  "
              f"mean nodes {statistics.mean(r['nodes_explored'] for r in rs):.1f}  "
              f"mean cost {statistics.mean(r['cost'] for r in ok) if ok else float('nan'):.3f}")


if __name__ == "__main__":
    main()
