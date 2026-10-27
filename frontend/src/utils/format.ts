import type { Severity } from "../types";

export const SEVERITY_COLOR: Record<Severity, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#f59e0b",
  low: "#22c55e",
};

export const PRIORITY_COLOR: Record<string, string> = {
  Critical: "#ef4444",
  High: "#f97316",
  Medium: "#f59e0b",
  Low: "#38bdf8",
  Resolved: "#22c55e",
};

export const ALG_COLOR: Record<string, string> = {
  astar: "#22d3ee",
  bfs: "#a78bfa",
  greedy: "#fbbf24",
};

export const ALG_LABEL: Record<string, string> = {
  astar: "A* Search",
  bfs: "Breadth-First",
  greedy: "Greedy Best-First",
};

export const fmt = (n: number | null | undefined, digits = 2) =>
  n === null || n === undefined ? "–" : n.toFixed(digits);

export const edgeId = (a: string, b: string) => (a <= b ? `${a}-${b}` : `${b}-${a}`);

export const formatTime = (iso: string) => {
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleTimeString([], { hour12: false });
};
