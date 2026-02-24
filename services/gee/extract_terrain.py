#!/usr/bin/env python3
"""Extract terrain context (elevation, slope, aspect, land cover) from GEE.

For each configured city, extracts data from USGS 3DEP 10m DEM and NLCD 2021,
then writes results to BigQuery terrain_context table.

Intended to run as a Cloud Run Job triggered by Cloud Scheduler (annually).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

import ee
from google.cloud import bigquery

from config import BQ_DATASET, GCP_PROJECT, load_cities

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

NLCD_CLASSES = {
    "11": "Open Water",
    "12": "Perennial Ice/Snow",
    "21": "Developed, Open Space",
    "22": "Developed, Low Intensity",
    "23": "Developed, Medium Intensity",
    "24": "Developed, High Intensity",
    "31": "Barren Land",
    "41": "Deciduous Forest",
    "42": "Evergreen Forest",
    "43": "Mixed Forest",
    "51": "Dwarf Scrub",
    "52": "Shrub/Scrub",
    "71": "Grassland/Herbaceous",
    "72": "Sedge/Herbaceous",
    "81": "Pasture/Hay",
    "82": "Cultivated Crops",
    "90": "Woody Wetlands",
    "95": "Emergent Herbaceous Wetlands",
}


def extract_terrain_for_city(city_slug: str, city, bq_client: bigquery.Client) -> dict:
    """Extract terrain data for a single city."""
    logger.info("Extracting terrain for %s (%s)", city_slug, city.name)

    point = ee.Geometry.Point([city.lon, city.lat])
    buffer = point.buffer(10000)  # 10km radius

    # 3DEP 10m DEM
    dem = ee.Image("USGS/3DEP/10m")
    elevation = dem.select("elevation")
    slope = ee.Terrain.slope(elevation)
    aspect = ee.Terrain.aspect(elevation)

    # Elevation stats
    elev_stats = elevation.reduceRegion(
        reducer=ee.Reducer.percentile([10, 25, 50, 75, 90])
        .combine(ee.Reducer.minMax(), sharedInputs=True)
        .combine(ee.Reducer.mean(), sharedInputs=True),
        geometry=buffer,
        scale=30,
        maxPixels=1e7,
    ).getInfo()

    # Slope stats
    slope_stats = slope.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
        geometry=buffer,
        scale=30,
        maxPixels=1e7,
    ).getInfo()

    # Aspect stats
    aspect_stats = aspect.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=buffer,
        scale=30,
        maxPixels=1e7,
    ).getInfo()

    # NLCD 2021 land cover
    nlcd = ee.Image("USGS/NLCD_RELEASES/2021_REL/NLCD/2021").select("landcover")
    lc_hist = nlcd.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=buffer,
        scale=30,
        maxPixels=1e7,
    ).getInfo()

    # Process land cover percentages
    land_cover = {}
    raw_hist = lc_hist.get("landcover", {})
    total = sum(raw_hist.values()) if raw_hist else 1
    for code, count in raw_hist.items():
        name = NLCD_CLASSES.get(str(code), f"Class {code}")
        pct = round(count / total * 100, 1)
        if pct >= 1.0:
            land_cover[name] = pct

    # Build elevation bands data
    elev_bands_data = {
        "configured_bands": [
            {"elevation_m": b, "elevation_ft": round(b * 3.28084)} for b in city.elev_bands
        ],
        "area_stats": {
            "min_m": elev_stats.get("elevation_min"),
            "max_m": elev_stats.get("elevation_max"),
            "mean_m": elev_stats.get("elevation_mean"),
            "p10_m": elev_stats.get("elevation_p10"),
            "p25_m": elev_stats.get("elevation_p25"),
            "median_m": elev_stats.get("elevation_p50"),
            "p75_m": elev_stats.get("elevation_p75"),
            "p90_m": elev_stats.get("elevation_p90"),
        },
    }

    slope_aspect = {
        "mean_slope_deg": slope_stats.get("elevation_slope_mean"),
        "slope_stddev": slope_stats.get("elevation_slope_stdDev"),
        "mean_aspect_deg": aspect_stats.get("elevation_aspect_mean"),
    }

    # Write to BigQuery
    table_ref = f"{GCP_PROJECT}.{BQ_DATASET}.terrain_context"

    # Delete existing row
    delete_query = f"DELETE FROM `{table_ref}` WHERE city_slug = @city_slug"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("city_slug", "STRING", city_slug),
        ]
    )
    bq_client.query(delete_query, job_config=job_config).result()

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

    errors = bq_client.insert_rows_json(table_ref, [row])
    if errors:
        logger.error("BigQuery insert failed for %s: %s", city_slug, errors)
        raise RuntimeError(f"BigQuery insert failed: {errors}")

    logger.info("Wrote terrain context for %s", city_slug)
    return row


def main() -> None:
    """Main entry point for terrain extraction job."""
    logger.info("Starting terrain extraction job")

    ee.Initialize(opt_url="https://earthengine-highvolume.googleapis.com")
    bq_client = bigquery.Client(project=GCP_PROJECT)
    cities = load_cities()

    if not cities:
        logger.error("No cities configured — set CITIES_CONFIG env var")
        sys.exit(1)

    logger.info("Processing %d cities", len(cities))
    success = 0
    failed = 0

    for city_slug, city in cities.items():
        try:
            extract_terrain_for_city(city_slug, city, bq_client)
            success += 1
        except Exception as e:
            logger.error("Failed for %s: %s", city_slug, e)
            failed += 1

    logger.info("Terrain extraction complete: %d success, %d failed", success, failed)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
