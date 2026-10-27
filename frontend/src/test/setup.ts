import "@testing-library/jest-dom/vitest";

// jsdom lacks SVG geometry APIs; Leaflet probes createSVGRect to detect SVG support.
// Test-environment polyfill only (real browsers provide it).
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(SVGElement.prototype as any).createSVGRect = () => ({});
