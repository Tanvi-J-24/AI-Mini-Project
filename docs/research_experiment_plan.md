# Research Experiment Plan

**Proposed title:** *Performance Evaluation of Heuristic Search Algorithms for Disaster Rescue Route Planning in Dynamic Environments*

> **Status:** this document is a plan. It contains **no experimental results**. All numbers must come from running `experiments/run_experiments.py`. Citations and related work are intentionally omitted; add only sources you have actually read.

## 1. Research problem

When roads are blocked during a disaster, a rescue planner must find a route quickly and re-find one when conditions change. Uninformed (BFS), purely heuristic (Greedy Best-First) and cost-plus-heuristic (A\*) search trade off route quality against search effort differently. How do they compare on road-like graphs of increasing size and blockage density, and when the network changes mid-operation?

## 2. Research questions

- **RQ1.** How do route cost and nodes explored differ among BFS, Greedy and A\* as map size grows?
- **RQ2.** How does blockage density affect route success rate and route cost for each algorithm?
- **RQ3.** How long does A\* take to replan after a road on its route is blocked, relative to planning from scratch?

## 3. Hypotheses to test

- **H1.** A\* returns the minimum route cost in every trial (expected from admissibility; verify empirically).
- **H2.** Greedy explores fewer nodes than A\* on average but returns a higher mean route cost.
- **H3.** BFS explores at least as many nodes as A\* on average and returns routes with equal or higher cost.
- **H4.** All algorithms achieve the same success rate (they are all complete on finite graphs); differences, if any, indicate a bug.
- **H5.** Replanning time grows with map size.

These are hypotheses, not findings; the data may refute them.

## 4. Algorithms compared

BFS, Greedy Best-First Search, A\* (implementations in `backend/app/algorithms/`, shared by the application and the experiment).

## 5. Variables

**Independent:** map size (e.g. 6×6, 10×10, 16×16 grids); blockage density (fraction of edges blocked, e.g. 0, 0.1, 0.25, 0.4); whether the network changes during routing (static vs. one edge on the A\* route blocked after the first plan).

**Dependent:** route cost; nodes explored; execution time (median of repeated runs); route success rate; replanning time.

## 6. Methodology

For each (size, density) cell, `--trials` trials. Each trial:

1. Generate a grid with seed `base_seed + size*10000 + density*100000 + k` (5% of roads removed, ~10% diagonals, travel cost = distance × U(1.0, 1.5)).
2. Block each edge independently with probability = density.
3. Draw one random (source, destination) pair.
4. Run BFS, Greedy and A\* on that same graph, blockage set and pair. Timing = median of `--repeats` runs using a monotonic ns timer.
5. Dynamic condition: block the middle edge of the A\* route and re-time A\* (`replan_time_ms`).
6. Record every attempt, including unreachable destinations (`success=False`), one CSV row per algorithm per trial.

## 7. Baseline and comparison

A\* with an admissible heuristic is the optimal-cost baseline (`optimal_cost`). For other algorithms, report `cost_ratio = cost / optimal_cost` on trials where A\* succeeded. Compare nodes explored and time paired by trial (same graph and endpoints). Use paired non-parametric tests (e.g. Wilcoxon signed-rank) and report effect sizes with confidence intervals; state the test you chose before looking at results.

## 8. Limitations and threats to validity

- Synthetic grid graphs, not real road networks; results may not transfer.
- Edge costs and risk are simulated; heuristic admissibility depends on the `≥ 1` multiplier by construction.
- Python timing of microsecond-scale runs is noisy (interpreter, GC, OS scheduling); use medians, many repeats and report variability. Absolute times are machine-specific.
- Randomly drawn endpoints include trivial pairs and unreachable pairs; report them separately.
- "Dynamic" is a single edge blockage, a simplification of real changing conditions.
- Single-threaded, single-machine measurements.

## 9. Suggested tables and charts

- Table: per (size, density, algorithm) mean ± SD of cost, nodes explored, median time, success rate.
- Table: `cost_ratio` distribution (mean, max, share of trials equal to 1.0).
- Chart: nodes explored vs. map size, one line per algorithm.
- Chart: success rate vs. blockage density.
- Chart: box plot of replanning time by map size.
- Clearly label **prototype demonstration results** (single runs in the web app) separately from **repeated experimental results** (CSV from this script).

## 10. Reproducibility

```bash
# from the repository root, with the venv active and requirements installed
python experiments/run_experiments.py --trials 30 --out experiments/results/run1.csv
```

Defaults: sizes `6 10 16`, densities `0 0.1 0.25 0.4`, `--base-seed 12345`, `--repeats 15`. The same arguments reproduce the same graphs, blockages and endpoints; timing columns will vary slightly. Record the Python version, OS, CPU and the git commit with your results.

CSV columns: `trial, seed, map_size, blockage_density, dynamic, source, destination, algorithm, success, cost, optimal_cost, cost_ratio, segments, nodes_explored, time_ms_median, timing_repeats, replan_time_ms`.
