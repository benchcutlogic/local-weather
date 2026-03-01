"""BigQuery queries for forecast data, drift, terrain, and verification scores."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from google.cloud import bigquery

from config import BQ_DATASET, GCP_PROJECT

logger = logging.getLogger(__name__)

_client: bigquery.Client | None = None


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=GCP_PROJECT)
    return _client


def get_latest_forecasts(city_slug: str) -> list[dict]:
    """Get latest *usable* forecast data for a city across all models.

    Prefer the most recent run with non-null core metrics to avoid selecting a run
    where every value is null (which can happen during transient ingest issues).
    """
    client = _get_client()
    query = f"""
    WITH run_quality AS (
        SELECT
            model_name,
            run_time,
            COUNT(*) AS row_count,
            COUNTIF(
                temperature_2m IS NOT NULL
                OR precip_kg_m2 IS NOT NULL
                OR wind_speed_10m IS NOT NULL
                OR snow_depth IS NOT NULL
                OR relative_humidity IS NOT NULL
            ) AS non_null_core_count
        FROM `{GCP_PROJECT}.{BQ_DATASET}.forecast_runs`
        WHERE city_slug = @city_slug
            AND run_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 48 HOUR)
        GROUP BY model_name, run_time
    ),
    latest_runs AS (
        SELECT
            model_name,
            run_time AS latest_run
        FROM run_quality
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY model_name
            ORDER BY
                (non_null_core_count > 0) DESC,
                run_time DESC
        ) = 1
    )
    SELECT
        f.city_slug,
        f.model_name,
        f.run_time,
        f.valid_time,
        f.elevation_band,
        f.temperature_2m,
        f.precip_kg_m2,
        f.wind_speed_10m,
        f.wind_dir_10m,
        f.snow_depth,
        f.freezing_level_m,
        f.cape,
        f.relative_humidity
    FROM `{GCP_PROJECT}.{BQ_DATASET}.forecast_runs` f
    JOIN latest_runs lr
        ON f.model_name = lr.model_name AND f.run_time = lr.latest_run
    WHERE f.city_slug = @city_slug
    ORDER BY f.model_name, f.valid_time, f.elevation_band
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("city_slug", "STRING", city_slug),
        ]
    )
    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]


def get_model_drift(city_slug: str) -> list[dict]:
    """Get model drift data (last 5 runs) for a city."""
    client = _get_client()
    query = f"""
    SELECT *
    FROM `{GCP_PROJECT}.{BQ_DATASET}.model_drift`
    WHERE city_slug = @city_slug
        AND run_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 48 HOUR)
    ORDER BY model_name, valid_time, run_time
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("city_slug", "STRING", city_slug),
        ]
    )
    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]


def get_terrain_context(city_slug: str) -> dict | None:
    """Get terrain context for a city."""
    client = _get_client()
    query = f"""
    SELECT *
    FROM `{GCP_PROJECT}.{BQ_DATASET}.terrain_context`
    WHERE city_slug = @city_slug
    LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("city_slug", "STRING", city_slug),
        ]
    )
    rows = list(client.query(query, job_config=job_config).result())
    return dict(rows[0]) if rows else None


def get_verification_scores(city_slug: str) -> list[dict]:
    """Get verification scores for a city (30-day rolling)."""
    client = _get_client()
    query = f"""
    SELECT *
    FROM `{GCP_PROJECT}.{BQ_DATASET}.verification_scores`
    WHERE city_slug = @city_slug
    ORDER BY model_name
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("city_slug", "STRING", city_slug),
        ]
    )
    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]


def get_data_trust_summary(city_slug: str) -> list[dict]:
    """Get per-model freshness and usable-row summary for UI trust contract."""
    client = _get_client()
    query = f"""
    WITH recent AS (
      SELECT
        model_name,
        run_time,
        valid_time,
        temperature_2m,
        precip_kg_m2,
        wind_speed_10m,
        snow_depth,
        relative_humidity
      FROM `{GCP_PROJECT}.{BQ_DATASET}.forecast_runs`
      WHERE city_slug = @city_slug
        AND run_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 48 HOUR)
    ),
    latest_per_model AS (
      SELECT model_name, MAX(run_time) AS latest_run_time
      FROM recent
      GROUP BY model_name
    )
    SELECT
      r.model_name,
      l.latest_run_time AS run_time,
      MAX(r.valid_time) AS latest_valid_time,
      COUNT(*) AS total_rows,
      COUNTIF(
        r.temperature_2m IS NOT NULL
        OR r.precip_kg_m2 IS NOT NULL
        OR r.wind_speed_10m IS NOT NULL
        OR r.snow_depth IS NOT NULL
        OR r.relative_humidity IS NOT NULL
      ) AS usable_rows
    FROM recent r
    JOIN latest_per_model l
      ON r.model_name = l.model_name
      AND r.run_time = l.latest_run_time
    GROUP BY r.model_name, l.latest_run_time
    ORDER BY r.model_name
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("city_slug", "STRING", city_slug),
        ]
    )
    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]


def get_verification_scores_by_zone(city_slug: str, zone_id: str | None = None) -> list[dict]:
    """Get rolling verification scores optionally filtered by microzone.

    Supports #38: rolling microclimate verification scores keyed by
    city + optional zone + horizon + model.
    """
    client = _get_client()
    zone_filter = ""
    params = [bigquery.ScalarQueryParameter("city_slug", "STRING", city_slug)]
    if zone_id:
        zone_filter = "AND zone_id = @zone_id"
        params.append(bigquery.ScalarQueryParameter("zone_id", "STRING", zone_id))

    query = f"""
    SELECT
        model_name,
        COALESCE(zone_id, 'city-wide') AS zone_id,
        horizon_bucket,
        num_comparisons,
        temp_rmse,
        temp_bias,
        precip_mae,
        wind_rmse,
        score_updated_at
    FROM `{GCP_PROJECT}.{BQ_DATASET}.verification_scores`
    WHERE city_slug = @city_slug
        {zone_filter}
    ORDER BY model_name, horizon_bucket
    """
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]


def get_best_model_by_horizon(city_slug: str, zone_id: str | None = None) -> list[dict]:
    """Return the best-performing model per horizon bucket for a city.

    Used by the frontend model performance summary card (#38).
    When *zone_id* is provided the ranking is scoped to that zone.
    """
    client = _get_client()
    zone_filter = "AND zone_id = @zone_id" if zone_id else ""
    query = f"""
    WITH ranked AS (
        SELECT
            model_name,
            COALESCE(horizon_bucket, 'all') AS horizon_bucket,
            num_comparisons,
            temp_rmse,
            precip_mae,
            ROW_NUMBER() OVER (
                PARTITION BY COALESCE(horizon_bucket, 'all')
                ORDER BY temp_rmse ASC
            ) AS rn
        FROM `{GCP_PROJECT}.{BQ_DATASET}.verification_scores`
        WHERE city_slug = @city_slug
            AND num_comparisons >= 10
            {zone_filter}
    )
    SELECT model_name, horizon_bucket, num_comparisons, temp_rmse, precip_mae
    FROM ranked
    WHERE rn = 1
    """
    params = [bigquery.ScalarQueryParameter("city_slug", "STRING", city_slug)]
    if zone_id:
        params.append(bigquery.ScalarQueryParameter("zone_id", "STRING", zone_id))
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]


def get_all_city_slugs() -> list[str]:
    """Get all distinct city slugs from forecast_runs."""
    client = _get_client()
    query = f"""
    SELECT DISTINCT city_slug
    FROM `{GCP_PROJECT}.{BQ_DATASET}.forecast_runs`
    WHERE run_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 48 HOUR)
    """
    rows = client.query(query).result()
    return [row["city_slug"] for row in rows]
