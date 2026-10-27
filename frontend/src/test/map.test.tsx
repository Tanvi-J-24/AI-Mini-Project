import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import RescueMap from "../components/RescueMap";
import type { SimState } from "../types";

const nodes = [
  { id: "A", lat: 12.99, lng: 77.57 }, { id: "B", lat: 12.99, lng: 77.58 },
  { id: "C", lat: 12.98, lng: 77.58 }, { id: "D", lat: 12.98, lng: 77.57 },
];
const edge = (u: string, v: string) => ({ id: `${u}-${v}`, u, v, travel_cost: 1, risk: 0.2 });
const result = (path: string[], success = true) => ({
  algorithm: "astar", algorithm_label: "A* Search", source: "A", destination: "C", success, path,
  path_edges: path.slice(1).map((n, i) => `${path[i]}-${n}`), cost: 2, travel_cost: 2, risk_total: 0.4,
  risk_weight: 0, segments: Math.max(path.length - 1, 0), nodes_explored: 3, explored: [],
  execution_time_ms: 0.01, estimated_minutes: 3, message: "ok",
});
const base = {
  version: 1, scenario: { id: "t", name: "T", description: "", seed: 1 }, map_center: { lat: 12.985, lng: 77.575 },
  graph: { nodes, edges: [edge("A", "B"), edge("B", "C"), edge("A", "D"), edge("C", "D")] },
  stations: [{ id: "S1", name: "Alpha", node: "A" }],
  incidents: [{ id: "INC-001", type: "Fire", severity: "critical", people_affected: 5, node: "C", description: "x",
    status: "Active", priority: { priority: "Critical", reason: "R1" }, route_costs: {}, best_cost: 2, best_station: "S1", route_available: true }],
  blocked: [{ id: "C-D", u: "C", v: "D" }],
  counts: {}, metrics: {}, events: [], rules: [],
};

const mkR = (sim: unknown) => ({
  sim, selectedIncidentId: "INC-001", selectedIncident: (sim as SimState).incidents[0], selectedStationId: "S1",
  edgeTool: "none", comparison: null, showCompareRoutes: true, riskCmp: null, loading: false,
  handleRoadClick: vi.fn(), selectStation: vi.fn(), selectIncident: vi.fn(), setShowCompareRoutes: vi.fn(), notify: vi.fn(),
// eslint-disable-next-line @typescript-eslint/no-explicit-any
}) as any;

describe("RescueMap", () => {
  it("renders roads, route, waypoints and legend without crashing", () => {
    const sim = { ...base, active_route: { status: "replanned", previous_path: ["A", "D", "C"], replan_count: 1,
      incident_id: "INC-001", station_id: "S1", result: result(["A", "B", "C"]) } };
    const { container } = render(<RescueMap r={mkR(sim)} />);
    expect(container.querySelector("#rescue-map")).toBeInTheDocument();
    expect(screen.getByText("Legend")).toBeInTheDocument();
    expect(screen.getByText("INC-001", { exact: false })).toBeInTheDocument();
  });
  it("shows the no-route banner instead of a route when the search failed", () => {
    const sim = { ...base, active_route: { status: "no_route", previous_path: null, replan_count: 1,
      incident_id: "INC-001", station_id: "S1", result: result([], false) } };
    render(<RescueMap r={mkR(sim)} />);
    expect(screen.getByText("No safe route available")).toBeInTheDocument();
  });
});
