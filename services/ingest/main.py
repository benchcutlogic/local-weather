"""GRIB2 byte-range ingestion service for hyperlocal weather platform.

Receives Pub/Sub push notifications and Cloud Scheduler triggers to ingest
NWP model data from NOAA GCS buckets, extract values for configured cities,
and stream results to BigQuery.
"""

from __future__ import annotations

import base64
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

from bigquery_writer import write_forecast_points
from config import load_cities, CityConfig
from grib2_reader import (
    get_default_forecast_hours,
    get_latest_run_time,
    read_grib2_for_cities,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CITIES: dict[str, CityConfig] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global CITIES
    CITIES = load_cities()
    logger.info("Loaded %d cities: %s", len(CITIES), list(CITIES.keys()))
    yield


app = FastAPI(
    title="GRIB2 Ingest Service",
    description="Byte-range GRIB2 ingestion for hyperlocal weather forecasts",
    version="1.0.0",
    lifespan=lifespan,
)


class IngestResponse(BaseModel):
    model: str
    run_time: str
    forecast_hours: int
    cities_processed: int
    rows_written: int


class PubSubMessage(BaseModel):
    message: dict
    subscription: str | None = None


@app.get("/health")
async def health_check() -> dict:
    return {"status": "healthy", "cities_loaded": len(CITIES)}


async def _run_ingestion(
    model: str,
    run_time: datetime | None = None,
    forecast_hours: list[int] | None = None,
) -> IngestResponse:
    """Core ingestion logic shared by all endpoints."""
    if not CITIES:
        raise HTTPException(status_code=500, detail="No cities configured")

    if run_time is None:
        run_time = get_latest_run_time(model)

    if forecast_hours is None:
        forecast_hours = get_default_forecast_hours(model)

    logger.info(
        "Starting %s ingestion: run_time=%s, hours=%d-%d, cities=%d",
        model.upper(),
        run_time.isoformat(),
        forecast_hours[0],
        forecast_hours[-1],
        len(CITIES),
    )

    points = await read_grib2_for_cities(model, run_time, forecast_hours, CITIES)
    rows_written = await write_forecast_points(points)

    logger.info(
        "Completed %s ingestion: %d points extracted, %d rows written",
        model.upper(),
        len(points),
        rows_written,
    )

    return IngestResponse(
        model=model.upper(),
        run_time=run_time.isoformat(),
        forecast_hours=len(forecast_hours),
        cities_processed=len(CITIES),
        rows_written=rows_written,
    )


@app.post("/ingest/hrrr", response_model=IngestResponse)
async def ingest_hrrr(request: Request) -> IngestResponse:
    """Ingest HRRR model data. Triggered by Pub/Sub push or Cloud Scheduler."""
    # Check if this is a Pub/Sub push message
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            if "message" in body:
                return await _handle_pubsub_hrrr(body)
        except json.JSONDecodeError:
            pass

    return await _run_ingestion("hrrr")


async def _handle_pubsub_hrrr(body: dict) -> IngestResponse:
    """Handle Pub/Sub push notification for HRRR data availability."""
    message = body.get("message", {})
    data_b64 = message.get("data", "")

    if data_b64:
        try:
            data = json.loads(base64.b64decode(data_b64).decode("utf-8"))
            logger.info("Pub/Sub HRRR notification: %s", data)

            # Extract run info from notification
            # NOAA notifications typically contain the GCS object path
            object_name = data.get("name", data.get("objectId", ""))
            if object_name:
                # Parse run time from filename like hrrr.20240101/conus/hrrr.t00z.wrfsfcf00.grib2
                import re
                match = re.search(r"hrrr\.(\d{8})/conus/hrrr\.t(\d{2})z", object_name)
                if match:
                    date_str, hour_str = match.groups()
                    run_time = datetime.strptime(
                        f"{date_str}{hour_str}", "%Y%m%d%H"
                    ).replace(tzinfo=timezone.utc)
                    return await _run_ingestion("hrrr", run_time=run_time)
        except Exception as e:
            logger.warning("Failed to parse Pub/Sub message: %s", e)

    return await _run_ingestion("hrrr")


@app.post("/ingest/gfs", response_model=IngestResponse)
async def ingest_gfs() -> IngestResponse:
    """Ingest GFS model data. Triggered by Cloud Scheduler."""
    return await _run_ingestion("gfs")


@app.post("/ingest/nam", response_model=IngestResponse)
async def ingest_nam() -> IngestResponse:
    """Ingest NAM model data. Triggered by Cloud Scheduler."""
    return await _run_ingestion("nam")


@app.post("/ingest/ecmwf", response_model=IngestResponse)
async def ingest_ecmwf() -> IngestResponse:
    """Ingest ECMWF model data. Triggered by Cloud Scheduler."""
    return await _run_ingestion("ecmwf")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
