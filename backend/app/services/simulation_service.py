"""Shared simulation state (the backend is the single source of truth).

All mutations go through ``SimulationService`` methods guarded by an RLock, because
FastAPI runs synchronous endpoints in a thread pool.
"""
from __future__ import annotations

import random
import threading
from collections import deque
from datetime import datetime
from typing import Any, Optional

from ..algorithms import ALGORITHMS, ALGORITHM_LABELS, Graph, edge_id, edge_key
from ..algorithms.graph import EdgeKey
from ..data.scenarios import (SCENARIOS, STATIONS, MAP_CENTER, build_graph, graph_payload)
from . import priority_engine
from .routing_service import (compare_algorithms, risk_compare, run_route)

DEFAULT_SCENARIO = "flood"
MAX_EVENTS = 200
MAX_RECORDS = 1000


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class SimulationService:
    def __init__(self, scenario_id: str = DEFAULT_SCENARIO):
        self._lock = threading.RLock()
        self._events: deque[dict] = deque(maxlen=MAX_EVENTS)
        self._records: deque[dict] = deque(maxlen=MAX_RECORDS)
        self._event_seq = 0
        self._version = 0
        self._load(scenario_id, log=False)
        self._log("info", "scenario_loaded", f"Scenario loaded: {self.scenario.name}")

    # ------------------------------------------------------------------ setup
    def _load(self, scenario_id: str, log: bool = True) -> None:
        if scenario_id not in SCENARIOS:
            raise NotFoundError(f"Unknown scenario: {scenario_id!r}")
        self.scenario = SCENARIOS[scenario_id]
        self.graph: Graph = build_graph(scenario_id)
        self.blocked: set[EdgeKey] = {edge_key(u, v) for u, v in self.scenario.blocked}
        self.incidents: dict[str, dict] = {
            i.id: {"id": i.id, "type": i.type, "severity": i.severity,
                   "people_affected": i.people_affected, "node": i.node,
                   "description": i.description, "status": "Active"}
            for i in self.scenario.incidents
        }
        self._next_incident_no = len(self.incidents) + 1
        self.active: Optional[dict] = None
        self._version += 1

    # ---------------------------------------------------------------- helpers
    def _log(self, level: str, kind: str, message: str) -> None:
        self._event_seq += 1
        self._events.appendleft({
            "id": self._event_seq,
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "level": level, "type": kind, "message": message,
        })

    def _bump(self) -> None:
        self._version += 1

    def _check_node(self, node: str, label: str = "node") -> None:
        if not self.graph.has_node(node):
            raise ValueError(f"Unknown {label}: {node!r}")

    def _record(self, r: dict, kind: str) -> None:
        self._records.append({"kind": kind, "algorithm": r["algorithm"], "success": r["success"],
                              "cost": r["cost"], "nodes_explored": r["nodes_explored"],
                              "time_ms": r["execution_time_ms"], "segments": r["segments"]})

    def _station_nodes(self) -> list[str]:
        return [s.node for s in STATIONS]

    def _route_available(self, node: str) -> bool:
        return any(node in self.graph.reachable(s, self.blocked) for s in self._station_nodes())

    def _incident_view(self, inc: dict) -> dict:
        resolved = inc["status"] == "Resolved"
        avail = True if resolved else self._route_available(inc["node"])
        pr = priority_engine.evaluate(inc["severity"], inc["people_affected"], resolved, avail)
        costs: dict[str, Optional[float]] = {}
        if not resolved:
            for s in STATIONS:
                res = ALGORITHMS["astar"](self.graph, s.node, inc["node"], frozenset(self.blocked))
                costs[s.id] = round(res.cost, 3) if res.success else None
        best = min((c for c in costs.values() if c is not None), default=None)
        best_station = next((sid for sid, c in costs.items() if c is not None and c == best), None)
        return {**inc, "priority": pr, "route_costs": costs, "best_cost": best,
                "best_station": best_station, "route_available": avail}

    def _sorted_incidents(self) -> list[dict]:
        views = [self._incident_view(i) for i in self.incidents.values()]
        views.sort(key=lambda v: (not v["priority"]["in_queue"], -v["priority"]["score"], v["id"]))
        return views

    def _metrics_summary(self) -> dict:
        recs = list(self._records)
        ok = [r for r in recs if r["success"]]
        per_alg = []
        for key in ("bfs", "greedy", "astar"):
            rs = [r for r in recs if r["algorithm"] == key]
            oks = [r for r in rs if r["success"]]
            n = len(rs)
            per_alg.append({
                "algorithm": key, "label": ALGORITHM_LABELS[key], "runs": n, "successes": len(oks),
                "avg_time_ms": round(sum(r["time_ms"] for r in rs) / n, 4) if n else None,
                "avg_nodes_explored": round(sum(r["nodes_explored"] for r in rs) / n, 2) if n else None,
                "avg_cost": round(sum(r["cost"] for r in oks) / len(oks), 3) if oks else None,
            })
        return {
            "total_runs": len(recs),
            "successful_routes": len(ok),
            "failed_routes": len(recs) - len(ok),
            "avg_path_cost": round(sum(r["cost"] for r in ok) / len(ok), 3) if ok else None,
            "avg_nodes_explored": round(sum(r["nodes_explored"] for r in recs) / len(recs), 2) if recs else None,
            "per_algorithm": per_alg,
        }

    def _active_view(self) -> Optional[dict]:
        a = self.active
        if not a:
            return None
        view = dict(a)
        res = a["result"]
        # Safety net: never present a route crossing a blocked road as valid.
        if res["success"] and any(
            edge_key(*e.split("-")) in self.blocked for e in res["path_edges"]):
            view["status"] = "invalid"
        return view

    # --------------------------------------------------------------- snapshot
    def state(self) -> dict:
        with self._lock:
            incidents = self._sorted_incidents()
            active_inc = [i for i in incidents if i["status"] == "Active"]
            return {
                "version": self._version,
                "scenario": {"id": self.scenario.id, "name": self.scenario.name,
                             "description": self.scenario.description, "seed": self.scenario.seed},
                "map_center": {"lat": MAP_CENTER[0], "lng": MAP_CENTER[1]},
                "graph": graph_payload(self.graph),
                "stations": [{"id": s.id, "name": s.name, "node": s.node} for s in STATIONS],
                "incidents": incidents,
                "blocked": [{"id": edge_id(u, v), "u": u, "v": v} for u, v in sorted(self.blocked)],
                "active_route": self._active_view(),
                "counts": {
                    "active_incidents": len(active_inc),
                    "critical_incidents": sum(1 for i in active_inc if i["priority"]["priority"] == "Critical"),
                    "resolved_incidents": sum(1 for i in incidents if i["status"] == "Resolved"),
                    "blocked_roads": len(self.blocked),
                    "flagged_alt_access": sum(1 for i in active_inc if i["priority"]["needs_alt_access"]),
                },
                "metrics": self._metrics_summary(),
                "events": list(self._events),
                "rules": [{"id": r.id, "description": r.description} for r in priority_engine.RULES]
                         + [{"id": priority_engine.RESOLVED_RULE[0],
                             "description": priority_engine.RESOLVED_RULE[1]}],
            }

    # ------------------------------------------------------------ scenarios
    @staticmethod
    def list_scenarios() -> list[dict]:
        return [{"id": s.id, "name": s.name, "description": s.description, "seed": s.seed,
                 "incident_count": len(s.incidents), "blocked_count": len(s.blocked)}
                for s in SCENARIOS.values()]

    @staticmethod
    def scenario_definition(scenario_id: str) -> dict:
        if scenario_id not in SCENARIOS:
            raise NotFoundError(f"Unknown scenario: {scenario_id!r}")
        s = SCENARIOS[scenario_id]
        return {
            "id": s.id, "name": s.name, "description": s.description, "seed": s.seed,
            "graph": graph_payload(build_graph(scenario_id)),
            "stations": [{"id": x.id, "name": x.name, "node": x.node} for x in STATIONS],
            "incidents": [{"id": i.id, "type": i.type, "severity": i.severity,
                           "people_affected": i.people_affected, "node": i.node,
                           "description": i.description, "status": "Active"} for i in s.incidents],
            "blocked": [{"id": edge_id(u, v), "u": u, "v": v} for u, v in s.blocked],
        }

    def load_scenario(self, scenario_id: str, clear_metrics: bool = False) -> str:
        with self._lock:
            self._load(scenario_id)
            if clear_metrics:
                self._records.clear()
            self._log("info", "scenario_loaded", f"Scenario loaded: {self.scenario.name} "
                      f"({len(self.incidents)} incidents, {len(self.blocked)} blocked roads)")
            return f"Loaded scenario {self.scenario.name}"

    def reset(self, clear_metrics: bool = False) -> str:
        with self._lock:
            sid = self.scenario.id
            self._load(sid)
            if clear_metrics:
                self._records.clear()
                self._events.clear()
            self._log("warning", "reset", f"Scenario reset to initial state: {self.scenario.name}")
            return f"Scenario {self.scenario.name} reset"

    # --------------------------------------------------------------- routing
    def route(self, source: str, destination: str, algorithm: str = "astar",
              risk_weight: float = 0.0, incident_id: Optional[str] = None,
              station_id: Optional[str] = None) -> dict:
        with self._lock:
            self._check_node(source, "source node")
            self._check_node(destination, "destination node")
            if incident_id is not None and incident_id not in self.incidents:
                raise NotFoundError(f"Unknown incident: {incident_id!r}")
            res = run_route(self.graph, self.blocked, source, destination, algorithm, risk_weight)
            self._record(res, "route")
            self.active = {"result": res, "status": "valid" if res["success"] else "no_route",
                           "incident_id": incident_id, "station_id": station_id,
                           "previous_path": None, "replan_count": 0}
            label = res["algorithm_label"]
            if res["success"]:
                self._log("success", "route_calculated",
                          f"Route calculated ({label}): {source} -> {destination}, "
                          f"cost {res['cost']:.2f}, {res['nodes_explored']} nodes explored")
            else:
                self._log("error", "no_route", f"No valid route available: {source} -> {destination} ({label})")
            self._bump()
            return res

    def _replan_active(self, reason: str, algorithm: Optional[str] = None,
                       risk_weight: Optional[float] = None) -> dict:
        a = self.active
        assert a is not None
        old = a["result"]
        alg = algorithm or "astar"
        rw = old["risk_weight"] if risk_weight is None else risk_weight
        res = run_route(self.graph, self.blocked, old["source"], old["destination"], alg, rw)
        self._record(res, "replan")
        previous = old["path"] if old["success"] else a.get("previous_path")
        a.update(result=res, previous_path=previous,
                 status="replanned" if res["success"] else "no_route",
                 replan_count=a["replan_count"] + 1)
        if res["success"]:
            self._log("success", "route_recalculated",
                      f"Route recalculated ({reason}): new cost {res['cost']:.2f}, "
                      f"{res['segments']} segments, {res['execution_time_ms']:.3f} ms")
        else:
            self._log("error", "no_route", f"No valid route available after {reason}: No safe route available")
        return {"triggered": True, "reason": reason, "success": res["success"],
                "previous_path": previous, "new_path": res["path"],
                "message": f"Route recalculated ({reason})" if res["success"] else "No safe route available"}

    def replan(self, source: Optional[str] = None, destination: Optional[str] = None,
               algorithm: Optional[str] = None, risk_weight: Optional[float] = None) -> tuple[dict, dict]:
        with self._lock:
            if self.active is None and not (source and destination):
                raise ValueError("No active route to recalculate; select a station and incident first")
            if source and destination:
                self._check_node(source, "source node")
                self._check_node(destination, "destination node")
                if self.active is None:
                    res = run_route(self.graph, self.blocked, source, destination,
                                    algorithm or "astar", risk_weight or 0.0)
                    self._record(res, "route")
                    self.active = {"result": res, "status": "valid" if res["success"] else "no_route",
                                   "incident_id": None, "station_id": None,
                                   "previous_path": None, "replan_count": 0}
                    self._log("success" if res["success"] else "error", "route_calculated",
                              f"Route calculated ({res['algorithm_label']}): {source} -> {destination}")
                    self._bump()
                    return res, {"triggered": False, "success": res["success"]}
                self.active["result"] = {**self.active["result"], "source": source, "destination": destination}
            alg = algorithm or self.active["result"]["algorithm"]
            info = self._replan_active("manual recalculation", alg, risk_weight)
            self._bump()
            return self.active["result"], info

    def compare(self, source: str, destination: str, risk_weight: float = 0.0, repeats: int = 25) -> dict:
        with self._lock:
            self._check_node(source, "source node")
            self._check_node(destination, "destination node")
            out = compare_algorithms(self.graph, self.blocked, source, destination, risk_weight, repeats)
            for r in out["results"]:
                self._record(r, "compare")
            ok = sum(1 for r in out["results"] if r["success"])
            self._log("info", "comparison", f"Algorithm comparison run: {source} -> {destination} "
                      f"({ok}/3 algorithms found a route)")
            self._bump()
            return out

    def risk_compare(self, source: str, destination: str, risk_weight: float) -> dict:
        with self._lock:
            self._check_node(source, "source node")
            self._check_node(destination, "destination node")
            out = risk_compare(self.graph, self.blocked, source, destination, risk_weight)
            self._record(out["shortest"], "risk_compare")
            self._record(out["risk_aware"], "risk_compare")
            self._log("info", "risk_comparison", f"Risk-aware comparison run (risk weight {risk_weight:g})")
            self._bump()
            return out

    # -------------------------------------------------------------- roads
    def _check_edge(self, u: str, v: str) -> None:
        self._check_node(u)
        self._check_node(v)
        if not self.graph.has_edge(u, v):
            raise ValueError(f"No road segment between {u!r} and {v!r}")

    def block_road(self, u: str, v: str) -> tuple[str, Optional[dict]]:
        with self._lock:
            self._check_edge(u, v)
            key = edge_key(u, v)
            if key in self.blocked:
                raise ConflictError(f"Road {edge_id(u, v)} is already blocked")
            self.blocked.add(key)
            self._log("warning", "road_blocked", f"Road blocked: {edge_id(u, v)}")
            replan = None
            a = self.active
            if a and a["result"]["success"] and edge_id(u, v) in a["result"]["path_edges"]:
                self._log("warning", "route_invalidated",
                          f"Active route crosses {edge_id(u, v)}; replanning with A*")
                replan = self._replan_active(f"road {edge_id(u, v)} blocked")
            self._bump()
            msg = f"Road {edge_id(u, v)} blocked"
            if replan:
                msg += "; " + ("route replanned" if replan["success"] else "No safe route available")
            return msg, replan

    def unblock_road(self, u: str, v: str) -> tuple[str, Optional[dict]]:
        with self._lock:
            self._check_edge(u, v)
            key = edge_key(u, v)
            if key not in self.blocked:
                raise ConflictError(f"Road {edge_id(u, v)} is not blocked")
            self.blocked.discard(key)
            self._log("info", "road_unblocked", f"Road restored: {edge_id(u, v)}")
            replan = None
            if self.active and not self.active["result"]["success"]:
                replan = self._replan_active(f"road {edge_id(u, v)} restored")
            self._bump()
            return f"Road {edge_id(u, v)} restored", replan

    # ----------------------------------------------------------- incidents
    def add_incident(self, node: Optional[str] = None, type: Optional[str] = None,
                     severity: Optional[str] = None, people_affected: Optional[int] = None,
                     description: Optional[str] = None) -> dict:
        with self._lock:
            n = self._next_incident_no
            # Controlled, reproducible randomness: fixed scenario seed + incident counter.
            rng = random.Random(self.scenario.seed * 1000 + n)
            if node is not None:
                self._check_node(node, "incident node")
            else:
                taken = {i["node"] for i in self.incidents.values() if i["status"] == "Active"}
                taken |= set(self._station_nodes())
                candidates = [x for x in sorted(self.graph.nodes) if x not in taken]
                node = rng.choice(candidates or sorted(self.graph.nodes))
            sev = severity or rng.choices(["critical", "high", "medium", "low"], [2, 4, 3, 1])[0]
            people = people_affected if people_affected is not None else {
                "critical": rng.randint(15, 45), "high": rng.randint(8, 32),
                "medium": rng.randint(3, 18), "low": rng.randint(1, 6)}[sev]
            itype = type or rng.choice(self.scenario.incident_types)
            iid = f"INC-{n:03d}"
            while iid in self.incidents:
                n += 1
                iid = f"INC-{n:03d}"
            self._next_incident_no = n + 1
            inc = {"id": iid, "type": itype, "severity": sev, "people_affected": people,
                   "node": node, "description": description or f"Simulated {itype.lower()} report",
                   "status": "Active"}
            self.incidents[iid] = inc
            self._log("warning", "incident_added",
                      f"Incident added: {iid} ({itype}, {sev}, {people} people) at {node}")
            self._bump()
            return inc

    def resolve_incident(self, incident_id: str) -> str:
        with self._lock:
            inc = self.incidents.get(incident_id)
            if inc is None:
                raise NotFoundError(f"Unknown incident: {incident_id!r}")
            if inc["status"] == "Resolved":
                raise ConflictError(f"Incident {incident_id} is already resolved")
            inc["status"] = "Resolved"
            self._log("success", "incident_resolved", f"Incident marked resolved: {incident_id}")
            if self.active and self.active.get("incident_id") == incident_id:
                self.active = None
            self._bump()
            return f"Incident {incident_id} resolved"

    # ---------------------------------------------------------------- demo
    def run_demo(self) -> dict:
        """Multi-incident demonstration: for each active incident (highest priority first)
        dispatch the cheapest reachable station using A*. Stations are assumed to have
        unlimited capacity (simplification)."""
        with self._lock:
            queue = [i for i in self._sorted_incidents() if i["priority"]["in_queue"]]
            plan = []
            first_set = False
            for inc in queue:
                best = None
                for s in STATIONS:
                    r = run_route(self.graph, self.blocked, s.node, inc["node"], "astar")
                    if r["success"] and (best is None or r["cost"] < best[1]["cost"]):
                        best = (s, r)
                if best is None:
                    r = run_route(self.graph, self.blocked, STATIONS[0].node, inc["node"], "astar")
                    self._record(r, "demo")
                    self._log("error", "no_route", f"No valid route available for {inc['id']}: flagged for alternative access planning")
                    plan.append({"incident_id": inc["id"], "priority": inc["priority"]["priority"],
                                 "station_id": None, "success": False, "cost": None, "path": []})
                    continue
                s, r = best
                self._record(r, "demo")
                self._log("success", "route_calculated",
                          f"Demo dispatch {inc['id']} ({inc['priority']['priority']}) <- {s.id}, cost {r['cost']:.2f}")
                plan.append({"incident_id": inc["id"], "priority": inc["priority"]["priority"],
                             "station_id": s.id, "success": True, "cost": r["cost"], "path": r["path"],
                             "path_edges": r["path_edges"], "segments": r["segments"]})
                if not first_set:
                    first_set = True
                    self.active = {"result": r, "status": "valid", "incident_id": inc["id"],
                                   "station_id": s.id, "previous_path": None, "replan_count": 0}
            self._log("info", "demo", f"Multi-incident demo dispatched {sum(1 for p in plan if p['success'])}"
                      f"/{len(plan)} incidents")
            self._bump()
            return {"plan": plan}


# Singleton used by the API layer.
simulation = SimulationService()
