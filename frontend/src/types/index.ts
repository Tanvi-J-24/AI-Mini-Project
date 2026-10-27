export type Algorithm = "astar" | "bfs" | "greedy";
export type Severity = "critical" | "high" | "medium" | "low";

export interface GraphNode { id: string; lat: number; lng: number }
export interface GraphEdge { id: string; u: string; v: string; travel_cost: number; risk: number }
export interface Station { id: string; name: string; node: string }
export interface BlockedRoad { id: string; u: string; v: string }

export interface PriorityInfo {
  priority: "Critical" | "High" | "Medium" | "Low" | "Resolved";
  level: number;
  score: number;
  in_queue: boolean;
  needs_alt_access: boolean;
  rules_fired: { id: string; description: string }[];
  reason: string;
}

export interface Incident {
  id: string;
  type: string;
  severity: Severity;
  people_affected: number;
  node: string;
  description: string;
  status: "Active" | "Resolved";
  priority: PriorityInfo;
  route_costs: Record<string, number | null>;
  best_cost: number | null;
  best_station: string | null;
  route_available: boolean;
}

export interface RouteResult {
  algorithm: Algorithm;
  algorithm_label: string;
  source: string;
  destination: string;
  success: boolean;
  path: string[];
  path_edges: string[];
  cost: number;
  travel_cost: number;
  risk_total: number;
  risk_weight: number;
  segments: number;
  nodes_explored: number;
  explored: string[];
  execution_time_ms: number;
  estimated_minutes: number | null;
  message: string;
  is_optimal?: boolean | null;
  timing_runs?: number;
}

export interface ActiveRoute {
  result: RouteResult;
  status: "valid" | "replanned" | "no_route" | "invalid";
  incident_id: string | null;
  station_id: string | null;
  previous_path: string[] | null;
  replan_count: number;
}

export interface AlgorithmMetric {
  algorithm: Algorithm;
  label: string;
  runs: number;
  successes: number;
  avg_time_ms: number | null;
  avg_nodes_explored: number | null;
  avg_cost: number | null;
}

export interface SimEvent {
  id: number;
  time: string;
  level: "info" | "success" | "warning" | "error";
  type: string;
  message: string;
}

export interface SimState {
  version: number;
  scenario: { id: string; name: string; description: string; seed: number };
  map_center: { lat: number; lng: number };
  graph: { nodes: GraphNode[]; edges: GraphEdge[] };
  stations: Station[];
  incidents: Incident[];
  blocked: BlockedRoad[];
  active_route: ActiveRoute | null;
  counts: {
    active_incidents: number;
    critical_incidents: number;
    resolved_incidents: number;
    blocked_roads: number;
    flagged_alt_access: number;
  };
  metrics: {
    total_runs: number;
    successful_routes: number;
    failed_routes: number;
    avg_path_cost: number | null;
    avg_nodes_explored: number | null;
    per_algorithm: AlgorithmMetric[];
  };
  events: SimEvent[];
  rules: { id: string; description: string }[];
}

export interface ScenarioSummary {
  id: string;
  name: string;
  description: string;
  seed: number;
  incident_count: number;
  blocked_count: number;
}

export interface MutationResponse {
  ok: boolean;
  message: string;
  state: SimState;
  route?: RouteResult | ActiveRoute | null;
  replan?: {
    triggered: boolean;
    success: boolean;
    previous_path?: string[] | null;
    new_path?: string[];
    message?: string;
    reason?: string;
  } | null;
  extra?: Record<string, unknown> | null;
}

export interface ComparisonResponse {
  source: string;
  destination: string;
  risk_weight: number;
  repeats: number;
  optimal_cost: number | null;
  results: RouteResult[];
  notes: string[];
  state: SimState;
}

export interface RiskComparison {
  shortest: RouteResult;
  risk_aware: RouteResult;
  risk_weight: number;
  note: string;
}

export interface DemoPlanItem {
  incident_id: string;
  priority: string;
  station_id: string | null;
  success: boolean;
  cost: number | null;
  path: string[];
}
