# ADR 0001: Microclimate Map v1 Architecture

## Status
Accepted

## Context
`local-weather` needs region-level visualization of microclimates and AOIs while preserving mobile performance and user trust.

## Decision

### 1) Zone geometry is static
- Zone polygons are generated offline and remain fixed for v1.
- Metrics update each model cycle; boundaries do not.

### 2) Label churn threshold is zero
- Human-readable labels are stable anchors.
- We do not rotate labels between forecast cycles.

### 3) Interaction priority is AOI > zone
- AOIs are high-intent user destinations and take click/tap priority.
- Zone context is still displayed in AOI details.

### 4) Route/segment-aware weather is deferred to v2
- v1 focuses on regional, point-in-time zone summaries.

### 5) Data delivery pattern: client-side join
- Static geometry asset (`/maps/{city}-zones.geojson`) is served as long-lived cached static content.
- Dynamic metrics (`/api/map/{city}/summary`) are fetched separately and joined in the browser via MapLibre `setFeatureState()`.

### 6) Confidence visualization
- Color is reserved for active metric encoding.
- Low confidence uses texture (hatching), not a second color scale.

### 7) Fallback strategy
- SSR renders AOI cards by default.
- Interactive map is lazy-loaded via `IntersectionObserver`.
- If map/webgl fails, AOI cards remain the primary experience.

## Consequences

### Positive
- Predictable mobile performance
- Low backend complexity for v1
- High explainability and user trust
- Minimal Cloudflare compute burden

### Trade-offs
- Less spatial flexibility than dynamic clustering
- Coarser representation of rapidly changing phenomena
- Requires later roadmap for advanced route-aware weather

## Implementation Notes
- Frontend map shell: `MicroclimateMap.svelte`
- Static geometry: `frontend/static/maps/durango-zones.geojson`
- Dynamic summary endpoint: `frontend/src/routes/api/map/[city]/summary/+server.ts`
- Mock metrics seed: `frontend/src/lib/map/mockData.ts`
