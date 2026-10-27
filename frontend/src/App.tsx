import { AlertTriangle, CheckCircle2, Info, RefreshCw, X, XCircle } from "lucide-react";
import Header from "./components/Header";
import IncidentPanel from "./components/IncidentPanel";
import RescueMap from "./components/RescueMap";
import RouteAnalysis from "./components/RouteAnalysis";
import PerformanceDashboard from "./components/PerformanceDashboard";
import AlgorithmComparison from "./components/AlgorithmComparison";
import EventLog from "./components/EventLog";
import { useRescue } from "./hooks/useRescue";
import { API_BASE_URL } from "./services/api";

const TOAST = {
  info: { c: "#38bdf8", Icon: Info },
  success: { c: "#22c55e", Icon: CheckCircle2 },
  warning: { c: "#f59e0b", Icon: AlertTriangle },
  error: { c: "#ef4444", Icon: XCircle },
};

export default function App() {
  const r = useRescue();
  const { sim } = r;

  return (
    <div className="flex min-h-screen flex-col">
      <Header sim={sim} loading={r.loading} offline={!!r.error && !sim}
              onReset={() => r.resetScenario(true)} />

      {r.error && !sim && (
        <div id="backend-error" className="m-6 mx-auto max-w-xl rounded-xl border border-red-500/40 bg-red-950/40 p-5 text-sm">
          <h2 className="mb-1 flex items-center gap-2 font-semibold text-red-200"><XCircle size={16} /> Backend unavailable</h2>
          <p className="text-red-200/80">{r.error}</p>
          <p className="mt-2 text-xs text-slate-400">Expected API at <code>{API_BASE_URL}</code>. Set <code>VITE_API_BASE_URL</code> to change it.</p>
          <button className="btn mt-3" onClick={() => void r.refresh()}><RefreshCw size={13} /> Retry</button>
        </div>
      )}

      {sim && (
        <main className="flex flex-1 flex-col gap-3 p-3">
          <div className="grid min-h-[560px] gap-3 lg:h-[calc(100vh-56px-330px)] lg:min-h-[540px] lg:grid-cols-[300px_minmax(0,1fr)_320px]">
            <div className="min-h-0 max-lg:max-h-[640px]"><IncidentPanel r={r} /></div>
            <div className="min-h-[480px]"><RescueMap r={r} /></div>
            <div className="min-h-0 max-lg:max-h-[640px]"><RouteAnalysis r={r} /></div>
          </div>
          <div className="grid gap-3 lg:h-[300px] lg:grid-cols-[minmax(0,5fr)_minmax(0,4fr)_minmax(0,3fr)]">
            <PerformanceDashboard sim={sim} />
            <AlgorithmComparison data={r.comparison} />
            <EventLog events={sim.events} />
          </div>
          <p className="px-1 pb-1 text-center text-[10px] text-slate-600">
            Simulation and academic demonstration only. Road network, incidents and risk scores are simulated;
            not connected to real emergency systems.
          </p>
        </main>
      )}

      {r.toast && (
        <div key={r.toast.id} role="status" id="toast"
             className="fixed bottom-5 left-1/2 z-[2000] flex -translate-x-1/2 items-center gap-2 rounded-lg border bg-ink-900/95 px-4 py-2 text-sm text-slate-100 shadow-panel"
             style={{ borderColor: `${TOAST[r.toast.kind].c}88` }}>
          {(() => { const T = TOAST[r.toast.kind]; return <T.Icon size={15} style={{ color: T.c }} />; })()}
          {r.toast.text}
          <button aria-label="Dismiss" onClick={r.dismissToast} className="ml-2 text-slate-500 hover:text-slate-200"><X size={13} /></button>
        </div>
      )}
    </div>
  );
}
