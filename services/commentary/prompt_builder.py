"""Build structured prompts for Gemini forecast commentary generation.

Produces conversational, terrain-aware forecasts in the style of durangoweatherguy.com,
mentioning model agreement/disagreement, elevation band differences, and local context.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone


def _k_to_f(k: float | None) -> str:
    """Convert Kelvin to Fahrenheit, formatted."""
    if k is None:
        return "N/A"
    f = (k - 273.15) * 9 / 5 + 32
    return f"{f:.0f}F"


def _ms_to_mph(ms: float | None) -> str:
    """Convert m/s to mph, formatted."""
    if ms is None:
        return "N/A"
    return f"{ms * 2.237:.0f} mph"


def _m_to_in(m: float | None) -> str:
    """Convert meters to inches, formatted."""
    if m is None:
        return "N/A"
    return f"{m * 39.3701:.1f} in"


def _m_to_ft(m: float | None) -> str:
    """Convert meters to feet, formatted."""
    if m is None:
        return "N/A"
    return f"{m * 3.28084:.0f} ft"


def _kg_m2_to_in(kg: float | None) -> str:
    """Convert kg/m2 (mm) precip to inches."""
    if kg is None:
        return "N/A"
    return f"{kg * 0.0393701:.2f} in"


def _format_forecasts_by_model(forecasts: list[dict]) -> str:
    """Format forecast data grouped by model for the prompt."""
    if not forecasts:
        return "No forecast data available."

    models: dict[str, list[dict]] = {}
    for row in forecasts:
        model = row["model_name"]
        if model not in models:
            models[model] = []
        models[model].append(row)

    sections: list[str] = []
    for model_name, rows in models.items():
        run_time = rows[0].get("run_time", "unknown")
        section = f"### {model_name} (run: {run_time})\n"

        # Group by valid_time, show surface + elevation bands
        by_time: dict[str, list[dict]] = {}
        for row in rows:
            vt = str(row.get("valid_time", ""))
            if vt not in by_time:
                by_time[vt] = []
            by_time[vt].append(row)

        for vt, time_rows in list(by_time.items())[:8]:  # Limit to first 8 timesteps
            surface = next((r for r in time_rows if r.get("elevation_band") is None), None)
            if surface:
                section += (
                    f"  {vt}: Temp={_k_to_f(surface.get('temperature_2m'))}, "
                    f"Wind={_ms_to_mph(surface.get('wind_speed_10m'))}, "
                    f"Precip={_kg_m2_to_in(surface.get('precip_kg_m2'))}, "
                    f"Snow={_m_to_in(surface.get('snow_depth'))}, "
                    f"Freezing={_m_to_ft(surface.get('freezing_level_m'))}, "
                    f"CAPE={surface.get('cape', 'N/A')}, "
                    f"RH={surface.get('relative_humidity', 'N/A')}%\n"
                )

            # Elevation bands
            elev_rows = sorted(
                [r for r in time_rows if r.get("elevation_band") is not None],
                key=lambda r: r.get("elevation_band", 0),
            )
            for er in elev_rows:
                section += (
                    f"    @{er['elevation_band']}m: "
                    f"Temp={_k_to_f(er.get('temperature_2m'))}\n"
                )

        sections.append(section)

    return "\n".join(sections)


def _format_drift(drift_data: list[dict]) -> str:
    """Format model drift data for the prompt."""
    if not drift_data:
        return "No drift data available (first run or insufficient history)."

    lines: list[str] = []
    for row in drift_data[:20]:  # Limit
        model = row.get("model_name", "?")
        vt = row.get("valid_time", "?")
        temp_drift = row.get("temp_drift_vs_last_run")
        precip_drift = row.get("precip_drift_vs_last_run")
        snow_drift = row.get("snow_drift_vs_last_run")
        lines.append(
            f"  {model} valid={vt}: "
            f"temp_drift={'+' if temp_drift and temp_drift > 0 else ''}{temp_drift or 0:.1f}K, "
            f"precip_drift={precip_drift or 0:.2f}kg/m2, "
            f"snow_drift={snow_drift or 0:.3f}m"
        )

    return "\n".join(lines)


def _format_terrain(terrain: dict | None) -> str:
    """Format terrain context for the prompt."""
    if terrain is None:
        return "No terrain context available."

    parts = [
        f"City: {terrain.get('city_name', '?')}",
        f"Location: {terrain.get('lat', '?')}N, {terrain.get('lon', '?')}W",
    ]

    elev = terrain.get("elevation_bands_json")
    if elev:
        if isinstance(elev, str):
            elev = json.loads(elev)
        parts.append(f"Elevation bands: {json.dumps(elev)}")

    lc = terrain.get("land_cover_json")
    if lc:
        if isinstance(lc, str):
            lc = json.loads(lc)
        parts.append(f"Land cover: {json.dumps(lc)}")

    sa = terrain.get("slope_aspect_json")
    if sa:
        if isinstance(sa, str):
            sa = json.loads(sa)
        parts.append(f"Slope/aspect: {json.dumps(sa)}")

    return "\n".join(parts)


def _format_verification(scores: list[dict]) -> str:
    """Format verification scores for the prompt."""
    if not scores:
        return "No verification scores available yet."

    lines: list[str] = []
    for row in scores:
        model = row.get("model_name", "?")
        n = row.get("num_comparisons", 0)
        temp_rmse = row.get("temp_rmse")
        precip_mae = row.get("precip_mae")
        lines.append(
            f"  {model}: "
            f"n={n}, "
            f"temp_RMSE={temp_rmse:.2f}K" if temp_rmse else f"  {model}: n={n}, temp_RMSE=N/A"
        )
        if precip_mae is not None:
            lines[-1] += f", precip_MAE={precip_mae:.2f}kg/m2"

    return "\n".join(lines)


def build_commentary_prompt(
    city_slug: str,
    city_name: str,
    forecasts: list[dict],
    drift_data: list[dict],
    terrain: dict | None,
    verification_scores: list[dict],
) -> str:
    """Build the full prompt for Gemini to generate forecast commentary."""
    now = datetime.now(timezone.utc)

    return f"""You are a hyperlocal weather forecaster writing for {city_name}. Write in a conversational,
engaging style similar to durangoweatherguy.com — knowledgeable but approachable, like you're talking to
a neighbor over the fence. You deeply understand mountain/terrain weather and local microclimates.

Current UTC time: {now.isoformat()}

## Your Task
Generate a comprehensive forecast commentary for {city_name} ({city_slug}). Include:

1. **Current Conditions Summary** — What's happening right now based on the latest model data
2. **Today's Forecast** — Temperature highs/lows, wind, precipitation chances
3. **Model Agreement/Disagreement** — Where models agree and where they diverge. If models are trending
   in a consistent direction (drift), mention that. If one model is an outlier, call it out.
4. **Elevation Band Breakdown** — How conditions vary across elevation bands. What's the snow level?
   Where's it raining vs snowing? Temperature inversions?
5. **Extended Outlook** (3-7 days) — General trend from longer-range models
6. **Confidence Level** — Based on model agreement, drift trends, and verification scores, how confident
   are you in this forecast? Which model has been most accurate here recently?

## Terrain Context
{_format_terrain(terrain)}

## Latest Model Forecasts
{_format_forecasts_by_model(forecasts)}

## Model Drift (Run-to-Run Changes)
{_format_drift(drift_data)}

## Model Verification Scores (30-day rolling)
{_format_verification(verification_scores)}

## Output Format
Respond with a JSON object containing these fields:
{{
    "city_slug": "{city_slug}",
    "city_name": "{city_name}",
    "generated_at": "<ISO timestamp>",
    "headline": "<catchy 1-line summary, e.g. 'Snow levels dropping tonight — powder day potential above 9,000ft'>",
    "current_conditions": "<2-3 sentence summary>",
    "todays_forecast": "<3-5 sentences, conversational>",
    "model_analysis": "<2-4 sentences about model agreement/disagreement/drift>",
    "elevation_breakdown": {{
        "summary": "<2-3 sentences>",
        "bands": [
            {{"elevation_m": <int>, "elevation_ft": <int>, "description": "<1-2 sentences>"}}
        ]
    }},
    "extended_outlook": "<3-5 sentences covering days 2-7>",
    "confidence": {{
        "level": "<high|moderate|low>",
        "explanation": "<1-2 sentences>"
    }},
    "best_model": "<which model has been most accurate here, based on verification scores>",
    "alerts": ["<any notable weather alerts or warnings>"],
    "updated_at": "<ISO timestamp>"
}}

Write naturally and engagingly. Don't just list numbers — interpret them. Say things like "the HRRR has been
flip-flopping on snow totals" or "all models are in rare agreement on a dry weekend." Reference specific
elevations in feet for US audiences. Mention local terrain features when relevant.
"""
