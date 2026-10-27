import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh():
    client.post("/api/scenarios/flood/load", json={"clear_metrics": True})
    yield


def state():
    return client.get("/api/state").json()


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_scenarios_list_and_detail():
    r = client.get("/api/scenarios")
    assert {s["id"] for s in r.json()["scenarios"]} == {"flood", "fire", "earthquake"}
    d = client.get("/api/scenarios/fire").json()
    assert d["graph"]["nodes"] and d["graph"]["edges"] and d["stations"] and d["incidents"]
    assert client.get("/api/scenarios/nope").status_code == 404


def test_load_each_scenario():
    for sid in ("fire", "earthquake", "flood"):
        r = client.post(f"/api/scenarios/{sid}/load")
        assert r.status_code == 200 and r.json()["state"]["scenario"]["id"] == sid


def test_route_astar_success():
    r = client.post("/api/route", json={"source": "N10", "destination": "N15", "algorithm": "astar"})
    body = r.json()
    assert r.status_code == 200 and body["ok"] and body["route"]["success"]
    assert body["route"]["path"][0] == "N10" and body["route"]["path"][-1] == "N15"
    assert body["route"]["nodes_explored"] > 0
    assert body["state"]["active_route"]["result"]["path"] == body["route"]["path"]


def test_route_invalid_input():
    assert client.post("/api/route", json={"source": "BAD", "destination": "N15"}).status_code == 400
    assert client.post("/api/route", json={"source": "N10", "destination": "N15",
                                           "algorithm": "dijkstra"}).status_code == 422
    assert client.post("/api/route", json={"source": "N10"}).status_code == 422
    assert client.post("/api/route", json={"source": "N10", "destination": "N15",
                                           "risk_weight": -1}).status_code == 422


def test_compare_returns_three_real_results():
    r = client.post("/api/compare", json={"source": "N10", "destination": "N56", "repeats": 5})
    body = r.json()
    assert r.status_code == 200
    algs = {x["algorithm"]: x for x in body["results"]}
    assert set(algs) == {"bfs", "greedy", "astar"}
    assert algs["astar"]["is_optimal"] is True
    assert algs["astar"]["cost"] <= min(algs["bfs"]["cost"], algs["greedy"]["cost"]) + 1e-9
    assert all(x["nodes_explored"] > 0 for x in algs.values())
    assert state()["metrics"]["total_runs"] == 3


def test_block_unblock_and_errors():
    r = client.post("/api/block-road", json={"u": "N10", "v": "N11"})
    assert r.status_code == 200 and "N10-N11" in {b["id"] for b in r.json()["state"]["blocked"]}
    assert client.post("/api/block-road", json={"u": "N10", "v": "N11"}).status_code == 409
    assert client.post("/api/block-road", json={"u": "N10", "v": "N66"}).status_code == 400
    assert client.post("/api/unblock-road", json={"u": "N10", "v": "N11"}).status_code == 200
    assert client.post("/api/unblock-road", json={"u": "N10", "v": "N11"}).status_code == 409


def test_routes_respect_blockage_and_replan():
    route = client.post("/api/route", json={"source": "N10", "destination": "N15"}).json()["route"]
    u, v = route["path"][0], route["path"][1]
    r = client.post("/api/block-road", json={"u": u, "v": v}).json()
    assert r["replan"]["triggered"] is True
    new = r["route"]["result"]
    assert new["success"]
    assert f"{min(u, v)}-{max(u, v)}" not in new["path_edges"]
    blocked_ids = {b["id"] for b in r["state"]["blocked"]}
    assert not blocked_ids & set(new["path_edges"])


def test_replan_endpoint():
    assert client.post("/api/replan").status_code == 400  # no active route yet
    client.post("/api/route", json={"source": "N10", "destination": "N15", "algorithm": "bfs"})
    r = client.post("/api/replan")
    assert r.status_code == 200 and r.json()["route"]["success"]


def test_incidents_and_resolve():
    r = client.post("/api/incidents", json={})
    assert r.status_code == 201
    inc = r.json()["extra"]["incident"]
    assert inc["id"] == "INC-006"
    assert client.post("/api/incidents", json={"node": "BAD"}).status_code == 400
    assert client.post("/api/incidents", json={"severity": "meh"}).status_code == 422
    assert client.post("/api/resolve-incident", json={"incident_id": inc["id"]}).status_code == 200
    assert client.post("/api/resolve-incident", json={"incident_id": inc["id"]}).status_code == 409
    assert client.post("/api/resolve-incident", json={"incident_id": "INC-404"}).status_code == 404


def test_reset_restores_scenario():
    client.post("/api/block-road", json={"u": "N10", "v": "N11"})
    client.post("/api/incidents", json={})
    r = client.post("/api/reset")
    st = r.json()["state"]
    assert "N10-N11" not in {b["id"] for b in st["blocked"]}
    assert len(st["incidents"]) == 5


def test_risk_compare_and_demo():
    r = client.post("/api/risk-compare", json={"source": "N10", "destination": "N50", "risk_weight": 5})
    assert r.status_code == 200
    ex = r.json()["extra"]
    assert ex["risk_aware"]["risk_total"] <= ex["shortest"]["risk_total"] + 1e-9
    d = client.post("/api/demo")
    assert d.status_code == 200 and len(d.json()["extra"]["plan"]) == 5
