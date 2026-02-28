-- BigQuery DDL for gridded forecast indexing tables
-- Dataset: weather_core

CREATE TABLE IF NOT EXISTS `hyperlocal-wx-prod.weather_core.grid_tiles` (
  model_name STRING NOT NULL,
  run_time TIMESTAMP NOT NULL,
  valid_time TIMESTAMP NOT NULL,
  tile_id STRING NOT NULL,
  -- Geographic envelope (WGS84)
  min_lat FLOAT64,
  min_lon FLOAT64,
  max_lat FLOAT64,
  max_lon FLOAT64,
  resolution_deg FLOAT64,
  row_count INT64,
  col_count INT64,
  gcs_prefix STRING,
  ingest_id STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(valid_time)
CLUSTER BY model_name, run_time, tile_id;

CREATE TABLE IF NOT EXISTS `hyperlocal-wx-prod.weather_core.grid_tile_fields` (
  model_name STRING NOT NULL,
  run_time TIMESTAMP NOT NULL,
  valid_time TIMESTAMP NOT NULL,
  tile_id STRING NOT NULL,
  field_name STRING NOT NULL,
  unit STRING,
  gcs_uri STRING NOT NULL,
  compression STRING,
  min_value FLOAT64,
  max_value FLOAT64,
  mean_value FLOAT64,
  null_count INT64,
  ingest_id STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(valid_time)
CLUSTER BY model_name, run_time, tile_id, field_name;

-- Optional bounded sampling table for SQL QA and quick lookups.
CREATE TABLE IF NOT EXISTS `hyperlocal-wx-prod.weather_core.grid_points_sampled` (
  model_name STRING NOT NULL,
  run_time TIMESTAMP NOT NULL,
  valid_time TIMESTAMP NOT NULL,
  tile_id STRING NOT NULL,
  lat FLOAT64 NOT NULL,
  lon FLOAT64 NOT NULL,
  temperature_2m FLOAT64,
  precip_kg_m2 FLOAT64,
  wind_u_10m FLOAT64,
  wind_v_10m FLOAT64,
  snow_depth FLOAT64,
  relative_humidity FLOAT64,
  ingest_id STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(valid_time)
CLUSTER BY model_name, run_time, tile_id;