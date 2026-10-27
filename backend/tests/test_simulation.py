import pytest

from app.algorithms.graph import edge_key
from app.data.scenarios import SCENARIOS, STATIONS, build_graph
from app.services import priority_engine as pe
from app.services.simulation_service import ConflictError, NotFoundError, SimulationService


@pytest.fixture
def sim():
    return SimulationService("flood")


# ---------------------------------------------------------------- priority engine
def test_critical_severity_is_critical():
    r = pe.evaluate("critical", 5, False, True)
    assert r["priority"] == "Critical" and r["rules_fired"][0]["id"] == "R1"


def test_high_with_many_people_escalates_to_critical():
    r = pe.evaluate("high", 30, False, True)
    assert r["priority"] == "Critical"
    assert [x["id"] for x in r["rules_fired"]] == ["R2", "R5"]  # forward chaining R2 -> R5


def test_high_with_few_people_stays_high():
    assert pe.evaluate("high", 10, False, True)["priority"] == "High"


def test_medium_with_many_people_escalates_to_high():
    assert pe.evaluate("medium", 20, False, True)["priority"] == "High"


def test_low_and_medium_basic():
    assert pe.evaluate("low", 1, False, True)["priority"] == "Low"
    assert pe.evaluate("medium", 1, False, True)["priority"] == "Medium"


def test_resolved_is_removed_from_queue():
    r = pe.evaluate("critical", 50, True, True)
    assert r["priority"] == "Resolved" and r["in_queue"] is False


def test_unreachable_flags_alt_access():
    r = pe.evaluate("medium", 2, False, False)
    assert r["needs_alt_access"] is True and "alternative access" in r["reason"]
    assert pe.evaluate("medium", 2, False, True)["needs_alt_access"] is False


# ---------------------------------------------------------------- scenarios
def test_scenario_data_is_consistent():
    station_nodes = {s.node for s in STATIONS}
    for sid, s in SCENARIOS.items():
        g = build_graph(sid)
        for u, v in s.blocked:
            assert g.has_edge(u, v), (sid, u, v)
        ids = [i.id for i in s.incidents]
        assert len(ids) == len(set(ids))
        for i in s.incidents:
            assert g.has_node(i.node) and i.node not in station_nodes


def test_scenarios_differ():
    blocked = {sid: frozenset(edge_key(*e) for e in s.blocked) for sid, s in SCENARIOS.items()}
    assert len(set(blocked.values())) == 3
    assert len({tuple(i.node for i in s.incidents) for s in SCENARIOS.values()}) == 3


# ---------------------------------------------------------------- simulation
def first_incident_route(sim):
    inc = next(i for i in sim.state()["incidents"] if i["status"] == "Active" and i["best_station"])
    st = next(s for s in STATIONS if s.id == inc["best_station"])
    return st.node, inc["node"], inc["id"]


def test_blocking_route_edge_triggers_replan(sim):
    src, dst, iid = first_incident_route(sim)
    res = sim.route(src, dst, "astar", 0.0, iid)
    assert res["success"]
    u, v = res["path"][0], res["path"][1]
    old_path = res["path"]
    _, replan = sim.block_road(u, v)
    assert replan and replan["triggered"]
    new = sim.state()["active_route"]["result"]
    if new["success"]:
        assert new["path"] != old_path
        assert (u, v) not in list(zip(new["path"], new["path"][1:]))
        assert (v, u) not in list(zip(new["path"], new["path"][1:]))
        assert sim.state()["active_route"]["previous_path"] == old_path


def test_blocking_all_alternatives_gives_no_route(sim):
    src, dst, iid = first_incident_route(sim)
    sim.route(src, dst, "astar", 0.0, iid)
    for nb in list(sim.graph.adj[dst]):
        if edge_key(dst, nb) not in sim.blocked:
            sim.block_road(dst, nb)
    ar = sim.state()["active_route"]
    assert ar["result"]["success"] is False
    assert ar["result"]["message"] == "No safe route available"
    assert ar["status"] == "no_route"
    inc = next(i for i in sim.state()["incidents"] if i["id"] == iid)
    assert inc["priority"]["needs_alt_access"] is True


def test_unblock_recovers_route(sim):
    src, dst, iid = first_incident_route(sim)
    sim.route(src, dst, "astar", 0.0, iid)
    nbs = [nb for nb in sim.graph.adj[dst] if edge_key(dst, nb) not in sim.blocked]
    for nb in nbs:
        sim.block_road(dst, nb)
    assert not sim.state()["active_route"]["result"]["success"]
    sim.unblock_road(dst, nbs[0])
    assert sim.state()["active_route"]["result"]["success"]


def test_reset_restores_initial_state(sim):
    initial_blocked = {b["id"] for b in sim.state()["blocked"]}
    sim.add_incident()
    sim.resolve_incident("INC-001")
    free = next(e for k, e in sim.graph.edges.items() if k not in sim.blocked)
    sim.block_road(free.u, free.v)
    sim.reset()
    st = sim.state()
    assert {b["id"] for b in st["blocked"]} == initial_blocked
    assert len(st["incidents"]) == len(SCENARIOS["flood"].incidents)
    assert all(i["status"] == "Active" for i in st["incidents"])
    assert st["active_route"] is None


def test_add_incident_unique_ids_valid_nodes_and_reproducible():
    a, b = SimulationService("fire"), SimulationService("fire")
    ia = [a.add_incident() for _ in range(4)]
    ib = [b.add_incident() for _ in range(4)]
    assert ia == ib  # fixed seeds -> reproducible
    assert len({i["id"] for i in ia}) == 4
    assert all(a.graph.has_node(i["node"]) for i in ia)
    assert not {i["id"] for i in ia} & {i.id for i in SCENARIOS["fire"].incidents}


def test_invalid_operations(sim):
    with pytest.raises(ValueError):
        sim.block_road("N00", "N66")  # nonexistent road
    with pytest.raises(ValueError):
        sim.add_incident(node="ZZZ")
    with pytest.raises(NotFoundError):
        sim.resolve_incident("INC-999")
    with pytest.raises(ConflictError):
        sim.unblock_road("N00", "N01")
    with pytest.raises(NotFoundError):
        sim.load_scenario("tsunami")


def test_resolve_incident_moves_it_out_of_queue(sim):
    sim.resolve_incident("INC-001")
    st = sim.state()
    inc = next(i for i in st["incidents"] if i["id"] == "INC-001")
    assert inc["status"] == "Resolved" and inc["priority"]["in_queue"] is False
    assert st["counts"]["resolved_incidents"] == 1
    assert st["incidents"][-1]["id"] == "INC-001"  # sorted after active queue


def test_metrics_come_from_real_runs(sim):
    assert sim.state()["metrics"]["total_runs"] == 0
    src, dst, _ = first_incident_route(sim)
    out = sim.compare(src, dst, 0.0, repeats=3)
    m = sim.state()["metrics"]
    assert m["total_runs"] == 3
    assert {a["algorithm"] for a in m["per_algorithm"] if a["runs"] == 1} == {"bfs", "greedy", "astar"}
    astar_row = next(r for r in out["results"] if r["algorithm"] == "astar")
    assert astar_row["is_optimal"] is True


def test_demo_dispatches_all_reachable(sim):
    out = sim.run_demo()
    assert len(out["plan"]) == len(SCENARIOS["flood"].incidents)
    assert all(p["success"] for p in out["plan"])
    pr = [p["priority"] for p in out["plan"]]
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    assert [order[x] for x in pr] == sorted(order[x] for x in pr)
