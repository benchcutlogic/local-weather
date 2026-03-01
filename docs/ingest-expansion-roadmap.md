# Model + Observation Ingest Expansion Roadmap

> Closes #39 (foundational slice). Full execution tracked via follow-up issues.

## Source Inventory

| Source | Type | Access | Update Cadence | Priority | Status |
|--------|------|--------|---------------|----------|--------|
| HRRR | Deterministic, 3km | NOAA/AWS open | Hourly | P1 | **Ready to ingest** |
| NAM Nest | Deterministic, 3km | NOAA/AWS open | 6h | P1 | **Ready to ingest** |
| GEFS | Ensemble, 30 members | NOAA/AWS open | 6h | P1 | Schema needed |
| HREF | Ensemble | Limited NCEP | 12h | P2 | Access TBD |
| ECMWF ENS | Ensemble, 51 members | Licensed (ECMWF API) | 12h | P2 | License needed |
| RDPS/GDPS | Deterministic | CMC open | 6h/12h | P3 | Schema needed |
| SNOTEL | Observations | NRCS API | Hourly | P1 | **Ready** |
| METAR | Observations | NOAA ISD | ~hourly | P1 | **Ready** |
| COOP | Observations | NOAA | Daily | P2 | Ready |
| MRMS | Radar QPE | NOAA/AWS | 2-min | P2 | High volume |
| NOHRSC | Snowfall analysis | NOAA | 6h | P2 | Ready |
| NWS Alerts | Alert polygons | api.weather.gov | Real-time | P1 | **Ready** |

## Cost/Volume Estimates (per city, per day)

| Source | Approx Storage/day | Egress | Processing |
|--------|-------------------|--------|------------|
| HRRR (single city extract) | ~5 MB | Free (AWS) | ~2 min/run |
| NAM Nest | ~3 MB | Free (AWS) | ~1 min/run |
| GEFS (ensemble stats) | ~10 MB | Free (AWS) | ~5 min/run |
| SNOTEL (nearby stations) | <1 MB | Free | <1 min |
| METAR (nearby stations) | <1 MB | Free | <1 min |

## Schema Updates Required

### Ensemble products (GEFS, HREF, ECMWF ENS)

New table: `forecast_ensemble_stats`
```sql
CREATE TABLE forecast_ensemble_stats (
  city_slug STRING,
  model_name STRING,
  run_time TIMESTAMP,
  valid_time TIMESTAMP,
  elevation_band INT64,
  -- Ensemble statistics
  temp_2m_mean FLOAT64,
  temp_2m_p10 FLOAT64,
  temp_2m_p25 FLOAT64,
  temp_2m_p50 FLOAT64,
  temp_2m_p75 FLOAT64,
  temp_2m_p90 FLOAT64,
  precip_mean FLOAT64,
  precip_p90 FLOAT64,
  wind_mean FLOAT64,
  wind_p90 FLOAT64,
  member_count INT64
);
```

### Observation products (SNOTEL, METAR, COOP)

New table: `observations`
```sql
CREATE TABLE observations (
  city_slug STRING,
  station_id STRING,
  source STRING,  -- 'snotel', 'metar', 'coop'
  obs_time TIMESTAMP,
  lat FLOAT64,
  lon FLOAT64,
  elevation_m FLOAT64,
  temp_k FLOAT64,
  precip_mm FLOAT64,
  snow_depth_m FLOAT64,
  wind_speed_ms FLOAT64,
  wind_dir_deg FLOAT64,
  rh_pct FLOAT64,
  pressure_hpa FLOAT64
);
```

### Verification scoring extension

Add columns to `verification_scores`:
- `zone_id STRING` — for microzone-level scoring
- `horizon_bucket STRING` — 'immediate_0_6h', 'short_6_48h', 'extended_48h_plus'
- `temp_bias FLOAT64`
- `wind_rmse FLOAT64`
- `score_updated_at TIMESTAMP`

## Rollout Plan

### Week 1: HRRR + METAR
- Add HRRR ingest to `services/ingest/` (AWS S3 GRIB2)
- Add METAR station lookup for configured cities
- Wire into existing `forecast_runs` table
- Update commentary prompt with HRRR-aware horizon blending

### Week 2: NAM Nest + SNOTEL + NWS Alerts
- Add NAM Nest ingest (same pattern as HRRR)
- Add SNOTEL ingest for Durango-area stations
- Ingest NWS alert polygons for alert-aware commentary

### Week 3: GEFS ensemble + verification pipeline
- Create `forecast_ensemble_stats` table
- Ingest GEFS ensemble statistics
- Build daily verification scoring job against METAR/SNOTEL observations
- Populate `verification_scores` with zone + horizon granularity

## City + Microzone Serving Strategy (Durango)

1. Valley floor (Animas): HRRR surface point, METAR from KDRO
2. Foothills (La Plata): HRRR + lapse-rate adjusted, nearest SNOTEL
3. Pass corridor (Coal Bank/Molas): HRRR ridge point, SNOTEL Red Mountain Pass
4. Each zone gets independent verification scoring
5. Commentary includes zone-specific model confidence

## Follow-up Issues Needed
- [ ] HRRR ingest implementation
- [ ] METAR/SNOTEL observation ingest
- [ ] GEFS ensemble statistics pipeline
- [ ] NWS alert polygon integration
- [ ] Daily verification scoring job with zone granularity
