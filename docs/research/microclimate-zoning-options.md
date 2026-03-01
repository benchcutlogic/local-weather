# Microclimate Zoning Options

## Objective
Identify and compare robust methods for generating region-level microclimate zones that can be visualized and explained to end users.

## Inputs Available Today
From current/near-current pipeline:
- Terrain: elevation, slope, aspect (3DEP)
- Land cover: NLCD classes
- Forecast fields: temperature, wind, precip, snow depth, RH, freezing level
- Model spread opportunities: inter-model variance (HRRR/GFS/NAM/ECMWF)
- Verification: RTMA-based error metrics
- AOI definitions: Terraform `aois` + `city_aoi_map`

---

## Candidate Method A — Rule-Based Terrain Weather Bands

### Method
Define deterministic zone classes using thresholds:
- Elevation bins
- Aspect classes (north/east/south/west)
- Slope exposure classes
- Optional land-cover modifiers

Example key:
`zone = elev_bin + aspect_class + exposure_class`

### Advantages
- Highly explainable (“north-facing high-elevation forested slope”)
- Easy to test and audit
- Stable labels over time
- Fast compute and low infrastructure overhead

### Limitations
- Can miss emergent weather patterns unrelated to static terrain classes
- Threshold tuning may be city-specific
- Risk of over-discretization in complex terrain

### Best for
- v1 baseline zoning and user trust

---

## Candidate Method B — Data-Driven Clustering

### Method
Cluster gridded cells by feature vectors:
- Static features: elevation/slope/aspect/land cover
- Dynamic features: forecast variables + model spread + recent verification error

Algorithms:
- K-means (fast, simple)
- HDBSCAN (arbitrary shape, noise handling)
- Gaussian mixture (probabilistic boundaries)

### Advantages
- Captures emergent microclimate structure
- Adapts to local dynamics
- Can discover non-obvious boundaries

### Limitations
- Harder to explain to users
- Labels can drift run-to-run (stability issue)
- More complex data ops and validation

### Best for
- v2+ refinement after baseline trust and observability are established

---

## Candidate Method C — Hybrid (Recommended)

### Method
1. Start with stable rule-based seed zones.
2. Apply clustering or boundary refinement inside each seed zone.
3. Keep stable user-facing labels while allowing dynamic adjustments.

### Advantages
- Preserves explainability and stability
- Improves spatial fit where terrain-only rules fail
- Better long-term flexibility

### Limitations
- Higher implementation complexity than pure rules
- Requires stronger monitoring and drift controls

### Best for
- staged roadmap: v1 rules, v1.5 selective refinement, v2 hybrid default

---

## Zone Data Model Proposal

```ts
interface MicroclimateZone {
  zoneId: string;                 // e.g., dgo-z-003
  citySlug: string;
  label: string;                  // "Upper South-Facing Ridge"
  method: 'rules' | 'cluster' | 'hybrid';
  geometryType: 'polygon' | 'hex';
  geometryRef: string;            // tile key or feature id

  terrain: {
    elevMinM: number;
    elevMaxM: number;
    dominantAspect?: 'N'|'E'|'S'|'W'|'flat';
    slopeClass?: 'low'|'moderate'|'steep';
    dominantLandCover?: string;
  };

  weatherDelta: {
    tempDeltaF?: number;          // vs city baseline
    windDeltaMph?: number;
    precipDeltaPct?: number;
    snowDeltaIn?: number;
  };

  confidence: {
    level: 'high' | 'moderate' | 'low';
    score: number;                // 0-1
    rationale: string[];          // model agreement, data recency, etc.
  };

  hazards: string[];              // ['wind', 'snow', 'flood', 'smoke']
  updatedAt: string;
}
```

---

## Comparison Matrix

| Criterion | Rules | Clustering | Hybrid |
|---|---:|---:|---:|
| Explainability | 5 | 2 | 4 |
| Stability across runs | 5 | 2 | 4 |
| Captures emergent behavior | 2 | 5 | 4 |
| Implementation complexity | 2 | 4 | 5 |
| Ops burden | 2 | 4 | 5 |
| v1 suitability | 5 | 2 | 3 |
| Long-term adaptability | 3 | 5 | 5 |

(1=low, 5=high; complexity/ops burden high = more cost)

---

## Recommendation

### v1
- Implement **Rules-Based Terrain Weather Bands**
- Keep 5–12 zones per city for readability
- Add confidence categorization by zone

### v1.5
- Add limited dynamic refinement for top-priority cities (e.g., Durango)

### v2
- Move to **Hybrid** where validation shows improved user outcomes

---

## Validation Plan for Zoning Quality
1. **Spatial coherence:** adjacent cells in a zone should have low intra-zone variance
2. **Predictive usefulness:** zone-level summaries should outperform city-wide averages
3. **User comprehension:** zone labels should be understandable without meteorology jargon
4. **Stability:** zone IDs/labels should not churn excessively between runs

---

## Open Implementation Decisions
- Zone granularity target by city size/topography
- Dynamic refresh cadence for zone stats
- Storage format for geometries (GeoJSON vs vector tile pipeline)
- Label generation strategy (human-readable and stable)
