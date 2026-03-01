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
    get_best_model_by_horizon,
    get_data_trust_summary,
    get_latest_forecasts,
    get_model_drift,
    get_terrain_context,
    get_verification_scores,
    get_verification_scores_by_zone,
)
from config import GCS_BUCKET, GCP_PROJECT, GEMINI_MODEL, load_cities, CityConfig
from gee_tasks import extract_rtma_for_city, extract_terrain_for_city
from prompt_builder import build_commentary_prompt
from tone_profiles import get_tone_profile, TONE_PROFILES, DEFAULT_TONE

MICROZONES: dict[str, list[dict]] = {}


def _load_microzones() -> dict[str, list[dict]]:
    """Load microzone definitions from config file."""
    import os
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "microzones.json")
    config_path = os.path.normpath(config_path)
    if not os.path.exists(config_path):
        return {}
    with open(config_path) as f:
        data = json.load(f)
    return data.get("microzones", {})

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
    global CITIES, MICROZONES
    CITIES = load_cities()
    MICROZONES = _load_microzones()
    logger.info("Loaded %d cities: %s", len(CITIES), list(CITIES.keys()))
    logger.info("Loaded microzones for: %s", list(MICROZONES.keys()))
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


class HorizonConfidence(BaseModel):
    immediate_0_6h: str
    short_6_48h: str
    extended_48h_plus: str


class DaypartPayload(BaseModel):
    am: str = ""
    pm: str = ""
    night: str = ""


class ModelDisagreement(BaseModel):
    level: str = "low"
    summary: str = ""
    biggest_spread_metric: str = ""
    biggest_spread_value: str = ""
    confidence_trend: str = "stable"


class MicrozoneInfo(BaseModel):
    zone_id: str
    name: str
    slug: str
    priority: int
    elevation_range_m: list[int]
    description: str


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
    horizon_confidence: HorizonConfidence
    dayparts: DaypartPayload | None = None
    changes: list[str] = []
    model_disagreement: ModelDisagreement | None = None
    tone: str = "professional"
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
        "horizon_confidence": {
            "immediate_0_6h": "Low confidence: near-term model inputs currently delayed.",
            "short_6_48h": "Low confidence: short-range blend unavailable until ingest recovers.",
            "extended_48h_plus": "Low confidence: extended trend withheld due upstream data delay.",
        },
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
    payload.setdefault(
        "horizon_confidence",
        {
            "immediate_0_6h": "Moderate confidence based on available near-term model coverage.",
            "short_6_48h": "Moderate confidence from blended short-range guidance.",
            "extended_48h_plus": "Lower confidence expected for longer-range trend framing.",
        },
    )
    # Ensure new structured fields have defaults for backward compat
    payload.setdefault("dayparts", {"am": "", "pm": "", "night": ""})
    payload.setdefault("changes", [])
    payload.setdefault("model_disagreement", {
        "level": "low",
        "summary": "",
        "biggest_spread_metric": "",
        "biggest_spread_value": "",
        "confidence_trend": "stable",
    })
    payload.setdefault("tone", "professional")

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


@app.get("/verification/{city_slug}")
async def get_verification(city_slug: str, zone_id: str | None = None) -> dict:
    """Return rolling verification scores for a city, optionally by zone.

    Closes #38: rolling microclimate verification scores.
    """
    city = CITIES.get(city_slug)
    if city is None:
        raise HTTPException(status_code=404, detail=f"City not found: {city_slug}")

    scores = get_verification_scores_by_zone(city_slug, zone_id)
    best_models = get_best_model_by_horizon(city_slug)

    return {
        "city_slug": city_slug,
        "zone_id": zone_id,
        "scores": scores,
        "best_model_by_horizon": best_models,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/microzones/{city_slug}")
async def get_microzones(city_slug: str) -> dict:
    """Return microzone definitions for a city."""
    zones = MICROZONES.get(city_slug, [])
    return {
        "city_slug": city_slug,
        "microzones": [
            MicrozoneInfo(
                zone_id=z["zone_id"],
                name=z["name"],
                slug=z["slug"],
                priority=z["priority"],
                elevation_range_m=z["elevation_range_m"],
                description=z["description"],
            ).model_dump()
            for z in zones
        ],
    }


@app.get("/tones")
async def list_tones() -> dict:
    """Return available tone profiles."""
    return {
        "tones": [
            {"slug": t.slug, "label": t.label}
            for t in TONE_PROFILES.values()
        ],
        "default": DEFAULT_TONE,
    }


@app.post("/generate/{city_slug}", response_model=CommentaryResponse)
async def generate_commentary(city_slug: str, tone: str | None = None) -> CommentaryResponse:
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
        tone_profile = get_tone_profile(tone)
        city_microzones = MICROZONES.get(city_slug, [])

        prompt = build_commentary_prompt(
            city_slug=city_slug,
            city_name=city.name,
            forecasts=forecasts,
            drift_data=drift_data,
            terrain=terrain,
            verification_scores=scores,
            tone_instruction=tone_profile.system_instruction,
            microzones=city_microzones,
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
