import { Activity, Loader2, RotateCcw, WifiOff } from "lucide-react";
import type { SimState } from "../types";

export function LogoMark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-label="RescueRoute AI logo">
      <rect width="32" height="32" rx="8" fill="#0f1b2e" stroke="#22d3ee" strokeOpacity="0.5" />
      <path d="M7 24 L13 12 L19 19 L25 8" fill="none" stroke="#22d3ee" strokeWidth="2.6"
            strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="7" cy="24" r="3" fill="#22c55e" />
      <circle cx="25" cy="8" r="3" fill="#ef4444" />
    </svg>
  );
}

interface Props {
  sim: SimState | null;
  loading: boolean;
  offline: boolean;
  onReset: () => void;
}

export default function Header({ sim, loading, offline, onReset }: Props) {
  const status = offline
    ? { text: "Backend offline", color: "text-red-400", dot: "bg-red-500", Icon: WifiOff }
    : loading
    ? { text: "Processing", color: "text-amber-300", dot: "bg-amber-400", Icon: Loader2 }
    : { text: "Simulation live", color: "text-emerald-300", dot: "bg-emerald-400", Icon: Activity };

  return (
    <header className="sticky top-0 z-[1100] flex h-14 items-center gap-4 border-b border-white/[0.07] bg-ink-900/95 px-4 backdrop-blur">
      <div className="flex items-center gap-3">
        <LogoMark />
        <div className="leading-tight">
          <h1 className="text-[15px] font-bold tracking-tight text-white">
            RescueRoute <span className="text-cyanx-400">AI</span>
          </h1>
          <p className="hidden text-[11px] text-slate-400 md:block">
            Intelligent Disaster Response &amp; Route Optimization
          </p>
        </div>
      </div>

      <div className="ml-auto flex items-center gap-3">
        <div id="sim-status" className={`flex items-center gap-2 rounded-full border border-white/10 bg-ink-800 px-3 py-1 text-xs ${status.color}`}>
          <span className="relative flex h-2 w-2">
            <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${status.dot}`} />
            <span className={`relative inline-flex h-2 w-2 rounded-full ${status.dot}`} />
          </span>
          <status.Icon size={13} className={loading && !offline ? "animate-spin" : ""} />
          {status.text}
        </div>
        <div className="hidden items-center gap-2 rounded-lg border border-white/10 bg-ink-800 px-3 py-1 text-xs sm:flex">
          <span className="text-slate-500">Scenario</span>
          <span id="scenario-name" className="font-semibold text-slate-100">{sim?.scenario.name ?? "–"}</span>
        </div>
        <button id="btn-reset-sim" className="btn btn-danger" onClick={onReset} disabled={!sim}
                title="Restore the scenario and clear metrics and the event log">
          <RotateCcw size={13} /> Reset simulation
        </button>
      </div>
    </header>
  );
}
