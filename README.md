# HyperlocalWx

Automated hyperlocal weather forecasting platform scaled to 200+ US cities. Multi-model NWP ingestion, terrain-aware AI commentary, and edge-delivered frontend.

## Architecture

```
NOAA GCS Buckets (HRRR/GFS/NAM/ECMWF)
    │
    ▼
┌─────────────────────┐     ┌──────────────────────┐
│  Ingest Service      │────▶│  BigQuery             │
│  (Cloud Run)         │     │  forecast_runs        │
│  GRIB2 byte-range    │     │  model_drift (view)   │
│  parsing via xarray  │     │  ground_truth         │
└─────────────────────┘     │  terrain_context      │
                             │  verification_scores  │
┌─────────────────────┐     └──────────┬───────────┘
│  GEE Scripts         │────▶           │
│  (Cloud Run Jobs)    │     ┌──────────▼───────────┐
│  RTMA verification   │     │  Commentary Service   │
│  3DEP/NLCD terrain   │     │  (Cloud Run)          │
└─────────────────────┘     │  Vertex AI Gemini     │
                             │  1.5 Flash            │
                             └──────────┬───────────┘
                                        │
                             ┌──────────▼───────────┐
                             │  GCS Bucket           │
                             │  {city}/latest.json   │
                             └──────────┬───────────┘
                                        │
                             ┌──────────▼───────────┐
                             │  Cloudflare Edge      │
                             │  Astro SSR + D1       │
                             │  Pages + Workers      │
                             └─────────────────────┘
```

## Project Structure

```
├── main.tf                          # Terraform module orchestration
├── modules/
│   ├── analytics/                   # BigQuery schema & views
│   ├── ingestion/                   # Cloud Run + Pub/Sub + Scheduler
│   ├── ml_and_jobs/                 # LLM service + GEE jobs
│   ├── notifications/               # Pub/Sub topics
│   └── edge/                        # Cloudflare Pages/Workers/D1
├── services/
│   ├── ingest/                      # GRIB2 byte-range ingestion (Python/FastAPI)
│   ├── commentary/                  # Gemini forecast commentary (Python/FastAPI)
│   └── gee/                         # Earth Engine extraction scripts
├── frontend/                        # SvelteKit 2 SSR app (Cloudflare Pages)
├── .github/workflows/
│   ├── terraform.yml                # Plan on PR, apply on merge
│   └── deploy.yml                   # Build & deploy services + frontend
└── docker-compose.yml               # Local development
```

## Services

### Ingest Service (`services/ingest/`)

FastAPI service that ingests NWP model data from NOAA GCS buckets using byte-range GRIB2 parsing.

- **Endpoints:** `POST /ingest/{hrrr,gfs,nam,ecmwf}`
- **Trigger:** Pub/Sub push (HRRR), Cloud Scheduler (GFS/NAM every 6h)
- **Process:** Reads `.idx` index files → byte-range fetches specific variables → extracts nearest grid points for configured cities → streams to BigQuery
- **Variables:** 2m temp, 10m wind (U/V), precip, snow depth, freezing level, CAPE, RH
- **Elevation:** Applies lapse-rate adjustment for configured elevation bands per city

### Commentary Service (`services/commentary/`)

FastAPI service that generates conversational weather commentary using Vertex AI Gemini.

- **Endpoints:** `POST /generate/{city_slug}`, `POST /generate-all`, `POST /trigger-gee-rtma`, `POST /trigger-gee-terrain`
- **Process:** Queries BigQuery for latest forecasts + model drift + terrain context + verification scores → builds structured prompt → Gemini 1.5 Flash generates commentary → uploads to GCS
- **Style:** Conversational, terrain-aware (like durangoweatherguy.com), mentions model agreement/disagreement

### GEE Scripts (`services/gee/`)

Cloud Run Job scripts for Earth Engine data extraction.

- **`extract_terrain.py`:** 3DEP DEM elevation/slope/aspect + NLCD land cover per city (annual)
- **`extract_verification.py`:** RTMA hourly observations for forecast verification (daily)

### Frontend (`frontend/`)

SvelteKit 2 SSR app deployed to Cloudflare Pages with D1 database.

- **UI stack:** SvelteKit + Tailwind v4 + shadcn-svelte conventions
- **Design system structure:** `atoms/`, `molecules/`, `organisms/` under `src/lib/components/`
- **Storybook:** configured for Svelte components in `.storybook/`
- **City pages:** Commentary display, elevation breakdown, model accuracy, community reports
- **D1 integration:** Crowdsourced weather report submission and display
- **Premium:** Stripe paywall for detailed model comparison charts
- **Forecast API:** Reads via `/api/forecast?city=<slug>&model=<name>&units=<imperial|metric>&hourWindow=<n>` through Cloudflare Worker edge cache
- **Cache invalidation:** Ingestion calls Worker `POST /api/cache/purge` after successful writes (version-bumps cache keys)

## Cities Configuration

Use `config/city-catalog.json` as the canonical per-city product schema.

- JSON Schema: `config/city-catalog.schema.json`
- Frontend city config is generated: `frontend/src/lib/cities.ts`
- Terraform still consumes `terraform.tfvars` (`cities`, `aois`, `city_aoi_map`) for infra + service runtime.

Generate frontend city config from the catalog:

```bash
node scripts/generate-cities-ts.mjs
```

Example city fields in Terraform (superset supported):

```hcl
cities = {
  "durango" = {
    name             = "Durango"
    state            = "CO"
    aliases          = ["dgo"]
    lat              = 37.2753
    lon              = -107.8801
    timezone         = "America/Denver"
    elev_bands       = [2000, 2200, 2500, 2800, 3000]
    terrain_profile  = "mountain"
    seasonal_hazards = ["snowpack", "monsoon_flooding", "fire_smoke"]
    alert_thresholds = {
      snow_in_24h_in    = 10
      wind_gust_mph     = 50
      rain_in_1h_in     = 0.6
      heat_index_f      = 92
      freezing_level_ft = 10000
    }
  }
}
```

## Development

Install git hooks: `brew install lefthook && lefthook install`

## Local Development

```bash
# Start all services
docker compose up --build

# Ingest service: http://localhost:8080
# Commentary service: http://localhost:8081
# Frontend: http://localhost:4321

# Or run services individually
cd services/ingest && pip install -r requirements.txt && uvicorn main:app --reload --port 8080
cd frontend && npm install && npm run dev
```

Requires GCP credentials (`gcloud auth application-default login`) for BigQuery/Vertex AI/GCS access.

## CI/CD

### Terraform (`terraform.yml`)
- **PR:** `terraform plan` with OIDC auth, posts plan as PR comment
- **Merge to main:** `terraform apply -auto-approve`

### Deploy (`deploy.yml`)
- Path-filtered: only builds/deploys changed services
- Docker images → Artifact Registry → Cloud Run
- Frontend → Cloudflare Pages via Wrangler

Both workflows use GCP Workload Identity Federation (no static keys).

## Required Secrets

| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | GCP project ID (`hyperlocal-wx-prod`) |
| `GCP_PROJECT_NUMBER` | GCP project number (for WIF) |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account ID |
| `TF_VAR_edge_cache_purge_token` | Shared token for Worker cache invalidation endpoint |
| `TF_VAR_edge_cache_purge_url` | Worker purge URL (e.g., `https://api.denver.<domain>/api/cache/purge`) |
