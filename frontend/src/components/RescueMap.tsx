import { useEffect, useMemo, useRef, useState } from "react";
import { CircleMarker, MapContainer, Marker, Polyline, TileLayer, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import { Grid3x3, Layers, Loader2, Maximize2 } from "lucide-react";
import type { useRescue } from "../hooks/useRescue";
import type { GraphNode, Incident } from "../types";
import { ALG_COLOR, PRIORITY_COLOR, SEVERITY_COLOR, fmt } from "../utils/format";
import MapLegend from "./MapLegend";

type R = ReturnType<typeof useRescue>;
type LL = [number, number];

function FitController({ points, signal }: { points: LL[]; signal: string }) {
  const map = useMap();
  const last = useRef("");
  useEffect(() => {
    if (!points.length || last.current === signal) return;
    last.current = signal;
    map.fitBounds(L.latLngBounds(points), { padding: [40, 40] });
  }, [map, points, signal]);
  return null;
}

function FitButton({ points }: { points: LL[] }) {
  const map = useMap();
  return (
    <button id="btn-fit" className="btn bg-ink-800/90" onClick={() => map.fitBounds(L.latLngBounds(points), { padding: [40, 40] })}>
      <Maximize2 size={13} /> Fit scenario
    </button>
  );
}

const incidentIcon = (inc: Incident, selected: boolean) => {
  const resolved = inc.status === "Resolved";
  const color = resolved ? "#22c55e" : SEVERITY_COLOR[inc.severity];
  const pulse = !resolved && inc.severity === "critical"
    ? `<circle cx="20" cy="20" r="11" fill="${color}" class="marker-pulse"/>` : "";
  const ring = selected ? `<circle cx="20" cy="20" r="16" fill="none" stroke="#22d3ee" stroke-width="2.5"/>` : "";
  const glyph = resolved
    ? `<path d="M15 20.5l3.5 3.5 7-8" stroke="#fff" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`
    : `<path d="M20 14v7M20 24.5v.5" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/>`;
  return L.divIcon({
    className: "",
    iconSize: [40, 40],
    iconAnchor: [20, 20],
    html: `<svg width="40" height="40" viewBox="0 0 40 40">${pulse}${ring}
      <circle cx="20" cy="20" r="10.5" fill="${color}" stroke="#0a1220" stroke-width="2"/>${glyph}</svg>`,
  });
};

const stationIcon = (id: string, selected: boolean) =>
  L.divIcon({
    className: "",
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    html: `<div style="width:34px;height:34px;border-radius:9px;background:#059669;border:2px solid ${selected ? "#fff" : "#064e3b"};
      box-shadow:0 0 ${selected ? "14px 3px rgba(52,211,153,.7)" : "6px rgba(0,0,0,.6)"};display:flex;align-items:center;justify-content:center;
      color:#ecfdf5;font:700 11px Inter,sans-serif">${id}</div>`,
  });

const waypointIcon = (n: number) =>
  L.divIcon({
    className: "",
    iconSize: [18, 18],
    iconAnchor: [9, 9],
    html: `<div style="width:18px;height:18px;border-radius:9999px;background:#0a1220;border:2px solid #22d3ee;color:#67e8f9;
      font:600 10px 'JetBrains Mono',monospace;display:flex;align-items:center;justify-content:center">${n}</div>`,
  });

export default function RescueMap({ r }: { r: R }) {
  const { sim } = r;
  const [mode, setMode] = useState<"map" | "schematic">("map");
  const tileErrors = useRef(0);

  const nodeMap = useMemo(() => {
    const m = new Map<string, GraphNode>();
    sim?.graph.nodes.forEach((n) => m.set(n.id, n));
    return m;
  }, [sim?.graph.nodes]);

  const pos = (id: string): LL => {
    const n = nodeMap.get(id)!;
    return [n.lat, n.lng];
  };
  const pathPts = (path: string[] | null | undefined): LL[] =>
    (path ?? []).filter((id) => nodeMap.has(id)).map(pos);

  const allPoints = useMemo<LL[]>(
    () => sim?.graph.nodes.map((n) => [n.lat, n.lng] as LL) ?? [],
    [sim?.graph.nodes],
  );

  if (!sim) {
    return <div className="panel flex h-full items-center justify-center text-sm text-slate-500">Waiting for backend…</div>;
  }

  const blockedIds = new Set(sim.blocked.map((b) => b.id));
  const active = sim.active_route;
  const res = active?.result;
  const routeOk = !!res?.success && (active?.status === "valid" || active?.status === "replanned");
  const routePath = routeOk ? res!.path : [];
  const stationNodes = new Set(sim.stations.map((s) => s.node));
  const incidentNodes = new Set(sim.incidents.map((i) => i.node));

  return (
    <div className={`relative h-full min-h-[420px] overflow-hidden rounded-xl border border-white/[0.07] shadow-panel
        ${mode === "schematic" ? "schematic" : "dark-tiles"}
        ${r.edgeTool !== "none" ? "[&_.leaflet-interactive]:cursor-crosshair" : ""}`}
         id="rescue-map">
      <MapContainer center={[sim.map_center.lat, sim.map_center.lng]} zoom={15} className="h-full w-full" zoomControl>
        {mode === "map" && (
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            eventHandlers={{
              tileerror: () => {
                tileErrors.current += 1;
                if (tileErrors.current === 4) {
                  setMode("schematic");
                  r.notify("Map tiles unavailable – switched to schematic grid.", "warning");
                }
              },
            }}
          />
        )}
        <FitController points={allPoints} signal={sim.scenario.id} />

        {/* Open roads */}
        {sim.graph.edges.map((e) =>
          blockedIds.has(e.id) ? null : (
            <Polyline key={`r-${e.id}`} positions={[pos(e.u), pos(e.v)]} interactive={false}
                      pathOptions={{ color: "#64748b", weight: 3, opacity: 0.85 }} />
          ),
        )}

        {/* Comparison routes */}
        {r.comparison && r.showCompareRoutes &&
          r.comparison.results.filter((x) => x.success && x.algorithm !== "astar").map((x) => (
            <Polyline key={`c-${x.algorithm}`} positions={pathPts(x.path)} interactive={false}
                      pathOptions={{ color: ALG_COLOR[x.algorithm], weight: 8, opacity: 0.55,
                                     dashArray: x.algorithm === "bfs" ? "2 9" : "10 7", lineCap: "round" }} />
          ))}

        {/* Risk comparison */}
        {r.riskCmp && (
          <>
            <Polyline positions={pathPts(r.riskCmp.shortest.path)} interactive={false}
                      pathOptions={{ color: "#22d3ee", weight: 8, opacity: 0.35 }} />
            <Polyline positions={pathPts(r.riskCmp.risk_aware.path)} interactive={false}
                      pathOptions={{ color: "#4ade80", weight: 5, opacity: 0.95, dashArray: "1 8", lineCap: "round" }} />
          </>
        )}

        {/* Previous route */}
        {active?.status === "replanned" && active.previous_path && (
          <Polyline positions={pathPts(active.previous_path)} interactive={false}
                    pathOptions={{ color: "#fb923c", weight: 5, opacity: 0.85, dashArray: "6 6" }} />
        )}

        {/* Blocked roads */}
        {sim.graph.edges.filter((e) => blockedIds.has(e.id)).map((e) => (
          <Polyline key={`b-${e.id}`} positions={[pos(e.u), pos(e.v)]} interactive={false}
                    pathOptions={{ color: "#ef4444", weight: 5, opacity: 0.95, dashArray: "6 6" }} />
        ))}

        {/* Active route */}
        {routeOk && (
          <>
            <Polyline positions={pathPts(routePath)} interactive={false}
                      pathOptions={{ color: "#22d3ee", weight: 7, opacity: 0.95, lineCap: "round", lineJoin: "round" }} />
            <Polyline positions={pathPts(routePath)} interactive={false}
                      pathOptions={{ color: "#ecfeff", weight: 2, opacity: 0.9, className: "route-flow" }} />
          </>
        )}

        {/* Clickable hit lines for every road */}
        {sim.graph.edges.map((e) => (
          <Polyline key={`h-${e.id}`} positions={[pos(e.u), pos(e.v)]}
                    pathOptions={{ color: "#000", weight: 16, opacity: 0 }}
                    eventHandlers={{ click: () => r.handleRoadClick(e) }}>
            <Tooltip sticky direction="top">
              <b>{e.id}</b> {blockedIds.has(e.id) ? "(blocked – click to restore)" : "(click to block)"}<br />
              cost {fmt(e.travel_cost)} · simulated risk {fmt(e.risk)}
            </Tooltip>
          </Polyline>
        ))}

        {/* Plain intersections */}
        {sim.graph.nodes.filter((n) => !stationNodes.has(n.id) && !incidentNodes.has(n.id)).map((n) => (
          <CircleMarker key={`n-${n.id}`} center={[n.lat, n.lng]} radius={3} interactive={false}
                        pathOptions={{ color: "#94a3b8", fillColor: "#0a1220", fillOpacity: 1, weight: 1.5 }} />
        ))}

        {/* Ordered waypoints */}
        {routeOk && routePath.slice(1, -1).map((id, i) => (
          <Marker key={`w-${id}`} position={pos(id)} icon={waypointIcon(i + 1)} interactive={false} zIndexOffset={200} />
        ))}

        {/* Stations */}
        {sim.stations.map((s) => (
          <Marker key={s.id} position={pos(s.node)} icon={stationIcon(s.id, r.selectedStationId === s.id)}
                  zIndexOffset={400} eventHandlers={{ click: () => r.selectStation(s.id) }}>
            <Tooltip direction="top" offset={[0, -14]}>{s.name} ({s.node})</Tooltip>
          </Marker>
        ))}

        {/* Incidents */}
        {sim.incidents.map((i) => (
          <Marker key={i.id} position={pos(i.node)} icon={incidentIcon(i, r.selectedIncidentId === i.id)}
                  zIndexOffset={r.selectedIncidentId === i.id ? 900 : 600}
                  eventHandlers={{ click: () => i.status === "Active" && r.selectIncident(i.id) }}>
            <Tooltip direction="top" offset={[0, -16]}>
              <b>{i.id}</b> · {i.type}<br />{i.priority.priority} · {i.people_affected} people
            </Tooltip>
          </Marker>
        ))}

        {/* Controls inside the map context */}
        <div className="leaflet-top leaflet-left" style={{ marginLeft: 44 }}>
          <div className="leaflet-control flex gap-2 pt-2.5" style={{ pointerEvents: "auto" }}>
            <FitButton points={allPoints} />
          </div>
        </div>
      </MapContainer>

      {/* Overlay controls */}
      <div className="absolute right-3 top-3 z-[1000] flex gap-2">
        <button id="btn-toggle-basemap" className="btn bg-ink-800/90"
                onClick={() => { tileErrors.current = 0; setMode(mode === "map" ? "schematic" : "map"); }}>
          {mode === "map" ? <Grid3x3 size={13} /> : <Layers size={13} />}
          {mode === "map" ? "Schematic grid" : "Street map"}
        </button>
        {r.comparison && (
          <button id="btn-toggle-compare-routes" className={`btn bg-ink-800/90 ${r.showCompareRoutes ? "btn-active" : ""}`}
                  onClick={() => r.setShowCompareRoutes(!r.showCompareRoutes)}>
            Comparison routes
          </button>
        )}
      </div>

      {r.loading && (
        <div className="absolute left-1/2 top-3 z-[1000] -translate-x-1/2 rounded-full border border-cyanx-400/40 bg-ink-900/90 px-3 py-1 text-xs text-cyanx-300">
          <Loader2 size={12} className="mr-1.5 inline animate-spin" /> Working…
        </div>
      )}

      {!routeOk && active && (
        <div id="no-route-banner" className="absolute left-1/2 top-12 z-[1000] -translate-x-1/2 rounded-lg border border-red-500/50 bg-red-950/90 px-4 py-2 text-sm font-semibold text-red-200 shadow-panel">
          No safe route available
        </div>
      )}

      {r.selectedIncident && (
        <div id="incident-detail" className="panel absolute bottom-3 left-3 z-[1000] w-72 p-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-mono font-semibold text-white">{r.selectedIncident.id}</span>
            <span className="text-slate-300">{r.selectedIncident.type}</span>
            <span className="ml-auto rounded px-1.5 py-0.5 text-[10px] font-semibold"
                  style={{ color: PRIORITY_COLOR[r.selectedIncident.priority.priority],
                           background: `${PRIORITY_COLOR[r.selectedIncident.priority.priority]}22` }}>
              {r.selectedIncident.priority.priority}
            </span>
          </div>
          <p className="mt-1 text-slate-400">{r.selectedIncident.description}</p>
          <p className="mt-1.5 text-slate-500">
            {r.selectedIncident.people_affected} people · node <span className="font-mono">{r.selectedIncident.node}</span>
          </p>
          <p className="mt-1 text-[11px] text-cyanx-300/90">Rule: {r.selectedIncident.priority.reason}</p>
        </div>
      )}

      <MapLegend />
    </div>
  );
}
