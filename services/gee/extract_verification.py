#!/usr/bin/env python3
"""Extract RTMA verification data from Google Earth Engine.

Pulls yesterday's hourly RTMA (Real-Time Mesoscale Analysis) observations
for all configured cities and writes to BigQuery ground_truth table.

Intended to run as a Cloud Run Job triggered daily at 4 AM UTC.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone

import ee
from google.cloud import bigquery

from config import BQ_DATASET, GCP_PROJECT, load_cities

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def extract_rtma_for_city(
    city_slug: str,
    city,
    bq_client: bigquery.Client,
    target_date: datetime,
) -> int:
    """Extract RTMA data for a single city for a given date.

    Returns number of rows written.
    """
    logger.info("Extracting RTMA for %s on %s", city_slug, target_date.date())

    point = ee.Geometry.Point([city.lon, city.lat])

    start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    rtma = (
        ee.ImageCollection("NOAA/NWS/RTMA")
        .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        .filterBounds(point)
    )

    n_images = rtma.size().getInfo()
    logger.info("Found %d RTMA images for %s", n_images, city_slug)

    if n_images == 0:
        return 0

    image_list = rtma.toList(n_images)
    rows: list[dict] = []

    for i in range(n_images):
        try:
            img = ee.Image(image_list.get(i))

            values = img.reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=point,
                scale=2500,
            ).getInfo()

            timestamp_ms = img.get("system:time_start").getInfo()
            valid_time = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)

            row = {
                "city_slug": city_slug,
                "valid_time": valid_time.isoformat(),
                "obs_temp_2m": values.get("TMP"),
                "obs_precip": values.get("APCP"),
                "obs_wind_speed": values.get("WIND"),
                "obs_snow_depth": None,
                "source": "RTMA",
            }
            rows.append(row)
        except Exception as e:
            logger.warning("Failed on image %d for %s: %s", i, city_slug, e)

    if not rows:
        return 0

    # Write to BigQuery
    table_ref = f"{GCP_PROJECT}.{BQ_DATASET}.ground_truth"
    errors = bq_client.insert_rows_json(table_ref, rows)

    if errors:
        logger.error("BigQuery insert errors for %s: %s", city_slug, errors)
        return 0

    logger.info("Wrote %d RTMA rows for %s", len(rows), city_slug)
    return len(rows)


def main() -> None:
    """Main entry point for RTMA verification extraction job."""
    logger.info("Starting RTMA verification extraction")

    ee.Initialize(opt_url="https://earthengine-highvolume.googleapis.com")
    bq_client = bigquery.Client(project=GCP_PROJECT)
    cities = load_cities()

    if not cities:
        logger.error("No cities configured — set CITIES_CONFIG env var")
        sys.exit(1)

    # Default to yesterday
    target_date = datetime.now(timezone.utc) - timedelta(days=1)
    logger.info("Target date: %s", target_date.date())
    logger.info("Processing %d cities", len(cities))

    total_rows = 0
    success = 0
    failed = 0

    for city_slug, city in cities.items():
        try:
            n = extract_rtma_for_city(city_slug, city, bq_client, target_date)
            total_rows += n
            success += 1
        except Exception as e:
            logger.error("Failed for %s: %s", city_slug, e)
            failed += 1

    logger.info(
        "RTMA extraction complete: %d cities success, %d failed, %d total rows",
        success,
        failed,
        total_rows,
    )

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
