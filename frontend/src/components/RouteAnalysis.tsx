import { AlertOctagon, CheckCircle2, GitCompare, Navigation, RefreshCw, ShieldAlert, XCircle, Zap } from "lucide-react";
import type { useRescue } from "../hooks/useRescue";
import type { Algorithm } from "../types";
import { ALG_LABEL, PRIORITY_COLOR, fmt } from "../utils/format";

type R = ReturnType<typeof useRescue>;

const ALGS: Algorithm[] = ["astar", "bfs", "greedy"];

function Stat({ label, value, id, accent }: { label: string; value: React.ReactNode; id?: string; accent?: string }) {
  return (
    <div className="rounded-lg border border-white/[0.06] bg-ink-900/50 px-2.5 py-1.5">
      <div className="stat-label">{label}</div>
      <div id={id} className="stat-value" style={accent ? { color: accent } : undefined}>{value}</div>
    </div>
  );
}

export default function RouteAnalysis({ r }: { r: R }) {
  const { sim } = r;
  if (!sim) return <aside className="panel p-4 text-sm text-slate-500">Loading…</aside>;

  const active = sim.active_route;
  const res = active?.result;
  const inc = r.selectedIncident;
  const st = r.selectedStation;
  const ok = !!res?.success && active?.status !== "invalid";
  const status = !active ? { text: "No route calculated", color: "#94a3b8", Icon: Navigation }
    : ok ? { text: active.status === "replanned" ? "Route replanned" : "Route valid", color: active.status === "replanned" ? "#fb923c" : "#22c55e", Icon: CheckCircle2 }
    : { text: "No safe route available", color: "#ef4444", Icon: XCircle };

  return (
    <aside className="flex h-full min-h-0 flex-col gap-3 overflow-y-auto pr-1" aria-label="Route analysis">
      <section className="panel p-3">
        <h2 className="panel-title mb-2">Route analysis</h2>
        <div id="route-status" className="mb-2 flex items-center gap-2 rounded-lg border px-2.5 py-2 text-sm font-semibold"
             style={{ color: status.color, borderColor: `${status.color}55`, background: `${status.color}12` }}>
          <status.Icon size={16} /> {status.text}
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          <Stat label="Station" value={st ? `${st.id} · ${st.node}` : "–"} id="ra-station" />
          <Stat label="Destination" value={inc ? `${inc.id} · ${inc.node}` : "–"} id="ra-destination" />
          <Stat label="Algorithm" value={res ? ALG_LABEL[res.algorithm] : ALG_LABEL[r.algorithm]} id="ra-algorithm" />
          <Stat label="Success" value={res ? (res.success ? "Yes" : "No") : "–"} id="ra-success"
                accent={res ? (res.success ? "#4ade80" : "#f87171") : undefined} />
          <Stat label="Total path cost" value={res?.success ? fmt(res.cost, 3) : "–"} id="ra-cost" />
          <Stat label="Route segments" value={res?.success ? res.segments : "–"} id="ra-segments" />
          <Stat label="Nodes explored" value={res ? res.nodes_explored : "–"} id="ra-nodes" />
          <Stat label="Execution time" value={res ? `${fmt(res.execution_time_ms, 3)} ms` : "–"} id="ra-time" />
        </div>
        <div className="mt-1.5 rounded-lg border border-white/[0.06] bg-ink-900/50 px-2.5 py-1.5">
          <div className="stat-label">Estimated travel time (simulation estimate)</div>
          <div id="ra-eta" className="stat-value">
            {res?.success && res.estimated_minutes !== null ? `${fmt(res.estimated_minutes, 1)} min` : "–"}
            <span className="ml-2 text-[10px] font-normal text-slate-500">assumes 40 km/h</span>
          </div>
        </div>

        {res?.success && (
          <div className="mt-2">
            <div className="stat-label mb-1">Ordered waypoints</div>
            <ol id="waypoints" className="flex flex-wrap items-center gap-1 font-mono text-[11px]">
              {res.path.map((n, i) => (
                <li key={`${n}-${i}`} className="flex items-center gap-1">
                  <span className={`rounded px-1.5 py-0.5 ${i === 0 ? "bg-emerald-500/20 text-emerald-300" : i === res.path.length - 1 ? "bg-red-500/20 text-red-300" : "bg-ink-700 text-slate-300"}`}>{n}</span>
                  {i < res.path.length - 1 && <span className="text-slate-600">›</span>}
                </li>
              ))}
            </ol>
          </div>
        )}

        {active?.status === "replanned" && (
          <div id="replan-banner" className="mt-2 rounded-lg border border-orange-400/40 bg-orange-500/10 p-2 text-[11px] text-orange-200">
            <b>Dynamic replan:</b> a road on the route was blocked and A* found a new route
            ({active.replan_count}×). Previous route shown dashed orange.
            {active.previous_path && <div className="mt-1 font-mono text-orange-300/80">Was: {active.previous_path.join(" › ")}</div>}
          </div>
        )}
        {active && !ok && (
          <div className="mt-2 flex items-start gap-2 rounded-lg border border-red-500/40 bg-red-500/10 p-2 text-[11px] text-red-200">
            <AlertOctagon size={14} className="mt-0.5 shrink-0" />
            No path exists with the current road blockages. The incident is flagged for alternative access
            planning; unblock a road or choose another station.
          </div>
        )}
      </section>

      <section className="panel p-3">
        <h2 className="panel-title mb-2">Algorithm &amp; mode</h2>
        <div className="grid grid-cols-3 gap-1.5" role="radiogroup" aria-label="Algorithm">
          {ALGS.map((a) => (
            <button key={a} id={`alg-${a}`} role="radio" aria-checked={r.algorithm === a}
                    className={`btn ${r.algorithm === a ? "btn-active" : ""}`} onClick={() => r.setAlgorithm(a)}>
              {a === "astar" ? "A*" : a === "bfs" ? "BFS" : "Greedy"}
            </button>
          ))}
        </div>
        <label className="mt-3 block text-[11px] text-slate-400" htmlFor="risk-weight">
          Risk weight: <b id="risk-weight-value" className="font-mono text-slate-200">{r.riskWeight.toFixed(1)}</b>
          <span className="ml-1 text-slate-500">(0 = shortest cost)</span>
        </label>
        <input id="risk-weight" type="range" min={0} max={10} step={0.5} value={r.riskWeight}
               onChange={(e) => r.setRiskWeight(Number(e.target.value))} className="w-full accent-cyan-400" />
        <p className="mt-1 text-[10px] leading-snug text-slate-500">
          edge cost = travel cost + risk weight × risk score. Risk scores are simulated, not real hazard data.
        </p>

        <div className="mt-3 grid grid-cols-2 gap-1.5">
          <button id="btn-calc" className="btn btn-primary" onClick={() => r.calculate()}>
            <Navigation size={13} /> Calculate route
          </button>
          <button id="btn-recalc-2" className="btn" onClick={() => r.recalculate()}>
            <RefreshCw size={13} /> Recalculate
          </button>
          <button id="btn-compare" className="btn col-span-2" onClick={() => r.compare()}>
            <GitCompare size={13} /> Run algorithm comparison
          </button>
          <button id="btn-risk-compare" className="btn col-span-2" onClick={() => r.compareRisk()}>
            <ShieldAlert size={13} /> Compare shortest vs risk-aware
          </button>
          <button id="btn-demo-replan" className="btn btn-danger col-span-2" onClick={() => r.demoBlockOnRoute()}
                  title="Blocks the middle road segment of the active route to demonstrate automatic replanning">
            <Zap size={13} /> Demo: block a road on this route
          </button>
        </div>
      </section>

      {r.riskCmp && (
        <section id="risk-compare-card" className="panel p-3 text-[11px]">
          <h2 className="panel-title mb-2">Shortest vs risk-aware (weight {r.riskCmp.risk_weight})</h2>
          <table className="w-full text-left">
            <thead className="text-slate-500"><tr><th></th><th>Travel</th><th>Risk</th><th>Segs</th></tr></thead>
            <tbody className="font-mono text-slate-200">
              <tr><td className="text-cyanx-300">Shortest</td><td>{fmt(r.riskCmp.shortest.travel_cost)}</td><td>{fmt(r.riskCmp.shortest.risk_total)}</td><td>{r.riskCmp.shortest.segments}</td></tr>
              <tr><td className="text-emerald-300">Risk-aware</td><td>{fmt(r.riskCmp.risk_aware.travel_cost)}</td><td>{fmt(r.riskCmp.risk_aware.risk_total)}</td><td>{r.riskCmp.risk_aware.segments}</td></tr>
            </tbody>
          </table>
          <p className="mt-1.5 text-slate-500">{r.riskCmp.note}</p>
        </section>
      )}

      {r.demoPlan && (
        <section id="demo-plan" className="panel p-3 text-[11px]">
          <h2 className="panel-title mb-2">Multi-incident dispatch plan</h2>
          <ul className="space-y-1">
            {r.demoPlan.map((p, i) => (
              <li key={p.incident_id} className="flex items-center gap-2 font-mono">
                <span className="text-slate-500">{i + 1}.</span>
                <span className="text-slate-200">{p.incident_id}</span>
                <span style={{ color: PRIORITY_COLOR[p.priority] }}>{p.priority}</span>
                <span className="ml-auto text-slate-400">
                  {p.success ? `${p.station_id} · cost ${fmt(p.cost)}` : <span className="text-red-400">no route</span>}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-1.5 text-slate-500">Stations are assumed to have unlimited capacity.</p>
        </section>
      )}
    </aside>
  );
}
