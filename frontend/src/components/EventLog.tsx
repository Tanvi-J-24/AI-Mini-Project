import type { SimEvent } from "../types";
import { formatTime } from "../utils/format";

const COLOR: Record<SimEvent["level"], string> = {
  info: "#38bdf8", success: "#22c55e", warning: "#f59e0b", error: "#ef4444",
};

export default function EventLog({ events }: { events: SimEvent[] }) {
  return (
    <section className="panel flex h-full min-h-0 flex-col p-3" id="event-log">
      <h2 className="panel-title mb-2">Event log</h2>
      <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto font-mono text-[11px]">
        {events.map((e) => (
          <li key={e.id} className="flex gap-2 leading-snug">
            <span className="shrink-0 text-slate-600">{formatTime(e.time)}</span>
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: COLOR[e.level] }} />
            <span className="text-slate-300">{e.message}</span>
          </li>
        ))}
        {events.length === 0 && <li className="text-slate-500">No events yet.</li>}
      </ul>
    </section>
  );
}
