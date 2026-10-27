import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "../services/api";
import type {
  Algorithm, ComparisonResponse, DemoPlanItem, GraphEdge, Incident, MutationResponse,
  RiskComparison, SimState,
} from "../types";

export type EdgeTool = "none" | "block" | "unblock";
export interface Toast { text: string; kind: "info" | "success" | "warning" | "error"; id: number }

export function useRescue() {
  const [sim, setSim] = useState<SimState | null>(null);
  const [pending, setPending] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [selectedStationId, setSelectedStationId] = useState<string>("S1");
  const [algorithm, setAlgorithmState] = useState<Algorithm>("astar");
  const [riskWeight, setRiskWeight] = useState(0);
  const [edgeTool, setEdgeTool] = useState<EdgeTool>("none");
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [showCompareRoutes, setShowCompareRoutes] = useState(true);
  const [riskCmp, setRiskCmp] = useState<RiskComparison | null>(null);
  const [demoPlan, setDemoPlan] = useState<DemoPlanItem[] | null>(null);

  const versionRef = useRef(-1);
  const seqRef = useRef(0);
  const toastId = useRef(0);

  const notify = useCallback((text: string, kind: Toast["kind"] = "info") => {
    toastId.current += 1;
    setToast({ text, kind, id: toastId.current });
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4500);
    return () => clearTimeout(t);
  }, [toast]);

  /** Only accept state that is at least as new as what we already show. */
  const applyState = useCallback((s: SimState) => {
    if (s.version >= versionRef.current) {
      versionRef.current = s.version;
      setSim(s);
    }
  }, []);

  /** Run an API call; stale responses never overwrite newer user actions. */
  const run = useCallback(
    async <T,>(fn: () => Promise<T>, onOk?: (r: T) => void, stateOf?: (r: T) => SimState | undefined) => {
      const seq = ++seqRef.current;
      setPending((p) => p + 1);
      try {
        const r = await fn();
        const st = stateOf?.(r);
        if (st) applyState(st);
        if (seq === seqRef.current) {
          setError(null);
          onOk?.(r);
        }
        return r;
      } catch (e) {
        if (seq === seqRef.current) {
          const msg = e instanceof ApiError ? e.message : "Unexpected error";
          if (e instanceof ApiError && e.status === 0) setError(msg);
          notify(msg, "error");
        }
        return undefined;
      } finally {
        setPending((p) => p - 1);
      }
    },
    [applyState, notify],
  );

  const refresh = useCallback(
    () => run(() => api.state(), undefined, (s) => s),
    [run],
  );
  useEffect(() => { void refresh(); }, [refresh]);

  // ---- derived -------------------------------------------------------
  const selectedIncident: Incident | null = useMemo(
    () => sim?.incidents.find((i) => i.id === selectedIncidentId) ?? null,
    [sim, selectedIncidentId],
  );
  const selectedStation = useMemo(
    () => sim?.stations.find((s) => s.id === selectedStationId) ?? null,
    [sim, selectedStationId],
  );

  // Drop selection if the incident disappeared or was resolved.
  useEffect(() => {
    if (selectedIncidentId && sim) {
      const inc = sim.incidents.find((i) => i.id === selectedIncidentId);
      if (!inc || inc.status === "Resolved") setSelectedIncidentId(null);
    }
  }, [sim, selectedIncidentId]);

  const clearAnalysis = () => { setComparison(null); setRiskCmp(null); setDemoPlan(null); };

  // ---- actions ---------------------------------------------------------
  const calculate = useCallback(
    async (o: { incidentId?: string; stationId?: string; algorithm?: Algorithm; riskWeight?: number } = {}) => {
      if (!sim) return;
      const inc = sim.incidents.find((i) => i.id === (o.incidentId ?? selectedIncidentId));
      const st = sim.stations.find((s) => s.id === (o.stationId ?? selectedStationId));
      if (!st) return notify("Select a rescue station first.", "warning");
      if (!inc) return notify("Select an incident (destination) first.", "warning");
      if (inc.status === "Resolved") return notify("That incident is already resolved.", "warning");
      const rw = o.riskWeight ?? riskWeight;
      await run(
        () => api.route({ source: st.node, destination: inc.node, algorithm: o.algorithm ?? algorithm,
                          risk_weight: rw, incident_id: inc.id, station_id: st.id }),
        (r) => {
          if (r.ok) notify(`Route calculated: ${st.id} → ${inc.id}`, "success");
          else notify("No safe route available", "error");
        },
        (r) => r.state,
      );
    },
    [sim, selectedIncidentId, selectedStationId, algorithm, riskWeight, run, notify],
  );

  const selectIncident = (id: string) => {
    setSelectedIncidentId(id);
    setDemoPlan(null);
    void calculate({ incidentId: id });
  };

  const selectStation = (id: string) => {
    setSelectedStationId(id);
    if (selectedIncidentId) void calculate({ stationId: id });
  };

  const setAlgorithm = (a: Algorithm) => {
    setAlgorithmState(a);
    if (selectedIncidentId) void calculate({ algorithm: a });
  };

  const handleReplanResult = (r: MutationResponse) => {
    if (r.replan?.triggered) {
      notify(r.replan.success ? "Active route blocked: route recalculated with A*" : "No safe route available",
             r.replan.success ? "warning" : "error");
    } else notify(r.message, "info");
  };

  const recalculate = useCallback(async () => {
    if (!sim?.active_route) return notify("No active route yet. Select an incident first.", "warning");
    await run(() => api.replan({ risk_weight: riskWeight }), (r) => {
      notify(r.ok ? "Route recalculated" : "No safe route available", r.ok ? "success" : "error");
    }, (r) => r.state);
  }, [sim, run, riskWeight, notify]);

  const compare = useCallback(async () => {
    if (!sim) return;
    const inc = selectedIncident;
    const st = selectedStation;
    if (!st || !inc) return notify("Select a station and an incident before comparing.", "warning");
    await run(
      () => api.compare({ source: st.node, destination: inc.node, risk_weight: riskWeight, repeats: 25 }),
      (r) => { setComparison(r); setShowCompareRoutes(true); notify("Algorithm comparison complete", "success"); },
      (r) => r.state,
    );
  }, [sim, selectedIncident, selectedStation, riskWeight, run, notify]);

  const compareRisk = useCallback(async () => {
    const inc = selectedIncident;
    const st = selectedStation;
    if (!st || !inc) return notify("Select a station and an incident first.", "warning");
    const w = riskWeight > 0 ? riskWeight : 3;
    await run(
      () => api.riskCompare({ source: st.node, destination: inc.node, risk_weight: w }),
      (r) => { setRiskCmp(r.extra as unknown as RiskComparison); notify(`Risk-aware comparison (weight ${w})`, "success"); },
      (r) => r.state,
    );
  }, [selectedIncident, selectedStation, riskWeight, run, notify]);

  const blockEdge = useCallback(async (e: GraphEdge, blocked: boolean) => {
    await run(
      () => (blocked ? api.unblockRoad(e.u, e.v) : api.blockRoad(e.u, e.v)),
      (r) => { clearAnalysis(); handleReplanResult(r); },
      (r) => r.state,
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run]);

  const handleRoadClick = (e: GraphEdge) => {
    if (!sim) return;
    const isBlocked = sim.blocked.some((b) => b.id === e.id);
    if (edgeTool === "block" && isBlocked) return notify(`Road ${e.id} is already blocked`, "warning");
    if (edgeTool === "unblock" && !isBlocked) return notify(`Road ${e.id} is not blocked`, "warning");
    void blockEdge(e, isBlocked);
  };

  /** Visible demo of dynamic replanning: block the middle segment of the active route. */
  const demoBlockOnRoute = () => {
    const r = sim?.active_route?.result;
    if (!sim || !r || !r.success || r.path_edges.length === 0)
      return notify("Calculate a route first, then block a road on it.", "warning");
    const eid = r.path_edges[Math.floor(r.path_edges.length / 2)];
    const edge = sim.graph.edges.find((e) => e.id === eid);
    if (edge) void blockEdge(edge, false);
  };

  const addIncident = () =>
    run(() => api.addIncident({}), (r) => notify(r.message, "success"), (r) => r.state);

  const resolveIncident = (id: string) =>
    run(() => api.resolveIncident(id), (r) => { setDemoPlan(null); notify(r.message, "success"); }, (r) => r.state);

  const loadScenario = (id: string) =>
    run(() => api.loadScenario(id), (r) => {
      clearAnalysis(); setSelectedIncidentId(null); setEdgeTool("none"); notify(r.message, "info");
    }, (r) => r.state);

  const resetScenario = (clearMetrics = false) =>
    run(() => api.reset(clearMetrics), (r) => {
      clearAnalysis(); setSelectedIncidentId(null); setEdgeTool("none"); notify(r.message, "info");
    }, (r) => r.state);

  const runDemo = () =>
    run(() => api.demo(), (r) => {
      const plan = ((r.extra as { plan?: DemoPlanItem[] } | null)?.plan ?? []);
      setDemoPlan(plan);
      const first = plan.find((p) => p.success);
      if (first) setSelectedIncidentId(first.incident_id);
      if (first?.station_id) setSelectedStationId(first.station_id);
      notify(`Demo: dispatched ${plan.filter((p) => p.success).length}/${plan.length} incidents by priority`, "success");
    }, (r) => r.state);

  return {
    sim, loading: pending > 0, error, toast, dismissToast: () => setToast(null), refresh,
    selectedIncident, selectedStation, selectedIncidentId, selectedStationId,
    algorithm, setAlgorithm, riskWeight, setRiskWeight, edgeTool, setEdgeTool,
    comparison, showCompareRoutes, setShowCompareRoutes, riskCmp, demoPlan,
    calculate, selectIncident, selectStation, recalculate, compare, compareRisk,
    handleRoadClick, demoBlockOnRoute, addIncident, resolveIncident, loadScenario,
    resetScenario, runDemo, notify,
  };
}
