import pytest

from app.algorithms import ALGORITHMS, Edge, Graph, astar, bfs, greedy_best_first
from app.algorithms.graph import edge_key, haversine_km
from app.data.scenarios import SCENARIOS, build_graph, generate_grid


def make_graph(coords, pairs, mult=None):
    """Graph whose edge cost = haversine distance * multiplier (>=1) -> heuristic admissible."""
    mult = mult or {}
    edges = []
    for u, v in pairs:
        d = haversine_km(*coords[u], *coords[v])
        edges.append(Edge(u, v, d * mult.get((u, v), mult.get((v, u), 1.0))))
    return Graph(coords, edges)


@pytest.fixture
def diamond():
    # S-G direct costs 1.5x its length; S-M-G detour is cheaper but has more edges.
    coords = {"S": (12.0, 77.0), "M": (12.0005, 77.01), "G": (12.0, 77.02), "X": (12.01, 77.01)}
    pairs = [("S", "G"), ("S", "M"), ("M", "G"), ("S", "X"), ("X", "G")]
    return make_graph(coords, pairs, {("S", "G"): 1.5, ("S", "X"): 1.3, ("X", "G"): 1.3})


@pytest.fixture
def grid():
    return generate_grid(4, 4, seed=1)


def path_is_valid(graph, path, blocked=frozenset()):
    return all(graph.has_edge(a, b) and edge_key(a, b) not in blocked for a, b in zip(path, path[1:]))


def test_heuristic_admissible_on_scenarios():
    for sid in SCENARIOS:
        assert build_graph(sid).heuristic_is_admissible()


def test_astar_finds_valid_path(grid):
    r = astar(grid, "N00", "N33")
    assert r.success and r.path[0] == "N00" and r.path[-1] == "N33"
    assert path_is_valid(grid, r.path)
    assert r.nodes_explored > 0 and r.execution_time_ms >= 0


def test_astar_is_optimal_vs_dijkstra_like_zero_heuristic(diamond):
    r = astar(diamond, "S", "G")
    assert r.path == ["S", "M", "G"]
    direct = diamond.path_cost(["S", "G"])
    assert r.cost < direct
    # brute-force check across all simple paths
    best = min(diamond.path_cost(p) for p in [["S", "G"], ["S", "M", "G"], ["S", "X", "G"]])
    assert r.cost == pytest.approx(best)


def test_astar_optimal_on_random_grids_matches_exhaustive_dijkstra():
    import heapq
    for seed in range(5):
        g = generate_grid(5, 5, seed=seed, removal_rate=0.1, diagonal_rate=0.2)
        dist = {"N00": 0.0}
        h = [(0.0, "N00")]
        while h:
            d, u = heapq.heappop(h)
            if d > dist[u]:
                continue
            for v, c in g.neighbors(u, frozenset()):
                if d + c < dist.get(v, 1e18):
                    dist[v] = d + c
                    heapq.heappush(h, (d + c, v))
        r = astar(g, "N00", "N44")
        if "N44" in dist:
            assert r.success and r.cost == pytest.approx(dist["N44"])
        else:
            assert not r.success


def test_bfs_minimum_edges_and_not_necessarily_cheapest(diamond):
    r = bfs(diamond, "S", "G")
    assert r.path == ["S", "G"]  # fewest edges
    assert r.cost > astar(diamond, "S", "G").cost  # but costlier


def test_bfs_min_edge_on_unweighted_grid():
    g = generate_grid(4, 4, seed=3)
    r = bfs(g, "N00", "N33")
    assert r.success and len(r.path) - 1 == 6  # Manhattan distance on a full grid


def test_greedy_returns_valid_path(grid):
    r = greedy_best_first(grid, "N00", "N33")
    assert r.success and path_is_valid(grid, r.path)
    assert r.path[0] == "N00" and r.path[-1] == "N33"


@pytest.mark.parametrize("name", list(ALGORITHMS))
def test_algorithms_avoid_blocked_edges(grid, name):
    base = ALGORITHMS[name](grid, "N00", "N33")
    blocked = {edge_key(a, b) for a, b in zip(base.path, base.path[1:])}
    r = ALGORITHMS[name](grid, "N00", "N33", blocked)
    assert r.success
    assert path_is_valid(grid, r.path, blocked)
    assert not blocked & {edge_key(a, b) for a, b in zip(r.path, r.path[1:])}


@pytest.mark.parametrize("name", list(ALGORITHMS))
def test_unreachable_returns_clean_failure(grid, name):
    blocked = {edge_key("N33", nb) for nb in grid.adj["N33"]}
    r = ALGORITHMS[name](grid, "N00", "N33", blocked)
    assert not r.success and r.path == [] and r.cost == 0.0
    assert r.message == "No safe route available"


@pytest.mark.parametrize("name", list(ALGORITHMS))
def test_source_equals_destination(grid, name):
    r = ALGORITHMS[name](grid, "N11", "N11")
    assert r.success and r.path == ["N11"] and r.cost == 0.0


@pytest.mark.parametrize("name", list(ALGORITHMS))
def test_invalid_nodes_raise(grid, name):
    with pytest.raises(ValueError):
        ALGORITHMS[name](grid, "NOPE", "N33")
    with pytest.raises(ValueError):
        ALGORITHMS[name](grid, "N00", "NOPE")


def test_risk_weight_changes_route_cost_and_stays_valid(grid):
    r0 = astar(grid, "N00", "N33", frozenset(), 0.0)
    r5 = astar(grid, "N00", "N33", frozenset(), 5.0)
    assert r5.cost >= r0.cost
    assert r5.cost == pytest.approx(grid.path_cost(r5.path, 5.0))
    # risk-aware route should have risk <= shortest route risk
    assert grid.path_risk(r5.path) <= grid.path_risk(r0.path) + 1e-9
