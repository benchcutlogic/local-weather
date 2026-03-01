# Microclimate Visualization Patterns

## Objective
Select map/visual encodings that maximize user comprehension while staying performant and maintainable on mobile-first SvelteKit + Cloudflare.

## Pattern 1 — Polygon Choropleth Zones

### Description
Render zone polygons with fill color based on selected metric:
- temperature delta
- wind intensity
- precip/snow risk
- confidence category

### Pros
- Intuitive region boundaries
- Good for AOI alignment and labels
- Easy click/tap interaction

### Cons
- Requires robust boundary generation
- Can imply false precision at edges

### Best use
Default map mode for v1

---

## Pattern 2 — Hex Grid Overlay

### Description
Uniform hex bins with color encoding for uncertainty/model spread/hazard intensity.

### Pros
- Spatially neutral bins, less boundary argument
- Great for confidence/error surfaces
- Easy aggregation and smoothing

### Cons
- Less natural for human region semantics
- Harder to explain than named zones

### Best use
Secondary “confidence layer” mode

---

## Pattern 3 — Isolines / Contours

### Description
Line overlays for critical thresholds:
- freezing line
- wind threshold lines
- precipitation intensity contours

### Pros
- Excellent for threshold-based decisions
- Familiar in weather contexts

### Cons
- Visual clutter risk
- Hard on mobile if too many lines

### Best use
Optional expert overlay, off by default

---

## Pattern 4 — AOI Cards + Minimap (Low-Fidelity Fallback)

### Description
List AOIs with mini static map and key metrics.

### Pros
- Very high performance
- Works on low-end devices/no WebGL
- Accessible and easy to scan

### Cons
- Lower spatial richness
- Less exploratory power

### Best use
Automatic fallback mode + accessibility mode

---

## Recommended v1 Visualization Stack

### Base
- Polygon choropleth zones (named microclimates)

### Overlays
- AOI boundaries + labels
- Confidence (categorical 3-tier) via light hatch or border style
- Hazard badges per zone

### Optional (advanced toggle)
- Isolines for freezing level / wind thresholds

### Fallback
- AOI card list + static minimap snapshot

---

## Interaction Model (v1)
1. Map opens with default metric: “Feels-like temperature delta”
2. User taps zone → bottom sheet/card
3. Card contains:
   - zone label
   - key metric deltas
   - confidence level + reason
   - current hazards
   - “next 6h” summary
4. Layer toggles:
   - Metric selector (temp/wind/precip/snow)
   - AOI boundaries on/off
   - Confidence overlay on/off

---

## Visual Design Guardrails
- Use colorblind-safe sequential/diverging ramps
- Keep max 2 simultaneous overlays visible
- Always show legend and scale context
- Include confidence symbol in legend (not color-only)

---

## Cognitive Load Rules
- Default to one metric at a time
- Avoid dual-axis map legends
- Keep label density low (declutter on small screens)
- Explain “confidence” in plain language

---

## Mobile Performance Budget Guidance
- Initial view: <= 150KB transferred for map metadata + primary layer descriptors
- Interaction latency: <100ms for zone tap highlight
- Time to first usable map interaction: <= 2.5s median on 4G
- Defer advanced overlays until user enables them

---

## Evaluation Criteria for Pattern Selection
- Accuracy perception without overconfidence
- Task completion speed
- Error rate in interpreting hazards/confidence
- Frame rate and memory stability on representative devices
- Implementation complexity vs value
