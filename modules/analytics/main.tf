variable "project_id" {}
variable "region" {}

resource "google_bigquery_dataset" "weather_core" {
  dataset_id  = "weather_core"
  location    = "US" # Multi-region for ML training availability
  description = "Central lake for NWP time-series, GEE terrain, and verification"
}

# 1. TIME-SERIES FORECAST RUNS
resource "google_bigquery_table" "forecast_runs" {
  dataset_id = google_bigquery_dataset.weather_core.dataset_id
  table_id   = "forecast_runs"

  time_partitioning {
    type  = "DAY"
    field = "run_time" # Partition by initialization time for easy cleanup
  }
  clustering = ["city_slug", "valid_time", "model_name"]

  schema = <<EOF
[
  {"name": "city_slug", "type": "STRING", "mode": "REQUIRED"},
  {"name": "model_name", "type": "STRING", "mode": "REQUIRED", "description": "HRRR, GFS, ECMWF"},
  {"name": "run_time", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "valid_time", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "elevation_band", "type": "INTEGER", "mode": "NULLABLE"},
  {"name": "temperature_2m", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "precip_kg_m2", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "wind_speed_10m", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "wind_dir_10m", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "snow_depth", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "freezing_level_m", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "cape", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "relative_humidity", "type": "FLOAT", "mode": "NULLABLE"}
]
EOF
}

# 2. MODEL DRIFT (Dynamic View using SQL Window Functions)
# Calculates drift instantly without requiring a separate physical table.
resource "google_bigquery_table" "model_drift_view" {
  dataset_id = google_bigquery_dataset.weather_core.dataset_id
  table_id   = "model_drift"

  view {
    use_legacy_sql = false
    query          = <<EOF
      SELECT 
        city_slug, model_name, valid_time, run_time, 
        temperature_2m,
        precip_kg_m2,
        snow_depth,
        (temperature_2m - LAG(temperature_2m) OVER (
          PARTITION BY city_slug, model_name, valid_time, elevation_band 
          ORDER BY run_time ASC
        )) as temp_drift_vs_last_run,
        (precip_kg_m2 - LAG(precip_kg_m2) OVER (
          PARTITION BY city_slug, model_name, valid_time, elevation_band 
          ORDER BY run_time ASC
        )) as precip_drift_vs_last_run,
        (snow_depth - LAG(snow_depth) OVER (
          PARTITION BY city_slug, model_name, valid_time, elevation_band 
          ORDER BY run_time ASC
        )) as snow_drift_vs_last_run
      FROM `${var.project_id}.${google_bigquery_dataset.weather_core.dataset_id}.forecast_runs`
EOF
  }
}

# 3. VERIFICATION GROUND TRUTH (Sourced from GEE RTMA)
resource "google_bigquery_table" "ground_truth" {
  dataset_id = google_bigquery_dataset.weather_core.dataset_id
  table_id   = "ground_truth"

  time_partitioning {
    type  = "DAY"
    field = "valid_time"
  }
  clustering = ["city_slug"]

  schema = <<EOF
[
  {"name": "city_slug", "type": "STRING", "mode": "REQUIRED"},
  {"name": "valid_time", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "obs_temp_2m", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "obs_precip", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "obs_wind_speed", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "obs_snow_depth", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "source", "type": "STRING", "mode": "REQUIRED", "description": "RTMA, ASOS, crowdsourced"}
]
EOF
}

# 4. TERRAIN CONTEXT (Sourced asynchronously from GEE 3DEP/NLCD)
resource "google_bigquery_table" "terrain_context" {
  dataset_id = google_bigquery_dataset.weather_core.dataset_id
  table_id   = "terrain_context"
  clustering = ["city_slug"]

  schema = <<EOF
[
  {"name": "city_slug", "type": "STRING", "mode": "REQUIRED"},
  {"name": "city_name", "type": "STRING", "mode": "REQUIRED"},
  {"name": "lat", "type": "FLOAT", "mode": "REQUIRED"},
  {"name": "lon", "type": "FLOAT", "mode": "REQUIRED"},
  {"name": "elevation_bands_json", "type": "JSON", "mode": "REQUIRED"},
  {"name": "land_cover_json", "type": "JSON", "mode": "REQUIRED"},
  {"name": "slope_aspect_json", "type": "JSON", "mode": "NULLABLE"},
  {"name": "last_updated", "type": "TIMESTAMP", "mode": "REQUIRED"}
]
EOF
}

# 5. VERIFICATION SCORES (Rolling model accuracy)
resource "google_bigquery_table" "verification_scores_view" {
  dataset_id = google_bigquery_dataset.weather_core.dataset_id
  table_id   = "verification_scores"

  view {
    use_legacy_sql = false
    query          = <<EOF
      SELECT
        f.city_slug,
        f.model_name,
        COUNT(*) as num_comparisons,
        AVG(ABS(f.temperature_2m - g.obs_temp_2m)) as temp_mae,
        AVG(POW(f.temperature_2m - g.obs_temp_2m, 2)) as temp_mse,
        SQRT(AVG(POW(f.temperature_2m - g.obs_temp_2m, 2))) as temp_rmse,
        AVG(ABS(f.precip_kg_m2 - g.obs_precip)) as precip_mae
      FROM `${var.project_id}.${google_bigquery_dataset.weather_core.dataset_id}.forecast_runs` f
      JOIN `${var.project_id}.${google_bigquery_dataset.weather_core.dataset_id}.ground_truth` g
        ON f.city_slug = g.city_slug
        AND f.valid_time = g.valid_time
      WHERE f.run_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
        AND f.elevation_band IS NULL  -- Compare surface-level only
      GROUP BY f.city_slug, f.model_name
EOF
  }
}

# 6. GRID TILE METADATA INDEX
resource "google_bigquery_table" "grid_tiles" {
  dataset_id = google_bigquery_dataset.weather_core.dataset_id
  table_id   = "grid_tiles"

  time_partitioning {
    type  = "DAY"
    field = "valid_time"
  }
  clustering = ["model_name", "run_time", "tile_id"]

  schema = <<EOF
[
  {"name": "model_name", "type": "STRING", "mode": "REQUIRED"},
  {"name": "run_time", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "valid_time", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "tile_id", "type": "STRING", "mode": "REQUIRED"},
  {"name": "min_lat", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "min_lon", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "max_lat", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "max_lon", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "resolution_deg", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "row_count", "type": "INTEGER", "mode": "NULLABLE"},
  {"name": "col_count", "type": "INTEGER", "mode": "NULLABLE"},
  {"name": "gcs_prefix", "type": "STRING", "mode": "NULLABLE"},
  {"name": "ingest_id", "type": "STRING", "mode": "NULLABLE"},
  {"name": "created_at", "type": "TIMESTAMP", "mode": "NULLABLE"}
]
EOF
}

# 7. GRID TILE FIELD INDEX
resource "google_bigquery_table" "grid_tile_fields" {
  dataset_id = google_bigquery_dataset.weather_core.dataset_id
  table_id   = "grid_tile_fields"

  time_partitioning {
    type  = "DAY"
    field = "valid_time"
  }
  clustering = ["model_name", "run_time", "tile_id", "field_name"]

  schema = <<EOF
[
  {"name": "model_name", "type": "STRING", "mode": "REQUIRED"},
  {"name": "run_time", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "valid_time", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "tile_id", "type": "STRING", "mode": "REQUIRED"},
  {"name": "field_name", "type": "STRING", "mode": "REQUIRED"},
  {"name": "unit", "type": "STRING", "mode": "NULLABLE"},
  {"name": "gcs_uri", "type": "STRING", "mode": "NULLABLE"},
  {"name": "compression", "type": "STRING", "mode": "NULLABLE"},
  {"name": "min_value", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "max_value", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "mean_value", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "null_count", "type": "INTEGER", "mode": "NULLABLE"},
  {"name": "ingest_id", "type": "STRING", "mode": "NULLABLE"},
  {"name": "created_at", "type": "TIMESTAMP", "mode": "NULLABLE"}
]
EOF
}

# 8. GRID POINT SAMPLE TABLE (bounded for QA/quick map previews)
resource "google_bigquery_table" "grid_points_sampled" {
  dataset_id = google_bigquery_dataset.weather_core.dataset_id
  table_id   = "grid_points_sampled"

  time_partitioning {
    type  = "DAY"
    field = "valid_time"
  }
  clustering = ["model_name", "run_time", "tile_id"]

  schema = <<EOF
[
  {"name": "model_name", "type": "STRING", "mode": "REQUIRED"},
  {"name": "run_time", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "valid_time", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "tile_id", "type": "STRING", "mode": "REQUIRED"},
  {"name": "city_slug", "type": "STRING", "mode": "NULLABLE"},
  {"name": "lat", "type": "FLOAT", "mode": "REQUIRED"},
  {"name": "lon", "type": "FLOAT", "mode": "REQUIRED"},
  {"name": "temperature_2m", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "precip_kg_m2", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "wind_u_10m", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "wind_v_10m", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "snow_depth", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "relative_humidity", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "ingest_id", "type": "STRING", "mode": "NULLABLE"},
  {"name": "created_at", "type": "TIMESTAMP", "mode": "NULLABLE"}
]
EOF
}

output "dataset_id" { value = google_bigquery_dataset.weather_core.dataset_id }
