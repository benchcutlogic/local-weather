# Technical Feasibility Spikes — Microclimate Map

## Objective
De-risk architecture and rendering strategy before implementation by running bounded technical spikes.

## Spike Plan Overview

### Spike A — Map Rendering Core (MapLibre)
**Goal:** Validate baseline rendering pipeline in SvelteKit route.

Tasks:
- Integrate MapLibre GL JS in SvelteKit component
- Render base map + synthetic polygon layer + click handlers
- Confirm Cloudflare deployment compatibility

Success criteria:
- No SSR/runtime conflicts
- Smooth pan/zoom on target devices
- Zone click interaction stable

---

### Spike B — Data Delivery Path (GeoJSON vs Vector Tiles)
**Goal:** Compare delivery formats for zone geometries.

Approach:
- Path 1: direct GeoJSON payload per city
- Path 2: vector tile/PMTiles approach

Measure:
- payload size
- time-to-first-render
- interaction responsiveness
- complexity of update pipeline

Recommendation target:
- GeoJSON for low-complexity cities/v1
- vector tile path for scale and complex geographies

---

### Spike C — Confidence Overlay Encoding
**Goal:** Ensure confidence layer is understandable and non-intrusive.

Test variants:
- fill opacity modulation
- border styles (solid/dashed)
- subtle pattern/hatch overlays

Evaluate:
- readability with hazard colors
- confusion in user interpretation
- accessibility (contrast/colorblind)

---

### Spike D — AOI + Zone Layer Compositing
**Goal:** Validate layer ordering and interaction semantics.

Tasks:
- AOI boundaries over zones
- AOI labels and zone labels decluttering
- click prioritization rules (zone first, AOI second or vice versa)

Deliverable:
- clear interaction contract and layer z-index model

---

### Spike E — Fallback Experience
**Goal:** Provide robust behavior for low-end/no-WebGL.

Tasks:
- detect low-capability mode
- render static map image or lightweight SVG minimap
- provide AOI list cards with metrics

Success criteria:
- core insights preserved without interactive map

---

## Candidate Stack

### Primary
- MapLibre GL JS
- SvelteKit component wrappers
- Data endpoint from SvelteKit server routes

### Optional
- deck.gl for specialized overlays (only if needed)
- PMTiles for scale and edge-friendly distribution

### Storage/compute candidates
- Precomputed zone geometries in GCS or object storage
- Zone metrics in BigQuery materialized export -> API-friendly shape

---

## API Contract Draft

### `GET /api/map/:city/zones`
Returns geometry + metadata:
- zoneId
- label
- geometry
- confidenceLevel
- hazard flags
- key metric deltas

### `GET /api/map/:city/summary`
Returns:
- city-level legend ranges
- timestamp freshness
- active metric metadata

### `GET /api/map/:city/aois`
Returns:
- AOI geometries
- AOI names/types
- optional AOI-level summary stats

---

## Instrumentation Plan
Track:
- map init duration
- first interactive paint
- layer toggle latency
- tap-to-tooltip latency
- memory footprint at steady state
- tile/geo request error rate

Use these metrics as go/no-go gates for architecture choice.

---

## Testing Matrix
- iPhone mid-tier device (Safari)
- Android mid-tier device (Chrome)
- Desktop Chrome baseline
- low-bandwidth simulation
- no-WebGL fallback path

---

## Known Failure Modes to Probe
- excessive polygon complexity causing jank
- label collisions at low zoom
- confidence overlay visually masking hazard overlay
- stale zone metrics due to asynchronous pipeline lags
- route hydration regressions in map-heavy pages

---

## Exit Criteria (Spikes Complete)
1. Selected rendering strategy + data format
2. Quantified performance profile by device tier
3. Accessibility and clarity validation on confidence/hazard overlays
4. Finalized fallback strategy
5. Implementation-ready technical architecture notes
