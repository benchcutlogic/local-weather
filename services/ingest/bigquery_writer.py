"""BigQuery streaming writer for forecast data."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
import math
import uuid

from google.cloud import bigquery

from config import (
    BQ_DATASET,
    BQ_GRID_POINTS_SAMPLED_TABLE,
    BQ_GRID_TILE_FIELDS_TABLE,
    BQ_GRID_TILES_TABLE,
    BQ_TABLE,
    GCP_PROJECT,
    CityConfig,
)
from grib2_reader import ForecastPoint, GridSamplePoint

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


def _tile_id(lat: float, lon: float) -> str:
    lat_bin = math.floor(lat)
    lon_bin = math.floor(lon)
    return f"tile_{lat_bin}_{lon_bin}"


def _uv_from_speed_dir(speed: float | None, direction: float | None) -> tuple[float | None, float | None]:
    if speed is None or direction is None:
        return None, None
    # Inverse of meteorological convention used in ingest (direction wind-from)
    # u = -speed * sin(dir), v = -speed * cos(dir)
    rad = math.radians(direction)
    u = -speed * math.sin(rad)
    v = -speed * math.cos(rad)
    return round(u, 3), round(v, 3)


def _insert_rows_batched(client: bigquery.Client, table_ref: str, rows: list[dict], batch_size: int = 500) -> int:
    total_inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        errors = client.insert_rows_json(table_ref, batch)
        if errors:
            logger.error("BigQuery insert errors for %s (batch %d-%d): %s", table_ref, i, i + len(batch), errors)
        else:
            total_inserted += len(batch)
            logger.info("Inserted %d rows to %s (batch %d-%d)", len(batch), table_ref, i, i + len(batch))
    return total_inserted


async def write_forecast_points(
    points: list[ForecastPoint],
    cities: dict[str, CityConfig],
    grid_samples: list[GridSamplePoint] | None = None,
) -> int:
    """Stream forecast points to BigQuery and populate gridded indexing tables.

    Returns the number of forecast_runs rows successfully written.
    """
    if not points:
        return 0

    client = _get_client()
    forecast_table_ref = f"{GCP_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"

    # 1) Write serving table (existing behavior)
    rows = [_forecast_point_to_row(p) for p in points]
    total_inserted = _insert_rows_batched(client, forecast_table_ref, rows)

    # 2) Build sampled spatial rows from base (non-elevation) points
    ingest_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    sampled_rows: list[dict] = []

    # Prefer AOI-wide grid samples when available.
    if grid_samples:
        for gp in grid_samples:
            tile = _tile_id(gp.lat, gp.lon)
            sampled_rows.append({
                "model_name": gp.model_name,
                "run_time": gp.run_time.isoformat(),
                "valid_time": gp.valid_time.isoformat(),
                "tile_id": tile,
                "city_slug": gp.aoi_slug,
                "lat": gp.lat,
                "lon": gp.lon,
                "temperature_2m": gp.temperature_2m,
                "precip_kg_m2": gp.precip_kg_m2,
                "wind_u_10m": gp.wind_u_10m,
                "wind_v_10m": gp.wind_v_10m,
                "snow_depth": gp.snow_depth,
                "relative_humidity": gp.relative_humidity,
                "ingest_id": ingest_id,
                "created_at": created_at,
            })
    else:
        # Fallback to city-point samples if AOI grid samples are unavailable.
        sampled_points: list[ForecastPoint] = [p for p in points if p.elevation_band is None and p.city_slug in cities]
        for p in sampled_points:
            city = cities[p.city_slug]
            tile = _tile_id(city.lat, city.lon)
            wind_u, wind_v = _uv_from_speed_dir(p.wind_speed_10m, p.wind_dir_10m)
            sampled_rows.append({
                "model_name": p.model_name,
                "run_time": p.run_time.isoformat(),
                "valid_time": p.valid_time.isoformat(),
                "tile_id": tile,
                "city_slug": p.city_slug,
                "lat": city.lat,
                "lon": city.lon,
                "temperature_2m": p.temperature_2m,
                "precip_kg_m2": p.precip_kg_m2,
                "wind_u_10m": wind_u,
                "wind_v_10m": wind_v,
                "snow_depth": p.snow_depth,
                "relative_humidity": p.relative_humidity,
                "ingest_id": ingest_id,
                "created_at": created_at,
            })

    if not sampled_rows:
        return total_inserted

    sampled_table_ref = f"{GCP_PROJECT}.{BQ_DATASET}.{BQ_GRID_POINTS_SAMPLED_TABLE}"
    _insert_rows_batched(client, sampled_table_ref, sampled_rows)

    # 3) Tile metadata and field summaries
    tile_groups: dict[tuple[str, str, str, str], list[dict]] = {}
    for r in sampled_rows:
        key = (r["model_name"], r["run_time"], r["valid_time"], r["tile_id"])
        tile_groups.setdefault(key, []).append(r)

    tile_rows: list[dict] = []
    field_rows: list[dict] = []
    fields = [
        ("temperature_2m", "K"),
        ("precip_kg_m2", "kg/m2"),
        ("wind_u_10m", "m/s"),
        ("wind_v_10m", "m/s"),
        ("snow_depth", "m"),
        ("relative_humidity", "%"),
    ]

    for (model_name, run_time, valid_time, tile_id), group in tile_groups.items():
        lats = [g["lat"] for g in group]
        lons = [g["lon"] for g in group]
        tile_rows.append({
            "model_name": model_name,
            "run_time": run_time,
            "valid_time": valid_time,
            "tile_id": tile_id,
            "min_lat": min(lats),
            "min_lon": min(lons),
            "max_lat": max(lats),
            "max_lon": max(lons),
            "resolution_deg": 0.25,
            "row_count": len(set(lats)),
            "col_count": len(set(lons)),
            "gcs_prefix": f"gs://hyperlocal-wx-grids/model={model_name}/run_time={run_time}/valid_time={valid_time}/tile={tile_id}",
            "ingest_id": ingest_id,
            "created_at": created_at,
        })

        for field_name, unit in fields:
            vals = [g[field_name] for g in group if g[field_name] is not None]
            null_count = len(group) - len(vals)
            field_rows.append({
                "model_name": model_name,
                "run_time": run_time,
                "valid_time": valid_time,
                "tile_id": tile_id,
                "field_name": field_name,
                "unit": unit,
                "gcs_uri": f"gs://hyperlocal-wx-grids/model={model_name}/run_time={run_time}/valid_time={valid_time}/tile={tile_id}/{field_name}.parquet",
                "compression": "snappy",
                "min_value": min(vals) if vals else None,
                "max_value": max(vals) if vals else None,
                "mean_value": (sum(vals) / len(vals)) if vals else None,
                "null_count": null_count,
                "ingest_id": ingest_id,
                "created_at": created_at,
            })

    grid_tiles_ref = f"{GCP_PROJECT}.{BQ_DATASET}.{BQ_GRID_TILES_TABLE}"
    grid_fields_ref = f"{GCP_PROJECT}.{BQ_DATASET}.{BQ_GRID_TILE_FIELDS_TABLE}"
    _insert_rows_batched(client, grid_tiles_ref, tile_rows)
    _insert_rows_batched(client, grid_fields_ref, field_rows)

    return total_inserted
