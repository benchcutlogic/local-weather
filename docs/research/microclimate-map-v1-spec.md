# Microclimate Map v1 — Implementation Specification

## Scope
Build a production-ready v1 map experience showing microclimate zones and AOIs for each city page.

## Functional Requirements
1. Render city region map with named microclimate zones
2. Show AOI boundaries and labels
3. Allow metric switching (temp/wind/precip/snow)
4. Show per-zone confidence (high/moderate/low) with rationale
5. Show zone hazard indicators (snow/wind/flood/smoke)
6. Zone detail card on tap/click
7. Graceful fallback for low-capability devices

---

## Data Model Additions

### Zone geometry dataset
- `city_slug`
- `zone_id`
- `zone_label`
- `geometry` (GeoJSON or tile reference)
- `method_version` (rules-v1, hybrid-v2, etc.)

### Zone metrics dataset (time-indexed)
- `city_slug`
- `zone_id`
- `valid_time`
- `temp_delta_f`
- `wind_delta_mph`
- `precip_delta_pct`
- `snow_delta_in`
- `confidence_level`
- `confidence_score`
- `confidence_reason_codes[]`
- `hazards[]`

### AOI dataset
- `city_slug`
- `aoi_slug`
- `aoi_name`
- `aoi_type`
- `geometry`

---

## Confidence Model (v1)

### Inputs
- Inter-model spread for active metric
- Data freshness (lag from expected ingest)
- Verification quality trend (RTMA error recent window)

### Simple scoring
`confidence_score = w1*spread_score + w2*freshness_score + w3*verification_score`

Suggested initial weights:
- spread: 0.5
- freshness: 0.2
- verification: 0.3

Bands:
- High: >= 0.75
- Moderate: 0.45–0.74
- Low: < 0.45

---

## UI Specification

### Entry point
- City route `/:city` adds “Microclimate Map” section under forecast summary

### Map controls
- metric selector chips
- AOI toggle
- confidence toggle
- reset view control

### Zone detail card
- title (zone label)
- elevation range
- current metric values/deltas
- confidence + human-readable reason
- active hazards
- short guidance text from commentary style system (optional)

### Legend
- metric color scale
- confidence symbology
- hazard icon key

---

## Component Architecture (SvelteKit)

Suggested structure:
- `atoms/`
  - `LegendChip.svelte`
  - `HazardBadge.svelte`
  - `ConfidenceBadge.svelte`
- `molecules/`
  - `LayerToggleGroup.svelte`
  - `MetricSelector.svelte`
  - `ZoneSummaryRow.svelte`
- `organisms/`
  - `MicroclimateMap.svelte`
  - `ZoneDetailCard.svelte`
  - `MapLegendPanel.svelte`

Server/data:
- `src/routes/api/map/[city]/zones/+server.ts`
- `src/routes/api/map/[city]/aois/+server.ts`
- `src/routes/api/map/[city]/summary/+server.ts`

---

## Delivery Architecture

### Generation pipeline
1. Build/refresh zone geometries per city
2. Compute metric deltas and confidence per zone per forecast cycle
3. Publish API-ready artifacts (or query layer)

### Runtime path
1. City page requests summary + zones + AOIs
2. Client renders map and overlays
3. User interactions remain client-side for responsiveness

---

## Performance Requirements
- Initial microclimate section ready in <= 2.5s median on 4G
- Zone click response <= 100ms perceived
- Layer toggle response <= 150ms perceived
- Memory stable under prolonged pan/zoom sessions

---

## Accessibility Requirements
- Keyboard-accessible controls
- Screen-reader labels for layers and confidence states
- Color palette meeting WCAG contrast recommendations
- Non-color encoding for confidence and hazard states

---

## Rollout Plan

### Stage 1
- Enable for Durango only
- Monitor performance and interaction telemetry

### Stage 2
- Expand to Denver + Salt Lake City
- Validate cross-city generalization

### Stage 3
- Add city onboarding checklist for map readiness

---

## Observability & QA
- Event telemetry: map load, layer toggles, zone taps
- Error monitoring: map data endpoint failures, render exceptions
- Synthetic tests on city routes with map enabled
- Manual UX checks for mobile and low-end fallback modes

---

## Open Questions
1. Should zone geometry be static seasonally or dynamic per cycle?
2. What is the acceptable label churn threshold for user trust?
3. How should AOI and zone conflicts be resolved in click priority?
4. Should route/segment-aware weather (race course overlays) be v1.1 or v2?

---

## Definition of Done (v1)
- Durango map live with microclimate zones + AOIs
- Confidence and hazard overlays functional
- Mobile performance and accessibility checks passed
- Monitoring and fallback paths validated
- Documentation complete for adding new cities
