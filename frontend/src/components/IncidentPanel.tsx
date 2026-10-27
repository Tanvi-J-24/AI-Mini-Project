import {
  AlertTriangle, Building2, CheckCircle2, Flame, Waves, Activity, Plus, Minus, RefreshCw, RotateCcw,
  Siren, Play,
} from "lucide-react";
import type { useRescue } from "../hooks/useRescue";
import { PRIORITY_COLOR, SEVERITY_COLOR, fmt } from "../utils/format";

type R = ReturnType<typeof useRescue>;

const SCENARIOS = [
  { id: "flood", label: "Flood", Icon: Waves },
  { id: "fire", label: "Urban Fire", Icon: Flame },
  { id: "earthquake", label: "Earthquake", Icon: Activity },
];

export default function IncidentPanel({ r }: { r: R }) {
  const { sim } = r;
  if (!sim) return <aside className="panel p-4 text-sm text-slate-500">Loading simulation…</aside>;

  return (
    <aside className="flex h-full min-h-0 flex-col gap-3 overflow-y-auto pr-1" aria-label="Incident and control panel">
      {/* Scenario selector */}
      <section className="panel p-3">
        <h2 className="panel-title mb-2">Disaster scenario</h2>
        <div className="grid grid-cols-3 gap-1.5">
          {SCENARIOS.map(({ id, label, Icon }) => (
            <button key={id} id={`scenario-${id}`} onClick={() => r.loadScenario(id)}
                    className={`btn flex-col gap-1 py-2 ${sim.scenario.id === id ? "btn-active" : ""}`}>
              <Icon size={16} /> {label}
            </button>
          ))}
        </div>
        <p className="mt-2 text-[11px] leading-snug text-slate-500">{sim.scenario.description}</p>
      </section>

      {/* Station selector */}
      <section className="panel p-3">
        <h2 className="panel-title mb-2">Rescue station</h2>
        <div className="space-y-1.5" role="radiogroup" aria-label="Rescue station">
          {sim.stations.map((s) => {
            const sel = r.selectedStationId === s.id;
            return (
              <button key={s.id} id={`station-${s.id}`} role="radio" aria-checked={sel}
                      onClick={() => r.selectStation(s.id)}
                      className={`flex w-full items-center gap-2 rounded-lg border px-2.5 py-1.5 text-left text-xs transition
                        ${sel ? "border-emerald-400/60 bg-emerald-500/10" : "border-white/[0.07] bg-ink-900/40 hover:border-white/20"}`}>
                <Building2 size={14} className={sel ? "text-emerald-400" : "text-slate-500"} />
                <span className="font-semibold text-slate-100">{s.id}</span>
                <span className="truncate text-slate-400">{s.name}</span>
                <span className="ml-auto font-mono text-[10px] text-slate-500">{s.node}</span>
              </button>
            );
          })}
        </div>
      </section>

      {/* Simulation controls */}
      <section className="panel p-3">
        <h2 className="panel-title mb-2">Simulation controls</h2>
        <div className="grid grid-cols-2 gap-1.5">
          <button id="btn-add-block" className={`btn ${r.edgeTool === "block" ? "btn-active" : ""}`}
                  onClick={() => r.setEdgeTool(r.edgeTool === "block" ? "none" : "block")}
                  title="Then click a road on the map to block it">
            <Plus size={13} /> Add blockage
          </button>
          <button id="btn-remove-block" className={`btn ${r.edgeTool === "unblock" ? "btn-active" : ""}`}
                  onClick={() => r.setEdgeTool(r.edgeTool === "unblock" ? "none" : "unblock")}
                  title="Then click a blocked road on the map to restore it">
            <Minus size={13} /> Remove blockage
          </button>
          <button id="btn-new-incident" className="btn" onClick={() => r.addIncident()}>
            <Siren size={13} /> New incident
          </button>
          <button id="btn-recalculate" className="btn btn-primary" onClick={() => r.recalculate()}>
            <RefreshCw size={13} /> Recalculate
          </button>
          <button id="btn-demo" className="btn" onClick={() => r.runDemo()}
                  title="Dispatch the best station to every active incident in priority order">
            <Play size={13} /> Multi-incident demo
          </button>
          <button id="btn-reset-scenario" className="btn" onClick={() => r.resetScenario(false)}>
            <RotateCcw size={13} /> Reset scenario
          </button>
        </div>
        <p className="mt-2 text-[11px] text-slate-500">
          {r.edgeTool === "block" && "Block mode: click a road on the map."}
          {r.edgeTool === "unblock" && "Restore mode: click a red blocked road."}
          {r.edgeTool === "none" && "Tip: click any road on the map to toggle its blockage."}
        </p>
      </section>

      {/* Incident list */}
      <section className="panel flex min-h-[220px] flex-1 flex-col p-3">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="panel-title">Incident queue</h2>
          <span className="font-mono text-[11px] text-slate-500">{sim.counts.active_incidents} active</span>
        </div>
        <ul className="min-h-0 flex-1 space-y-1.5 overflow-y-auto" aria-label="Incidents">
          {sim.incidents.map((inc) => {
            const sel = r.selectedIncidentId === inc.id;
            const resolved = inc.status === "Resolved";
            const color = PRIORITY_COLOR[inc.priority.priority];
            return (
              <li key={inc.id}>
                <div id={`incident-${inc.id}`} role="button" tabIndex={0} aria-pressed={sel}
                     onClick={() => !resolved && r.selectIncident(inc.id)}
                     onKeyDown={(e) => e.key === "Enter" && !resolved && r.selectIncident(inc.id)}
                     className={`w-full cursor-pointer rounded-lg border p-2 text-left transition
                      ${sel ? "border-cyanx-400/70 bg-cyanx-500/10" : "border-white/[0.07] bg-ink-900/40 hover:border-white/20"}
                      ${resolved ? "opacity-50" : ""}`}>
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: SEVERITY_COLOR[inc.severity] }} />
                    <span className="font-mono text-xs font-semibold text-slate-100">{inc.id}</span>
                    <span className="truncate text-xs text-slate-300">{inc.type}</span>
                    <span className="ml-auto rounded px-1.5 py-0.5 text-[10px] font-semibold"
                          style={{ color, background: `${color}22` }}>{inc.priority.priority}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-slate-500">
                    <span>Severity <b className="font-medium capitalize text-slate-300">{inc.severity}</b></span>
                    <span>{inc.people_affected} people</span>
                    <span>Node <b className="font-mono font-medium text-slate-300">{inc.node}</b></span>
                    <span className={resolved ? "text-emerald-400" : "text-slate-400"}>{inc.status}</span>
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[11px]">
                    {resolved ? (
                      <span className="flex items-center gap-1 text-emerald-400"><CheckCircle2 size={12} /> Resolved</span>
                    ) : inc.route_available ? (
                      <span className="text-slate-400">
                        Est. cost <b className="font-mono text-cyanx-300">{fmt(inc.best_cost)}</b>
                        {inc.best_station && <> via {inc.best_station}</>}
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-amber-300"><AlertTriangle size={12} /> No route – plan alternative access</span>
                    )}
                    {sel && !resolved && (
                      <button className="btn ml-auto px-2 py-0.5 text-[10px]" id={`resolve-${inc.id}`}
                              onClick={(e) => { e.stopPropagation(); void r.resolveIncident(inc.id); }}>
                        <CheckCircle2 size={11} /> Resolve
                      </button>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
          {sim.incidents.length === 0 && <li className="text-xs text-slate-500">No incidents.</li>}
        </ul>
      </section>
    </aside>
  );
}

