import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Check, Minus, X } from "lucide-react";
import type { ComparisonResponse } from "../types";
import { ALG_COLOR, ALG_LABEL, fmt } from "../utils/format";

export default function AlgorithmComparison({ data }: { data: ComparisonResponse | null }) {
  if (!data) {
    return (
      <section className="panel flex h-full flex-col p-3" id="comparison-panel">
        <h2 className="panel-title mb-2">Algorithm comparison</h2>
        <p className="text-xs text-slate-500">
          Select a station and an incident, then press <b>Run algorithm comparison</b>. BFS, Greedy Best-First
          and A* run on the same graph, endpoints and blockages; results are measured, not pre-set.
        </p>
      </section>
    );
  }
  const chart = data.results.map((r) => ({
    name: r.algorithm === "astar" ? "A*" : r.algorithm === "bfs" ? "BFS" : "Greedy",
    key: r.algorithm, nodes: r.nodes_explored, cost: r.success ? r.cost : 0,
  }));
  return (
    <section className="panel flex h-full min-h-0 flex-col overflow-y-auto p-3" id="comparison-panel">
      <h2 className="panel-title mb-2">
        Algorithm comparison <span className="ml-1 font-mono normal-case text-slate-500">{data.source} → {data.destination}</span>
      </h2>
      <table className="w-full text-left text-[11px]" id="comparison-table">
        <thead className="text-slate-500">
          <tr><th className="pb-1">Algorithm</th><th>Found</th><th>Cost</th><th>Segs</th><th>Nodes</th><th>Time (ms)</th><th>Optimal</th></tr>
        </thead>
        <tbody className="font-mono text-slate-200">
          {data.results.map((r) => (
            <tr key={r.algorithm} className="border-t border-white/5">
              <td className="py-1 font-sans font-medium" style={{ color: ALG_COLOR[r.algorithm] }}>{ALG_LABEL[r.algorithm]}</td>
              <td>{r.success ? <Check size={13} className="text-emerald-400" /> : <X size={13} className="text-red-400" />}</td>
              <td>{r.success ? fmt(r.cost, 3) : "–"}</td>
              <td>{r.success ? r.segments : "–"}</td>
              <td>{r.nodes_explored}</td>
              <td>{fmt(r.execution_time_ms, 4)}</td>
              <td>{r.is_optimal === null || r.is_optimal === undefined ? <Minus size={13} className="text-slate-500" />
                : r.is_optimal ? <span className="text-emerald-400">Yes</span> : <span className="text-amber-400">No</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-2 h-24">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chart} margin={{ top: 4, right: 4, left: -22, bottom: 0 }}>
            <CartesianGrid stroke="#1e2f4a" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} allowDecimals={false} />
            <Tooltip contentStyle={{ background: "#0f1b2e", border: "1px solid #203551", fontSize: 11 }} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
            <Bar dataKey="nodes" name="Nodes explored" radius={[3, 3, 0, 0]}>
              {chart.map((c) => <Cell key={c.key} fill={ALG_COLOR[c.key]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-[10px] leading-snug text-slate-500">
        Chart: nodes explored. Time is the median of {data.repeats} runs; on a graph this small, timing
        differences are dominated by measurement noise. BFS minimises segments (not cost); Greedy is not
        guaranteed optimal; A* is optimal here (admissible heuristic).
      </p>
    </section>
  );
}
