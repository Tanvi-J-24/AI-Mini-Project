"""Predefined road network and disaster scenarios.

The road graph is a SIMULATED overlay (an irregular 6x7 grid of intersections
around a map centre). It is not extracted from OpenStreetMap, so it is not
claimed to match real roads. Risk scores are simulated, not hazard measurements.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable

from ..algorithms.graph import Edge, Graph, edge_id, edge_key, haversine_km

ROWS, COLS = 6, 7
ORIGIN_LAT, ORIGIN_LNG = 12.9900, 77.5700
LAT_STEP, LNG_STEP = 0.0065, 0.0075
MAP_CENTER = (ORIGIN_LAT - LAT_STEP * (ROWS - 1) / 2, ORIGIN_LNG + LNG_STEP * (COLS - 1) / 2)

# Roads removed from the full grid so the network is irregular.
REMOVED_EDGES = [("N01", "N11"), ("N14", "N24"), ("N21", "N22"), ("N33", "N34"),
                 ("N42", "N52"), ("N35", "N45"), ("N25", "N26")]
# Extra diagonal connector roads.
DIAGONALS = [("N10", "N21"), ("N23", "N34"), ("N32", "N43"), ("N15", "N26"), ("N44", "N55")]


def nid(r: int, c: int) -> str:
    return f"N{r}{c}"


def generate_grid(
    rows: int, cols: int, seed: int, removal_rate: float = 0.0, diagonal_rate: float = 0.0,
    risk_boost: Callable[[float, float], float] | None = None,
    fixed_removed: list[tuple[str, str]] | None = None,
    fixed_diagonals: list[tuple[str, str]] | None = None,
) -> Graph:
    """Deterministic grid road network. Travel cost = distance_km * U(1.0, 1.5)
    so the straight-line heuristic is admissible."""
    rng = random.Random(seed)
    # Single-digit ids (N23) keep the predefined scenarios readable; larger grids are
    # zero-padded (N0312) so ids stay unambiguous.
    pad = max(rows, cols) > 10
    name = (lambda r, c: f"N{r:02d}{c:02d}") if pad else nid
    rc = {name(r, c): (r, c) for r in range(rows) for c in range(cols)}
    nodes = {name(r, c): (ORIGIN_LAT - r * LAT_STEP, ORIGIN_LNG + c * LNG_STEP)
             for r in range(rows) for c in range(cols)}
    removed = {edge_key(*e) for e in (fixed_removed or [])}
    pairs: list[tuple[str, str]] = []
    for r in range(rows):
        for c in range(cols):
            if c + 1 < cols:
                pairs.append((name(r, c), name(r, c + 1)))
            if r + 1 < rows:
                pairs.append((name(r, c), name(r + 1, c)))
    for r in range(rows - 1):
        for c in range(cols - 1):
            if diagonal_rate and rng.random() < diagonal_rate:
                pairs.append((name(r, c), name(r + 1, c + 1)))
    pairs += list(fixed_diagonals or [])
    if removal_rate:
        for p in list(pairs):
            if rng.random() < removal_rate:
                removed.add(edge_key(*p))

    edges: list[Edge] = []
    for u, v in pairs:
        if edge_key(u, v) in removed:
            continue
        dist = haversine_km(*nodes[u], *nodes[v])
        mult = rng.uniform(1.0, 1.5)
        mid_r = (rc[u][0] + rc[v][0]) / 2
        mid_c = (rc[u][1] + rc[v][1]) / 2
        risk = rng.uniform(0.05, 0.35) + (risk_boost(mid_r, mid_c) if risk_boost else 0.0)
        edges.append(Edge(u, v, round(dist * mult, 4), round(min(risk, 1.0), 3)))
    return Graph(nodes, edges)


@dataclass(frozen=True)
class IncidentSeed:
    id: str
    type: str
    severity: str
    people_affected: int
    node: str
    description: str


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    node: str


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str
    seed: int
    blocked: list[tuple[str, str]]
    incidents: list[IncidentSeed]
    risk_boost: Callable[[float, float], float]
    incident_types: list[str] = field(default_factory=list)


STATIONS = [
    Station("S1", "Alpha Command Station", "N10"),
    Station("S2", "Bravo Rescue Base", "N06"),
    Station("S3", "Charlie Field Depot", "N53"),
]

SCENARIOS: dict[str, Scenario] = {
    "flood": Scenario(
        id="flood", name="Flood", seed=101,
        description="River flooding in the southern districts; bridges and low roads are cut.",
        blocked=[("N31", "N32"), ("N32", "N33"), ("N41", "N42"), ("N33", "N43"), ("N24", "N34")],
        incidents=[
            IncidentSeed("INC-001", "Flood Rescue", "critical", 40, "N50", "Residents stranded on rooftops"),
            IncidentSeed("INC-002", "Flood Rescue", "high", 18, "N43", "Families trapped by rising water"),
            IncidentSeed("INC-003", "Medical Evacuation", "medium", 6, "N41", "Care home needs evacuation"),
            IncidentSeed("INC-004", "Supply Drop", "low", 3, "N15", "Isolated households need supplies"),
            IncidentSeed("INC-005", "Flood Rescue", "high", 30, "N34", "Shelter flooded, many people affected"),
        ],
        risk_boost=lambda r, c: 0.45 if r >= 3 else 0.0,
        incident_types=["Flood Rescue", "Medical Evacuation", "Supply Drop"],
    ),
    "fire": Scenario(
        id="fire", name="Urban Fire", seed=202,
        description="Fast-spreading fire in the dense city centre closes central arterial roads.",
        blocked=[("N12", "N13"), ("N22", "N23"), ("N13", "N23"), ("N14", "N15")],
        incidents=[
            IncidentSeed("INC-001", "Structure Fire", "critical", 12, "N23", "High-rise fire, people on upper floors"),
            IncidentSeed("INC-002", "Structure Fire", "high", 8, "N14", "Market building burning"),
            IncidentSeed("INC-003", "Gas Leak", "medium", 4, "N32", "Gas leak near fire front"),
            IncidentSeed("INC-004", "Structure Fire", "high", 26, "N45", "Apartment block evacuation"),
            IncidentSeed("INC-005", "Smoke Casualties", "low", 2, "N02", "Minor smoke inhalation cases"),
        ],
        risk_boost=lambda r, c: 0.5 if 1 <= r <= 3 and 2 <= c <= 4 else 0.0,
        incident_types=["Structure Fire", "Gas Leak", "Smoke Casualties"],
    ),
    "earthquake": Scenario(
        id="earthquake", name="Earthquake", seed=303,
        description="Major earthquake: scattered road damage and multiple building collapses.",
        blocked=[("N11", "N21"), ("N20", "N21"), ("N22", "N32"), ("N34", "N44"),
                 ("N24", "N25"), ("N03", "N04"), ("N43", "N53"), ("N41", "N51")],
        incidents=[
            IncidentSeed("INC-001", "Building Collapse", "critical", 35, "N22", "Residential block collapsed"),
            IncidentSeed("INC-002", "Building Collapse", "critical", 20, "N40", "School partially collapsed"),
            IncidentSeed("INC-003", "Trapped Survivors", "high", 14, "N33", "Survivors under rubble"),
            IncidentSeed("INC-004", "Road Collapse", "medium", 7, "N15", "Vehicles trapped on broken road"),
            IncidentSeed("INC-005", "Trapped Survivors", "high", 11, "N05", "Office building damaged"),
            IncidentSeed("INC-006", "Medical Evacuation", "low", 3, "N46", "Clinic needs patient transfer"),
        ],
        risk_boost=lambda r, c: 0.3,
        incident_types=["Building Collapse", "Trapped Survivors", "Road Collapse", "Medical Evacuation"],
    ),
}


@lru_cache(maxsize=None)
def build_graph(scenario_id: str) -> Graph:
    s = SCENARIOS[scenario_id]
    return generate_grid(ROWS, COLS, seed=s.seed, risk_boost=s.risk_boost,
                         fixed_removed=REMOVED_EDGES, fixed_diagonals=DIAGONALS)


def graph_payload(graph: Graph) -> dict:
    return {
        "nodes": [{"id": n, "lat": lat, "lng": lng} for n, (lat, lng) in graph.nodes.items()],
        "edges": [{"id": edge_id(e.u, e.v), "u": e.u, "v": e.v,
                   "travel_cost": e.travel_cost, "risk": e.risk} for e in graph.edges.values()],
    }
