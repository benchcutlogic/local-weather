# Gridded Spatial Forecast Data Plan

## Goal
Add a gridded data pipeline alongside the current city/elevation `forecast_runs` table so we can support map tiles, bbox queries, corridor/race analytics, and regional aggregates.

## Current State
- `weather_core.forecast_runs` is point-based (`city_slug`, `model_name`, `run_time`, `valid_time`, metrics).
- Ingestion currently extracts nearest-grid values for configured cities.

## Proposed Architecture

### 1) Canonical grid storage (object storage)
Store full gridded fields in chunked columnar format in GCS:
- Format: **Parquet** (phase 1) or **Zarr** (phase 2)
- Path shape:
  - `gs://<bucket>/model=<MODEL>/run_date=<YYYY-MM-DD>/run_hour=<HH>/valid_time=<ISO>/tile=<tile_id>/part-*.parquet`
- Why: cheaper and better for large arrays than fully exploded BigQuery rows.

### 2) BigQuery index + serving tables
Keep BigQuery for indexing, metadata, and query-friendly subsets.

#### A. `weather_core.grid_tiles`
One row per tile/time/model with envelope + metadata.
- partition: `DATE(valid_time)`
- cluster: `model_name, run_time, tile_id`

#### B. `weather_core.grid_tile_fields`
Per-field references + optional small summary stats.
- points to GCS object URI per tile/field.

#### C. `weather_core.grid_points_sampled` (optional, bounded)
Downsampled cells for ad-hoc SQL and QA.
- not intended for full-resolution archive.

### 3) Existing table stays
`forecast_runs` remains the application serving table for city/elevation UX. It can be derived from gridded source instead of direct nearest-point extraction over time.

---

## Tile strategy
Use stable tile IDs so data is queryable and cacheable:
- Option A: `z/x/y` style slippy tile at fixed zoom (easy web-map integration)
- Option B: fixed lat/lon chunking (e.g., 0.25° x 0.25° or 1° x 1°)

Recommendation: start with **fixed chunking matching model resolution** and add z/x/y materialization later.

---

## Query patterns this unlocks
1. **bbox + time range**
2. **race corridor extraction** (polyline buffer)
3. **area aggregates** (county/watershed/elevation bands)
4. **model comparison heatmaps**

---

## Phased rollout

### Phase 1 (fast path)
- Add BQ index tables (`grid_tiles`, `grid_tile_fields`)
- Write Parquet tiles to GCS during ingestion
- Continue writing `forecast_runs`

### Phase 2
- Add tile API endpoints (`/grid/{model}/{run}/{valid}?bbox=...`)
- Add Cloud CDN caching strategy
- Add derived rollups for race routes and regions

### Phase 3
- Migrate canonical storage to Zarr if needed for xarray-native workflows
- Add data retention tiers (hot/warm/cold)

---

## Operational notes
- Partition pruning on `valid_time` is critical for cost.
- Track lineage fields: `ingest_id`, `source_url`, `sha256`, `created_at`.
- Add row/field completeness checks per tile before publish.

---

## Immediate implementation tasks
1. Add new BQ table resources in Terraform (see `docs/sql/grid_tables.sql`).
2. Extend ingestion writer to emit tile metadata rows.
3. Add feature flag to enable/disable gridded writes per model.
4. Add basic QA dashboard: tile count, field coverage, lag per model run.
