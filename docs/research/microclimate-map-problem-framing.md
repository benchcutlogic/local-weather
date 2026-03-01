# Microclimate & AOI Mapping — Problem Framing

## Purpose
Define the exact user problems, constraints, and success criteria for visualizing microclimates and areas of interest (AOIs) in `local-weather`.

## Product Context
Current platform strengths:
- Multi-model forecast ingestion (HRRR/GFS/NAM/ECMWF)
- Terrain-aware AI commentary
- City-level configuration with elevation bands
- AOI support in Terraform (`aois`, `city_aoi_map`)

Current gap:
- No spatial surface that explains *where within a city/region* conditions diverge.
- Users can read narrative differences but cannot visually localize them.

---

## Core User Jobs to Be Done

### Primary users
1. Local runners/trail users
2. Race directors / operations staff
3. General outdoor users (drivers, hikers, cyclists)

### User questions the map must answer
1. **Where am I in this weather system?**
   - “Am I in a warmer valley pocket or exposed ridge zone?”
2. **How different are neighboring zones?**
   - “If I move 8–12 miles and +2,000 ft elevation, what changes?”
3. **Where are risks concentrated?**
   - “Where are strongest gusts / heavy snow / convective precip pockets?”
4. **How trustworthy is the forecast *here*?**
   - “Is this area high-confidence or model disagreement territory?”
5. **What should I do next?**
   - “Which route/area is safer in the next 6–12 hours?”

---

## Decision Scope
This research covers:
- Spatial representation of microclimate zones
- AOI visualization and interaction model
- Confidence/uncertainty overlay strategy
- v1 implementation architecture on SvelteKit + Cloudflare

Out of scope for v1:
- Full atmospheric simulation visuals
- 3D terrain flythroughs
- Per-user route optimization engine

---

## Constraints

### Technical
- Frontend stack: SvelteKit + Tailwind v4, Cloudflare runtime
- Existing data stack: BigQuery + GCS commentary + D1 reports
- Must support variable city sizes and terrain complexity
- Must have graceful fallback for low-end devices / weak networks

### UX
- Mobile-first readability
- Fast initial render (<2.5s on median 4G for baseline map state)
- Clear legend and explainability (avoid meteorology-only language)

### Operational
- Incremental launch by city
- Minimal custom GIS ops burden for v1
- Reusable pattern across 200+ cities

---

## Non-Functional Requirements
- **Performance:** visible map + base layer interactive within 1.5–2.5s median
- **Reliability:** map degrades gracefully if tile/layer endpoints fail
- **Explainability:** each zone must expose “why this is a separate microclimate”
- **Accessibility:** keyboard focus, high-contrast palette options, color-safe ramps

---

## High-Level Success Criteria

### User outcomes
- 80%+ of test users identify their relevant zone in <10 seconds
- 70%+ accurately explain at least one key difference between two zones
- 70%+ correctly interpret confidence category for their selected area

### Product outcomes
- Increased engagement on city pages with maps enabled
- Increased click-through to hazard/confidence details
- Increased confidence in forecast utility (qualitative user feedback)

### Technical outcomes
- No significant increase in page failure rate
- Controlled JS payload increase
- Stable Cloudflare edge behavior

---

## Research Questions (to answer in subsequent docs)
1. Should microclimates be represented as polygons, grids, or isolines (or hybrid)?
2. What zoning method balances explainability, accuracy, and maintenance burden?
3. Which weather variables define useful microclimate segmentation for v1?
4. How should AOIs coexist with microclimate layers (toggle hierarchy)?
5. What confidence model can be communicated simply without overselling precision?
6. What minimum map interactions create clear value without complexity overload?

---

## Risk Hypotheses
- Users may misinterpret smooth color gradients as deterministic precision.
- Too many overlays can reduce comprehension and trust.
- High-res dynamic layers could exceed mobile performance budgets.
- City-specific special-casing may become a maintenance trap.

Mitigation strategy: optimize for simple, explainable layers first; advanced layers later.

---

## Recommended v1 Principle Set
1. **Explainability over sophistication**
2. **Mobile performance over visual novelty**
3. **Consistent cross-city semantics**
4. **Uncertainty visibility by default (not hidden)**
5. **Progressive enhancement architecture**
