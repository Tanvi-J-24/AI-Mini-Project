# Architecture

## Layers

| Layer | Module | Responsibility |
|---|---|---|
| Algorithms | `backend/app/algorithms/` | Pure functions over a `Graph`: A\*, BFS, Greedy. No shared state. |
| Scenario data | `backend/app/data/scenarios.py` | Road topology, stations, per-scenario blockages/incidents, seeded grid generator (also used by the experiment script). |
| Services | `routing_service.py` | Stateless route / comparison / risk-comparison computations. |
| | `priority_engine.py` | Forward-chaining rules for incident priority. |
| | `simulation_service.py` | The only mutable state (blocked edges, incidents, active route, metrics, event log) behind an `RLock`. |
| API | `api/routes.py`, `models/schemas.py`, `main.py` | Pydantic validation, error mapping (400 invalid input, 404 unknown id, 409 conflicting state, 422 schema), CORS. |
| Frontend | `frontend/src/` | `services/api.ts` is the single network module; `hooks/useRescue.ts` holds UI state and actions. |

## Design decisions

- **Topology vs. metadata:** the immutable `Graph` (nodes, edges, costs, risk) is separate from mutable incident and blockage state. Blockages are passed to the algorithms as a set of canonical edge keys, so the graph can never be corrupted by an invalid edit; `block-road` validates that the edge exists.
- **Single source of truth:** every mutation returns a full state snapshot with a monotonically increasing `version`. The client ignores snapshots older than the one it shows and ignores local results of superseded requests.
- **Metrics are measured:** each executed search appends a record (algorithm, success, cost, nodes explored, time). Dashboard charts are aggregated from those records only.
- **Replanning:** `block_road` checks whether the blocked edge is in the active route's `path_edges`; if so it re-runs A\* with the same endpoints and risk weight, keeps `previous_path`, and logs the change. `unblock_road` retries automatically if the active route had failed.
- **Safety net:** `state()` re-validates the active route against the blocked set and reports `invalid` rather than a blocked route as valid.
- **Reproducibility:** scenario seeds are fixed; generated incidents use `Random(scenario_seed * 1000 + incident_number)`.

## API summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness |
| GET | `/api/scenarios`, `/api/scenarios/{id}` | list / definition (graph, incidents, stations, blocked) |
| POST | `/api/scenarios/{id}/load` | switch the live simulation to a scenario |
| GET | `/api/state` | full snapshot |
| POST | `/api/route` | run one algorithm; becomes the active route |
| POST | `/api/compare` | BFS, Greedy and A\* on identical inputs |
| POST | `/api/risk-compare` | shortest vs risk-aware route |
| POST | `/api/block-road`, `/api/unblock-road` | edit blockages (auto-replans) |
| POST | `/api/incidents`, `/api/resolve-incident` | add (optionally seeded-random) / resolve incident |
| POST | `/api/replan` | recompute the active route on the current graph |
| POST | `/api/demo` | multi-incident dispatch by priority |
| POST | `/api/reset` | restore the scenario (`clear_metrics` optional) |

See `http://127.0.0.1:8000/docs` for schemas.
