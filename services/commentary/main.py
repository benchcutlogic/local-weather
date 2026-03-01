"""Gemini forecast commentary service.

Generates conversational, terrain-aware weather forecast commentary
by querying BigQuery for model data and calling Vertex AI Gemini.
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from google.cloud import bigquery, storage
from pydantic import BaseModel, ValidationError

from bq_queries import (
    get_all_city_slugs,
    get_data_trust_summary,
    get_latest_forecasts,
    get_model_drift,
    get_terrain_context,
    get_verification_scores,
)
from config import GCS_BUCKET, GCP_PROJECT, GEMINI_MODEL, load_cities, CityConfig
from gee_tasks import extract_rtma_for_city, extract_terrain_for_city
from prompt_builder import build_commentary_prompt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CITIES: dict[str, CityConfig] = {}
_gcs_client: storage.Client | None = None
_bq_client: bigquery.Client | None = None


def _get_gcs_client() -> storage.Client:
    global _gcs_client
    if _gcs_client is None:
        _gcs_client = storage.Client(project=GCP_PROJECT)
    return _gcs_client


def _get_bq_client() -> bigquery.Client:
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=GCP_PROJECT)
    return _bq_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    global CITIES
    CITIES = load_cities()
    logger.info("Loaded %d cities: %s", len(CITIES), list(CITIES.keys()))
    yield


app = FastAPI(
    title="Forecast Commentary Service",
    description="Gemini-powered conversational forecast commentary",
    version="1.0.0",
    lifespan=lifespan,
)


class CommentaryResponse(BaseModel):
    city_slug: str
    status: str
    gcs_path: str | None = None
    error: str | None = None


class GenerateAllResponse(BaseModel):
    total_cities: int
    triggered: int
    message: str


class GeeResponse(BaseModel):
    cities_processed: int
    status: str


class DataTrustModel(BaseModel):
    model_name: str
    run_time: str
    latest_valid_time: str
    total_rows: int
    usable_rows: int


class DataTrustResponse(BaseModel):
    city_slug: str
    status: str
    generated_at: str
    models: list[DataTrustModel]


class CommentaryConfidence(BaseModel):
    level: str
    explanation: str


class CommentaryElevationBand(BaseModel):
    elevation_m: int
    elevation_ft: int
    description: str


class CommentaryElevationBreakdown(BaseModel):
    summary: str
    bands: list[CommentaryElevationBand]


class CommentaryPayload(BaseModel):
    city_slug: str
    city_name: str
    generated_at: str
    headline: str
    current_conditions: str
    todays_forecast: str
    model_analysis: str
    elevation_breakdown: CommentaryElevationBreakdown
    extended_outlook: str
    confidence: CommentaryConfidence
    best_model: str
    alerts: list[str]
    updated_at: str


def _has_usable_core_values(row: dict) -> bool:
    return any(
        row.get(k) is not None
        for k in ("temperature_2m", "precip_kg_m2", "wind_speed_10m", "snow_depth", "relative_humidity")
    )


def _build_data_delay_commentary(city_slug: str, city_name: str) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "city_slug": city_slug,
        "city_name": city_name,
        "generated_at": now_iso,
        "headline": "Forecast data is delayed — refreshing shortly",
        "current_conditions": "Our model feed for this city is currently delayed. We are waiting for the next successful ingest cycle.",
        "todays_forecast": "A full model-based forecast is temporarily unavailable. Please check back shortly as new data lands.",
        "model_analysis": "We did not publish a synthetic fallback forecast because current model input coverage is below minimum quality thresholds.",
        "elevation_breakdown": {
            "summary": "Elevation-specific guidance is temporarily unavailable while model data refreshes.",
            "bands": [],
        },
        "extended_outlook": "Extended outlook will repopulate automatically once model data coverage returns.",
        "confidence": {
            "level": "low",
            "explanation": "Confidence is low because the latest model ingest does not yet contain enough usable fields.",
        },
        "best_model": "Unavailable (insufficient current data)",
        "alerts": ["Data delay: model ingest coverage below quality threshold"],
        "updated_at": now_iso,
    }


def _extract_json_payload(raw_response: str) -> dict[str, Any]:
    """Parse Gemini response robustly.

    Handles plain JSON, fenced JSON blocks, and extra leading/trailing text.
    """
    text = raw_response.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])

    raise ValueError("No valid JSON object found in model response")


def _normalize_and_validate_commentary(
    city_slug: str,
    city_name: str,
    commentary_raw: dict[str, Any],
) -> dict[str, Any]:
    """Validate commentary payload schema and return normalized dict."""
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = dict(commentary_raw)
    payload["city_slug"] = city_slug
    payload["city_name"] = city_name
    payload.setdefault("generated_at", now_iso)
    payload.setdefault("updated_at", payload["generated_at"])

    validated = CommentaryPayload.model_validate(payload)
    return validated.model_dump()


async def _call_gemini(prompt: str) -> str:
    """Call Vertex AI Gemini for commentary generation."""
    import vertexai
    from vertexai.generative_models import GenerativeModel, GenerationConfig

    vertexai.init(project=GCP_PROJECT, location="us-central1")
    model = GenerativeModel(GEMINI_MODEL)

    response = model.generate_content(
        prompt,
        generation_config=GenerationConfig(
            temperature=0.7,
            max_output_tokens=4096,
            response_mime_type="application/json",
        ),
    )
    return response.text


def _upload_commentary_to_gcs(city_slug: str, commentary_json: dict) -> str:
    """Upload commentary JSON to GCS bucket."""
    client = _get_gcs_client()
    bucket = client.bucket(GCS_BUCKET)

    # Store as {city_slug}/latest.json and {city_slug}/{timestamp}.json
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for path in [f"{city_slug}/latest.json", f"{city_slug}/{timestamp}.json"]:
        blob = bucket.blob(path)
        blob.upload_from_string(
            json.dumps(commentary_json, indent=2),
            content_type="application/json",
        )
        blob.cache_control = "public, max-age=300"
        blob.patch()

    gcs_path = f"gs://{GCS_BUCKET}/{city_slug}/latest.json"
    logger.info("Uploaded commentary to %s", gcs_path)
    return gcs_path


@app.get("/health")
async def health_check() -> dict:
    return {"status": "healthy", "cities_loaded": len(CITIES)}


@app.post("/generate/{city_slug}", response_model=CommentaryResponse)
async def generate_commentary(city_slug: str) -> CommentaryResponse:
    """Generate forecast commentary for a single city."""
    city = CITIES.get(city_slug)
    if city is None:
        raise HTTPException(status_code=404, detail=f"City not found: {city_slug}")

    try:
        # Gather all data from BigQuery
        forecasts = get_latest_forecasts(city_slug)
        drift_data = get_model_drift(city_slug)
        terrain = get_terrain_context(city_slug)
        scores = get_verification_scores(city_slug)

        logger.info(
            "Data for %s: %d forecasts, %d drift rows, terrain=%s, %d scores",
            city_slug,
            len(forecasts),
            len(drift_data),
            "yes" if terrain else "no",
            len(scores),
        )

        if not forecasts:
            return CommentaryResponse(
                city_slug=city_slug,
                status="skipped",
                error="No forecast data available",
            )

        usable_count = sum(1 for row in forecasts if _has_usable_core_values(row))
        logger.info("Usable forecast rows for %s: %d/%d", city_slug, usable_count, len(forecasts))

        # Quality gate: do not ask LLM to improvise when model fields are effectively missing.
        if usable_count == 0:
            commentary = _build_data_delay_commentary(city_slug=city_slug, city_name=city.name)
            gcs_path = _upload_commentary_to_gcs(city_slug, commentary)
            return CommentaryResponse(
                city_slug=city_slug,
                status="success",
                gcs_path=gcs_path,
            )

        # Build prompt and call Gemini
        prompt = build_commentary_prompt(
            city_slug=city_slug,
            city_name=city.name,
            forecasts=forecasts,
            drift_data=drift_data,
            terrain=terrain,
            verification_scores=scores,
        )

        raw_response = await _call_gemini(prompt)

        try:
            commentary_raw = _extract_json_payload(raw_response)
            commentary = _normalize_and_validate_commentary(
                city_slug=city_slug,
                city_name=city.name,
                commentary_raw=commentary_raw,
            )
        except (ValueError, json.JSONDecodeError, ValidationError) as parse_err:
            logger.warning(
                "Commentary payload invalid for %s (%s). Falling back to data-delay payload.",
                city_slug,
                parse_err,
            )
            commentary = _build_data_delay_commentary(city_slug=city_slug, city_name=city.name)

        # Upload to GCS
        gcs_path = _upload_commentary_to_gcs(city_slug, commentary)

        return CommentaryResponse(
            city_slug=city_slug,
            status="success",
            gcs_path=gcs_path,
        )

    except Exception as e:
        logger.error("Failed to generate commentary for %s: %s", city_slug, e)
        return CommentaryResponse(
            city_slug=city_slug,
            status="error",
            error=str(e),
        )


@app.get("/trust/{city_slug}", response_model=DataTrustResponse)
async def get_data_trust(city_slug: str) -> DataTrustResponse:
    """Return per-model freshness + usable row counts for UI trust contract."""
    city = CITIES.get(city_slug)
    if city is None:
        raise HTTPException(status_code=404, detail=f"City not found: {city_slug}")

    rows = get_data_trust_summary(city_slug)
    models = [
        DataTrustModel(
            model_name=str(r["model_name"]),
            run_time=str(r["run_time"]),
            latest_valid_time=str(r["latest_valid_time"]),
            total_rows=int(r["total_rows"]),
            usable_rows=int(r["usable_rows"]),
        )
        for r in rows
    ]

    return DataTrustResponse(
        city_slug=city_slug,
        status="ok" if models else "missing",
        generated_at=datetime.now(timezone.utc).isoformat(),
        models=models,
    )


@app.post("/generate-all", response_model=GenerateAllResponse)
async def generate_all(background_tasks: BackgroundTasks) -> GenerateAllResponse:
    """Generate commentary for all configured cities (background)."""
    city_slugs = list(CITIES.keys())

    for slug in city_slugs:
        background_tasks.add_task(_generate_city_background, slug)

    return GenerateAllResponse(
        total_cities=len(city_slugs),
        triggered=len(city_slugs),
        message=f"Commentary generation triggered for {len(city_slugs)} cities",
    )


async def _generate_city_background(city_slug: str) -> None:
    """Background task to generate commentary for a single city."""
    try:
        await generate_commentary(city_slug)
    except Exception as e:
        logger.error("Background generation failed for %s: %s", city_slug, e)


@app.post("/trigger-gee-rtma", response_model=GeeResponse)
async def trigger_gee_rtma() -> GeeResponse:
    """Trigger RTMA verification data extraction via Earth Engine."""
    bq_client = _get_bq_client()
    processed = 0

    for city_slug, city in CITIES.items():
        try:
            extract_rtma_for_city(city_slug, city, bq_client)
            processed += 1
        except Exception as e:
            logger.error("RTMA extraction failed for %s: %s", city_slug, e)

    return GeeResponse(cities_processed=processed, status="complete")


@app.post("/trigger-gee-terrain", response_model=GeeResponse)
async def trigger_gee_terrain() -> GeeResponse:
    """Trigger terrain context extraction via Earth Engine."""
    bq_client = _get_bq_client()
    processed = 0

    for city_slug, city in CITIES.items():
        try:
            extract_terrain_for_city(city_slug, city, bq_client)
            processed += 1
        except Exception as e:
            logger.error("Terrain extraction failed for %s: %s", city_slug, e)

    return GeeResponse(cities_processed=processed, status="complete")


if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
