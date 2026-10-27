import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { api, ApiError } from "../services/api";
import IncidentPanel from "../components/IncidentPanel";
import RouteAnalysis from "../components/RouteAnalysis";
import EventLog from "../components/EventLog";
import PerformanceDashboard from "../components/PerformanceDashboard";
import type { SimState } from "../types";

afterEach(() => vi.restoreAllMocks());

const priority = (p: string, reason = "rule") => ({
  priority: p, level: 4, score: 440, in_queue: true, needs_alt_access: false, rules_fired: [], reason,
});

const sim = {
  version: 1,
  scenario: { id: "flood", name: "Flood", description: "Flood scenario", seed: 1 },
  map_center: { lat: 0, lng: 0 },
  graph: { nodes: [], edges: [] },
  stations: [{ id: "S1", name: "Alpha", node: "N10" }],
  incidents: [{
    id: "INC-001", type: "Flood Rescue", severity: "critical", people_affected: 40, node: "N50",
    description: "d", status: "Active", priority: priority("Critical"), route_costs: { S1: 5 },
    best_cost: 5, best_station: "S1", route_available: true,
  }],
  blocked: [], active_route: null,
  counts: { active_incidents: 1, critical_incidents: 1, resolved_incidents: 0, blocked_roads: 5, flagged_alt_access: 0 },
  metrics: { total_runs: 0, successful_routes: 0, failed_routes: 0, avg_path_cost: null, avg_nodes_explored: null, per_algorithm: [] },
  events: [{ id: 1, time: new Date().toISOString(), level: "success", type: "route_calculated", message: "Route calculated (A*)" }],
  rules: [],
} as unknown as SimState;

const fakeR = (over: Record<string, unknown> = {}) => ({
  sim, selectedIncidentId: null, selectedStationId: "S1", selectedIncident: null, selectedStation: sim.stations[0],
  edgeTool: "none", algorithm: "astar", riskWeight: 0, comparison: null, riskCmp: null, demoPlan: null,
  loadScenario: vi.fn(), selectIncident: vi.fn(), selectStation: vi.fn(), setEdgeTool: vi.fn(),
  addIncident: vi.fn(), recalculate: vi.fn(), runDemo: vi.fn(), resetScenario: vi.fn(), resolveIncident: vi.fn(),
  setAlgorithm: vi.fn(), calculate: vi.fn(), compare: vi.fn(), compareRisk: vi.fn(), demoBlockOnRoute: vi.fn(),
  setRiskWeight: vi.fn(), ...over,
// eslint-disable-next-line @typescript-eslint/no-explicit-any
}) as any;

describe("api service", () => {
  it("reports an unavailable backend clearly", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("failed")));
    await expect(api.health()).rejects.toMatchObject({ status: 0, message: expect.stringContaining("Backend unavailable") });
  });
  it("surfaces backend error details", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ detail: "Road X is already blocked" }) }));
    const err = await api.blockRoad("a", "b").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe("Road X is already blocked");
  });
  it("formats validation (422) errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 422, json: async () => ({ detail: [{ loc: ["body", "risk_weight"], msg: "too small" }] }) }));
    const err = await api.route({ source: "a", destination: "b", algorithm: "astar", risk_weight: -1 }).catch((e) => e);
    expect(err.message).toContain("risk_weight: too small");
  });
});

describe("IncidentPanel", () => {
  it("selecting an incident and scenario calls the handlers", () => {
    const r = fakeR();
    render(<IncidentPanel r={r} />);
    fireEvent.click(screen.getByText("INC-001"));
    expect(r.selectIncident).toHaveBeenCalledWith("INC-001");
    fireEvent.click(screen.getByRole("button", { name: /Earthquake/ }));
    expect(r.loadScenario).toHaveBeenCalledWith("earthquake");
  });
  it("simulation controls perform actions", () => {
    const r = fakeR();
    render(<IncidentPanel r={r} />);
    fireEvent.click(screen.getByRole("button", { name: /Add blockage/ }));
    expect(r.setEdgeTool).toHaveBeenCalledWith("block");
    fireEvent.click(screen.getByRole("button", { name: /New incident/ }));
    expect(r.addIncident).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /Recalculate/ }));
    expect(r.recalculate).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /Reset scenario/ }));
    expect(r.resetScenario).toHaveBeenCalled();
  });
});

describe("RouteAnalysis", () => {
  it("shows an empty state, then the no-route failure state", () => {
    const { rerender } = render(<RouteAnalysis r={fakeR()} />);
    expect(screen.getByText("No route calculated")).toBeInTheDocument();
    const failed = { ...sim, active_route: { status: "no_route", incident_id: null, station_id: null, previous_path: null, replan_count: 1,
      result: { success: false, algorithm: "astar", path: [], path_edges: [], nodes_explored: 12, execution_time_ms: 0.1, cost: 0, segments: 0 } } } as unknown as SimState;
    rerender(<RouteAnalysis r={fakeR({ sim: failed })} />);
    expect(screen.getAllByText("No safe route available").length).toBeGreaterThan(0);
  });
  it("validates the compare action via handler", () => {
    const r = fakeR();
    render(<RouteAnalysis r={r} />);
    fireEvent.click(screen.getByRole("button", { name: /Run algorithm comparison/ }));
    expect(r.compare).toHaveBeenCalled();
  });
});

describe("dashboard and log", () => {
  it("renders counts and events from state", () => {
    render(<><PerformanceDashboard sim={sim} /><EventLog events={sim.events} /></>);
    expect(screen.getByText("Route calculated (A*)")).toBeInTheDocument();
    expect(screen.getByText("Blocked roads")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText(/No algorithm runs yet/)).toBeInTheDocument();
  });
});
