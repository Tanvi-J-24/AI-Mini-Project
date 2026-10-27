import type {
  Algorithm, ComparisonResponse, MutationResponse, ScenarioSummary, SimState, Severity,
} from "../types";

export const API_BASE_URL: string =
  (import.meta.env?.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(
      `Backend unavailable at ${API_BASE_URL}. Start it with: uvicorn app.main:app --app-dir backend`,
      0,
    );
  }
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON body */
  }
  if (!res.ok) {
    const detail = (body as { detail?: unknown } | null)?.detail;
    let msg = `Request failed (${res.status})`;
    if (typeof detail === "string") msg = detail;
    else if (Array.isArray(detail))
      msg = detail.map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg}`).join("; ");
    throw new ApiError(msg, res.status);
  }
  return body as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  health: () => request<{ status: string }>("/api/health"),
  scenarios: () => request<{ scenarios: ScenarioSummary[]; current: string }>("/api/scenarios"),
  state: () => request<SimState>("/api/state"),
  loadScenario: (id: string) => post<MutationResponse>(`/api/scenarios/${id}/load`, { clear_metrics: false }),
  route: (p: { source: string; destination: string; algorithm: Algorithm; risk_weight: number;
               incident_id?: string; station_id?: string }) => post<MutationResponse>("/api/route", p),
  compare: (p: { source: string; destination: string; risk_weight: number; repeats?: number }) =>
    post<ComparisonResponse>("/api/compare", p),
  riskCompare: (p: { source: string; destination: string; risk_weight: number }) =>
    post<MutationResponse>("/api/risk-compare", p),
  blockRoad: (u: string, v: string) => post<MutationResponse>("/api/block-road", { u, v }),
  unblockRoad: (u: string, v: string) => post<MutationResponse>("/api/unblock-road", { u, v }),
  addIncident: (p: { node?: string; type?: string; severity?: Severity; people_affected?: number } = {}) =>
    post<MutationResponse>("/api/incidents", p),
  resolveIncident: (incident_id: string) => post<MutationResponse>("/api/resolve-incident", { incident_id }),
  replan: (p: { algorithm?: Algorithm; risk_weight?: number } = {}) => post<MutationResponse>("/api/replan", p),
  reset: (clear_metrics = false) => post<MutationResponse>("/api/reset", { clear_metrics }),
  demo: () => post<MutationResponse>("/api/demo"),
};
