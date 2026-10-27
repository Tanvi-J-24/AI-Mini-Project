import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./frontend/src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#060b16", 900: "#0a1220", 800: "#0f1b2e", 700: "#16263d", 600: "#203551" },
        cyanx: { 300: "#67e8f9", 400: "#22d3ee", 500: "#06b6d4" },
        alert: "#ef4444",
        warn: "#f59e0b",
        safe: "#22c55e",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: { panel: "0 4px 24px rgba(0,0,0,0.35)" },
    },
  },
  plugins: [],
} satisfies Config;
