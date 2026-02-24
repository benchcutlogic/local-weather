"""BigQuery streaming writer for forecast data."""

from __future__ import annotations

import logging
from datetime import datetime

from google.cloud import bigquery

from config import BQ_DATASET, BQ_TABLE, GCP_PROJECT
from grib2_reader import ForecastPoint

logger = logging.getLogger(__name__)

_client: bigquery.Client | None = None


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=GCP_PROJECT)
    return _client


def _forecast_point_to_row(point: ForecastPoint) -> dict:
    """Convert a ForecastPoint to a BigQuery row dict."""
    return {
        "city_slug": point.city_slug,
        "model_name": point.model_name,
        "run_time": point.run_time.isoformat(),
        "valid_time": point.valid_time.isoformat(),
        "elevation_band": point.elevation_band,
        "temperature_2m": point.temperature_2m,
        "precip_kg_m2": point.precip_kg_m2,
        "wind_speed_10m": point.wind_speed_10m,
        "wind_dir_10m": point.wind_dir_10m,
        "snow_depth": point.snow_depth,
        "freezing_level_m": point.freezing_level_m,
        "cape": point.cape,
        "relative_humidity": point.relative_humidity,
    }


async def write_forecast_points(points: list[ForecastPoint]) -> int:
    """Stream forecast points to BigQuery.

    Returns the number of rows successfully written.
    """
    if not points:
        return 0

    client = _get_client()
    table_ref = f"{GCP_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"

    rows = [_forecast_point_to_row(p) for p in points]

    # Insert in batches of 500
    batch_size = 500
    total_inserted = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        errors = client.insert_rows_json(table_ref, batch)

        if errors:
            logger.error(
                "BigQuery insert errors (batch %d-%d): %s",
                i,
                i + len(batch),
                errors,
            )
        else:
            total_inserted += len(batch)
            logger.info(
                "Inserted %d rows to %s (batch %d-%d)",
                len(batch),
                table_ref,
                i,
                i + len(batch),
            )

    return total_inserted
