import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

const Line = ({ color, dash, w = 4 }: { color: string; dash?: string; w?: number }) => (
  <svg width="28" height="10" aria-hidden>
    <line x1="1" y1="5" x2="27" y2="5" stroke={color} strokeWidth={w} strokeDasharray={dash} strokeLinecap="round" />
  </svg>
);
const Dot = ({ color, ring }: { color: string; ring?: boolean }) => (
  <svg width="28" height="14" aria-hidden>
    <circle cx="14" cy="7" r="5" fill={color} stroke={ring ? "#fff" : "none"} strokeWidth="1.5" />
  </svg>
);
const Square = ({ color }: { color: string }) => (
  <svg width="28" height="14" aria-hidden>
    <rect x="9" y="2" width="10" height="10" rx="2" fill={color} stroke="#052e16" />
  </svg>
);

export default function MapLegend() {
  const [open, setOpen] = useState(true);
  const rows: [React.ReactNode, string][] = [
    [<Line color="#22d3ee" w={6} />, "Selected route"],
    [<Line color="#fb923c" dash="5 5" />, "Previous route (before replan)"],
    [<Line color="#a78bfa" dash="2 6" w={5} />, "BFS route (comparison)"],
    [<Line color="#fbbf24" dash="9 5" w={5} />, "Greedy route (comparison)"],
    [<Line color="#4ade80" w={4} dash="1 7" />, "Risk-aware route"],
    [<Line color="#ef4444" dash="6 5" w={5} />, "Blocked road"],
    [<Line color="#64748b" w={3} />, "Open road"],
    [<Dot color="#ef4444" />, "Critical incident"],
    [<Dot color="#f97316" />, "High incident"],
    [<Dot color="#f59e0b" />, "Medium incident"],
    [<Dot color="#22c55e" />, "Low incident"],
    [<Dot color="#22c55e" ring />, "Resolved incident"],
    [<Square color="#34d399" />, "Rescue station"],
  ];
  return (
    <div id="map-legend" className="panel absolute bottom-3 right-3 z-[1000] w-52 p-2.5 text-[11px]">
      <button className="flex w-full items-center justify-between" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="panel-title">Legend</span>
        {open ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
      </button>
      {open && (
        <ul className="mt-2 space-y-0.5">
          {rows.map(([sym, label], i) => (
            <li key={i} className="flex items-center gap-2 text-slate-300">{sym}{label}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
