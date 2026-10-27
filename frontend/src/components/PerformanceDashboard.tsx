import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AlertTriangle, CheckCircle2, Construction, Flame, Gauge, Navigation, Network, Siren } from "lucide-react";
import type { SimState } from "../types";
import { ALG_COLOR, fmt } from "../utils/format";

const METRICS = [
  { key: "avg_time_ms", label: "Avg execution time (ms)" },
  { key: "avg_nodes_explored", label: "Avg nodes explored" },
  { key: "avg_cost", label: "Avg path cost" },
] as const;

function Card({ label, value, Icon, color, id }: { label: string; value: React.ReactNode; Icon: typeof Flame; color: string; id: string }) {
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-white/[0.06] bg-ink-900/50 px-2.5 py-2">
      <div className="rounded-md p-1.5" style={{ background: `${color}1f`, color }}><Icon size={15} /></div>
      <div>
        <div id={id} className="font-mono text-base font-semibold leading-none text-slate-100">{value}</div>
        <div className="stat-label mt-1">{label}</div>
      </div>
    </div>
  );
}

export default function PerformanceDashboard({ sim }: { sim: SimState }) {
  const [metric, setMetric] = useState<(typeof METRICS)[number]["key"]>("avg_time_ms");
  const c = sim.counts;
  const m = sim.metrics;
  const data = m.per_algorithm.map((a) => ({
    name: a.algorithm === "astar" ? "A*" : a.algorithm === "bfs" ? "BFS" : "Greedy",
    key: a.algorithm, value: a[metric] ?? 0, runs: a.runs,
  }));
  const hasData = m.total_runs > 0;

  return (
    <section className="panel flex h-full min-h-0 flex-col p-3" id="dashboard" aria-label="Performance dashboard">
      <h2 className="panel-title mb-2">Operations &amp; performance dashboard</h2>
      <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
        <Card id="m-active" label="Active incidents" value={c.active_incidents} Icon={Siren} color="#38bdf8" />
        <Card id="m-critical" label="Critical incidents" value={c.critical_incidents} Icon={Flame} color="#ef4444" />
        <Card id="m-blocked" label="Blocked roads" value={c.blocked_roads} Icon={Construction} color="#f59e0b" />
        <Card id="m-resolved" label="Resolved incidents" value={c.resolved_incidents} Icon={CheckCircle2} color="#22c55e" />
        <Card id="m-success" label="Successful routes" value={m.successful_routes} Icon={Navigation} color="#22d3ee" />
        <Card id="m-failed" label="Failed searches" value={m.failed_routes} Icon={AlertTriangle} color="#f87171" />
        <Card id="m-avgcost" label="Avg path cost" value={fmt(m.avg_path_cost)} Icon={Gauge} color="#a78bfa" />
        <Card id="m-avgnodes" label="Avg nodes explored" value={fmt(m.avg_nodes_explored, 1)} Icon={Network} color="#fbbf24" />
      </div>
      <div className="mt-2 flex items-center gap-1.5">
        {METRICS.map((x) => (
          <button key={x.key} className={`btn px-2 py-0.5 text-[10px] ${metric === x.key ? "btn-active" : ""}`}
                  onClick={() => setMetric(x.key)}>{x.label}</button>
        ))}
      </div>
      <div className="mt-1 min-h-[90px] flex-1" id="dashboard-chart">
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
              <CartesianGrid stroke="#1e2f4a" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "#0f1b2e", border: "1px solid #203551", fontSize: 11 }}
                       cursor={{ fill: "rgba(255,255,255,0.04)" }}
                       formatter={(v: number, _n, p) => [`${v} (${(p.payload as { runs: number }).runs} runs)`, "Average"]} />
              <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                {data.map((d) => <Cell key={d.key} fill={ALG_COLOR[d.key]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-slate-500">
            No algorithm runs yet. Calculate a route; charts use only measured results from real executions.
          </div>
        )}
      </div>
    </section>
  );
}
