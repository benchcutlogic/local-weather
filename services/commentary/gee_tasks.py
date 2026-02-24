"""Google Earth Engine extraction tasks for terrain context and RTMA verification."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import ee
from google.cloud import bigquery

from config import BQ_DATASET, GCP_PROJECT, CityConfig

logger = logging.getLogger(__name__)

_ee_initialized = False


def _init_ee() -> None:
    """Initialize Earth Engine API."""
    global _ee_initialized
    if not _ee_initialized:
        ee.Initialize(opt_url="https://earthengine-highvolume.googleapis.com")
        _ee_initialized = True


def extract_terrain_for_city(
    city_slug: str, city: CityConfig, bq_client: bigquery.Client
) -> dict:
    """Extract terrain context from 3DEP and NLCD for a city.

    Writes results to BigQuery terrain_context table.
    """
    _init_ee()

    point = ee.Geometry.Point([city.lon, city.lat])
    # 10km buffer around city center for terrain analysis
    buffer = point.buffer(10000)

    # 3DEP 10m DEM for elevation, slope, aspect
    dem = ee.Image("USGS/3DEP/10m")
    elevation = dem.select("elevation")
    slope = ee.Terrain.slope(elevation)
    aspect = ee.Terrain.aspect(elevation)

    # Sample elevation statistics within buffer
    elev_stats = elevation.reduceRegion(
        reducer=ee.Reducer.percentile([10, 25, 50, 75, 90]).combine(
            ee.Reducer.minMax(), sharedInputs=True
        ),
        geometry=buffer,
        scale=30,
        maxPixels=1e7,
    ).getInfo()

    # Slope and aspect stats
    slope_stats = slope.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
        geometry=buffer,
        scale=30,
        maxPixels=1e7,
    ).getInfo()

    aspect_stats = aspect.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=buffer,
        scale=30,
        maxPixels=1e7,
    ).getInfo()

    # NLCD land cover classification
    nlcd = ee.Image("USGS/NLCD_RELEASES/2021_REL/NLCD/2021").select("landcover")
    lc_hist = nlcd.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=buffer,
        scale=30,
        maxPixels=1e7,
    ).getInfo()

    # NLCD class names
    nlcd_classes = {
        "11": "Open Water", "12": "Perennial Ice/Snow",
        "21": "Developed, Open Space", "22": "Developed, Low Intensity",
        "23": "Developed, Medium Intensity", "24": "Developed, High Intensity",
        "31": "Barren Land", "41": "Deciduous Forest",
        "42": "Evergreen Forest", "43": "Mixed Forest",
        "51": "Dwarf Scrub", "52": "Shrub/Scrub",
        "71": "Grassland/Herbaceous", "72": "Sedge/Herbaceous",
        "81": "Pasture/Hay", "82": "Cultivated Crops",
        "90": "Woody Wetlands", "95": "Emergent Herbaceous Wetlands",
    }

    land_cover = {}
    raw_hist = lc_hist.get("landcover", {})
    total = sum(raw_hist.values()) if raw_hist else 1
    for code, count in raw_hist.items():
        name = nlcd_classes.get(str(code), f"Class {code}")
        pct = round(count / total * 100, 1)
        if pct >= 1.0:  # Only include classes >= 1%
            land_cover[name] = pct

    # Build elevation bands config
    elev_bands_data = []
    for band in city.elev_bands:
        elev_bands_data.append({
            "elevation_m": band,
            "elevation_ft": round(band * 3.28084),
        })

    slope_aspect = {
        "mean_slope_deg": slope_stats.get("elevation_slope_mean"),
        "slope_stddev": slope_stats.get("elevation_slope_stdDev"),
        "mean_aspect_deg": aspect_stats.get("elevation_aspect_mean"),
    }

    # Write to BigQuery
    row = {
        "city_slug": city_slug,
        "city_name": city.name,
        "lat": city.lat,
        "lon": city.lon,
        "elevation_bands_json": json.dumps(elev_bands_data),
        "land_cover_json": json.dumps(land_cover),
        "slope_aspect_json": json.dumps(slope_aspect),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    table_ref = f"{GCP_PROJECT}.{BQ_DATASET}.terrain_context"

    # Delete existing row for this city, then insert
    delete_query = f"""
    DELETE FROM `{table_ref}`
    WHERE city_slug = @city_slug
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("city_slug", "STRING", city_slug),
        ]
    )
    bq_client.query(delete_query, job_config=job_config).result()

    errors = bq_client.insert_rows_json(table_ref, [row])
    if errors:
        logger.error("Failed to write terrain for %s: %s", city_slug, errors)
        raise RuntimeError(f"BigQuery insert failed: {errors}")

    logger.info("Wrote terrain context for %s", city_slug)
    return row


def extract_rtma_for_city(
    city_slug: str,
    city: CityConfig,
    bq_client: bigquery.Client,
    target_date: datetime | None = None,
) -> list[dict]:
    """Extract yesterday's hourly RTMA verification data for a city.

    RTMA (Real-Time Mesoscale Analysis) provides gridded observations
    for verifying model forecasts.
    """
    _init_ee()

    if target_date is None:
        target_date = datetime.now(timezone.utc) - timedelta(days=1)

    start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    point = ee.Geometry.Point([city.lon, city.lat])

    # RTMA dataset in GEE
    rtma = (
        ee.ImageCollection("NOAA/NWS/RTMA")
        .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        .filterBounds(point)
    )

    n_images = rtma.size().getInfo()
    logger.info("Found %d RTMA images for %s on %s", n_images, city_slug, start.date())

    if n_images == 0:
        return []

    rows: list[dict] = []

    def _extract_image(img):
        img = ee.Image(img)
        info = img.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=2500,
        ).getInfo()

        timestamp = img.get("system:time_start").getInfo()

        return {
            "timestamp": timestamp,
            "temp": info.get("TMP"),
            "precip": info.get("APCP"),
            "wind": info.get("WIND"),
        }

    image_list = rtma.toList(rtma.size())
    for i in range(n_images):
        try:
            img = ee.Image(image_list.get(i))
            info = img.reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=point,
                scale=2500,
            ).getInfo()

            timestamp_ms = img.get("system:time_start").getInfo()
            valid_time = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)

            row = {
                "city_slug": city_slug,
                "valid_time": valid_time.isoformat(),
                "obs_temp_2m": info.get("TMP"),  # Already in K
                "obs_precip": info.get("APCP"),
                "obs_wind_speed": info.get("WIND"),
                "obs_snow_depth": None,  # RTMA doesn't have snow depth
                "source": "RTMA",
            }
            rows.append(row)
        except Exception as e:
            logger.warning("Failed to extract RTMA image %d for %s: %s", i, city_slug, e)

    if rows:
        table_ref = f"{GCP_PROJECT}.{BQ_DATASET}.ground_truth"
        errors = bq_client.insert_rows_json(table_ref, rows)
        if errors:
            logger.error("Failed to write RTMA for %s: %s", city_slug, errors)
        else:
            logger.info("Wrote %d RTMA rows for %s", len(rows), city_slug)

    return rows
