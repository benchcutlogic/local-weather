"""Build structured prompts for Gemini forecast commentary generation.

Produces conversational, terrain-aware forecasts in the style of durangoweatherguy.com,
mentioning model agreement/disagreement, elevation band differences, and local context.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone


def _k_to_f(k: float | None) -> str | None:
    """Convert Kelvin to Fahrenheit, formatted."""
    if k is None:
        return None
    f = (k - 273.15) * 9 / 5 + 32
    return f"{f:.0f}F"


def _ms_to_mph(ms: float | None) -> str | None:
    """Convert m/s to mph, formatted."""
    if ms is None:
        return None
    return f"{ms * 2.237:.0f} mph"


def _m_to_in(m: float | None) -> str | None:
    """Convert meters to inches, formatted."""
    if m is None:
        return None
    return f"{m * 39.3701:.1f} in"


def _m_to_ft(m: float | None) -> str | None:
    """Convert meters to feet, formatted."""
    if m is None:
        return None
    return f"{m * 3.28084:.0f} ft"


def _kg_m2_to_in(kg: float | None) -> str | None:
    """Convert kg/m2 (mm) precip to inches."""
    if kg is None:
        return None
    return f"{kg * 0.0393701:.2f} in"


def _format_forecasts_by_model(forecasts: list[dict]) -> str:
    """Format forecast data grouped by model for the prompt.

    Avoid flooding the model prompt with explicit N/A values; include only available
    metrics and annotate sparse timesteps when needed.
    """
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

        by_time: dict[str, list[dict]] = {}
        for row in rows:
            vt = str(row.get("valid_time", ""))
            if vt not in by_time:
                by_time[vt] = []
            by_time[vt].append(row)

        for vt, time_rows in list(by_time.items())[:8]:
            surface = next((r for r in time_rows if r.get("elevation_band") is None), None)
            if surface:
                parts: list[str] = []
                temp = _k_to_f(surface.get("temperature_2m"))
                wind = _ms_to_mph(surface.get("wind_speed_10m"))
                precip = _kg_m2_to_in(surface.get("precip_kg_m2"))
                snow = _m_to_in(surface.get("snow_depth"))
                freezing = _m_to_ft(surface.get("freezing_level_m"))
                cape = surface.get("cape")
                rh = surface.get("relative_humidity")

                if temp is not None:
                    parts.append(f"Temp={temp}")
                if wind is not None:
                    parts.append(f"Wind={wind}")
                if precip is not None:
                    parts.append(f"Precip={precip}")
                if snow is not None:
                    parts.append(f"Snow={snow}")
                if freezing is not None:
                    parts.append(f"Freezing={freezing}")
                if cape is not None:
                    parts.append(f"CAPE={cape}")
                if rh is not None:
                    parts.append(f"RH={rh}%")

                if not parts:
                    parts.append("no core fields available at this timestep")

                section += f"  {vt}: " + ", ".join(parts) + "\n"

            elev_rows = sorted(
                [r for r in time_rows if r.get("elevation_band") is not None],
                key=lambda r: r.get("elevation_band", 0),
            )
            for er in elev_rows:
                temp = _k_to_f(er.get("temperature_2m"))
                if temp is None:
                    continue
                section += f"    @{er['elevation_band']}m: Temp={temp}\n"

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


def _data_availability_summary(forecasts: list[dict]) -> str:
    """Summarize usable data coverage per model."""
    if not forecasts:
        return "No forecast rows available."

    per_model: dict[str, dict[str, int]] = {}
    for row in forecasts:
        model = row.get("model_name", "UNKNOWN")
        m = per_model.setdefault(model, {"rows": 0, "usable": 0, "surface": 0, "surface_usable": 0})
        m["rows"] += 1
        usable = any(
            row.get(k) is not None
            for k in ("temperature_2m", "precip_kg_m2", "wind_speed_10m", "snow_depth", "relative_humidity")
        )
        if usable:
            m["usable"] += 1
        if row.get("elevation_band") is None:
            m["surface"] += 1
            if usable:
                m["surface_usable"] += 1

    lines = []
    for model, stats in sorted(per_model.items()):
        lines.append(
            f"- {model}: rows={stats['rows']}, usable_rows={stats['usable']}, "
            f"surface_rows={stats['surface']}, surface_usable={stats['surface_usable']}"
        )
    return "\n".join(lines)


def _hours_ahead(valid_time: object, now: datetime) -> float | None:
    """Return forecast lead time in hours, or None when unavailable."""
    if valid_time is None:
        return None

    if isinstance(valid_time, datetime):
        vt = valid_time
    else:
        try:
            vt = datetime.fromisoformat(str(valid_time).replace("Z", "+00:00"))
        except ValueError:
            return None

    if vt.tzinfo is None:
        vt = vt.replace(tzinfo=timezone.utc)

    return (vt - now).total_seconds() / 3600.0


def _horizon_bucket(hours_ahead: float | None) -> str:
    if hours_ahead is None:
        return "unknown"
    if hours_ahead <= 6:
        return "immediate_0_6h"
    if hours_ahead <= 48:
        return "short_6_48h"
    return "extended_48h_plus"


HORIZON_MODEL_PRIORITY: dict[str, list[str]] = {
    "immediate_0_6h": ["HRRR", "NAMNEST", "NAM", "GFS", "ECMWF", "GEFS"],
    "short_6_48h": ["NAMNEST", "NAM", "GFS", "ECMWF", "HRRR", "GEFS"],
    "extended_48h_plus": ["ECMWF", "GFS", "GEFS", "NAM", "NAMNEST", "HRRR"],
}


def select_models_for_horizon(available_models: set[str], horizon: str) -> list[str]:
    """Select models for a horizon according to explicit priority rules."""
    priority = HORIZON_MODEL_PRIORITY.get(horizon, [])
    selected = [m for m in priority if m in available_models]

    if selected:
        return selected

    # Graceful fallback: use whatever exists.
    return sorted(available_models)


def _horizon_blend_summary(forecasts: list[dict], now: datetime) -> str:
    """Create explicit horizon/model guidance section for the LLM prompt."""
    if not forecasts:
        return "No horizon blend guidance available (no forecasts)."

    models_by_horizon: dict[str, set[str]] = {
        "immediate_0_6h": set(),
        "short_6_48h": set(),
        "extended_48h_plus": set(),
    }

    for row in forecasts:
        model = str(row.get("model_name", "")).upper().strip()
        if not model:
            continue
        hrs = _hours_ahead(row.get("valid_time"), now)
        bucket = _horizon_bucket(hrs)
        if bucket in models_by_horizon:
            models_by_horizon[bucket].add(model)

    lines: list[str] = []
    for bucket in ("immediate_0_6h", "short_6_48h", "extended_48h_plus"):
        available = models_by_horizon[bucket]
        selected = select_models_for_horizon(available, bucket)
        lines.append(
            f"- {bucket}: selected={','.join(selected) if selected else 'none'}; "
            f"available={','.join(sorted(available)) if available else 'none'}"
        )

    return "\n".join(lines)


def _model_disagreement_summary(forecasts: list[dict]) -> str:
    """Compute model spread metrics for temperature and precip at overlapping valid times."""
    if not forecasts:
        return "No model disagreement data (insufficient forecasts)."

    by_time: dict[str, dict[str, dict[str, float | None]]] = {}
    for row in forecasts:
        if row.get("elevation_band") is not None:
            continue
        vt = str(row.get("valid_time", ""))
        model = str(row.get("model_name", ""))
        if not vt or not model:
            continue
        if vt not in by_time:
            by_time[vt] = {}
        by_time[vt][model] = {
            "temp_k": row.get("temperature_2m"),
            "precip": row.get("precip_kg_m2"),
        }

    lines: list[str] = []
    for vt in sorted(by_time.keys())[:8]:
        models = by_time[vt]
        if len(models) < 2:
            continue
        temps = [v["temp_k"] for v in models.values() if v.get("temp_k") is not None]
        precips = [v["precip"] for v in models.values() if v.get("precip") is not None]
        parts = [f"valid={vt}, models={','.join(sorted(models.keys()))}"]
        if len(temps) >= 2:
            spread_f = (max(temps) - min(temps)) * 9 / 5
            parts.append(f"temp_spread={spread_f:.1f}F")
        if len(precips) >= 2:
            spread_in = (max(precips) - min(precips)) * 0.0393701
            parts.append(f"precip_spread={spread_in:.2f}in")
        lines.append("  " + ", ".join(parts))

    if not lines:
        return "Insufficient overlapping timesteps to compute model disagreement."
    return "\n".join(lines)


def build_commentary_prompt(
    city_slug: str,
    city_name: str,
    forecasts: list[dict],
    drift_data: list[dict],
    terrain: dict | None,
    verification_scores: list[dict],
    *,
    tone_instruction: str = "",
    microzones: list[dict] | None = None,
) -> str:
    """Build the full prompt for Gemini to generate forecast commentary."""
    now = datetime.now(timezone.utc)

    microzone_section = ""
    if microzones:
        zone_lines = []
        for z in microzones:
            zone_lines.append(
                f"- {z['name']} ({z['zone_id']}): elev {z['elevation_range_m'][0]}-{z['elevation_range_m'][1]}m, "
                f"{z.get('terrain_notes', '')}"
            )
        microzone_section = "## City Microzones\n" + "\n".join(zone_lines)

    tone_block = ""
    if tone_instruction:
        tone_block = f"\n## Voice / Tone Instruction\n{tone_instruction}\n"

    return f"""You are a hyperlocal weather forecaster writing for {city_name}. Write in a conversational,
engaging style similar to durangoweatherguy.com — knowledgeable but approachable, like you're talking to
a neighbor over the fence. You deeply understand mountain/terrain weather and local microclimates.
{tone_block}
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
7. **Horizon confidence rationale** — Provide explicit confidence rationale for:
   - immediate (0-6h)
   - short (6-48h)
   - extended (>48h)
   Use horizon model priority rules from "Horizon-Aware Blend Guidance".

## Terrain Context
{_format_terrain(terrain)}

{microzone_section}

## Model Disagreement (spread at overlapping timesteps)
{_model_disagreement_summary(forecasts)}

## Data Availability Summary (important)
{_data_availability_summary(forecasts)}

## Horizon-Aware Blend Guidance (explicit model priority rules)
{_horizon_blend_summary(forecasts, now)}

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
    "horizon_confidence": {{
        "immediate_0_6h": "<1 sentence rationale for immediate horizon model blend>",
        "short_6_48h": "<1 sentence rationale for short horizon model blend>",
        "extended_48h_plus": "<1 sentence rationale for extended horizon model blend>"
    }},
    "dayparts": {{
        "am": "<1-3 sentence morning forecast>",
        "pm": "<1-3 sentence afternoon forecast>",
        "night": "<1-3 sentence evening/overnight forecast>"
    }},
    "changes": ["<string describing what changed vs prior run, e.g. 'GFS warmed 3F for tomorrow afternoon'>"],
    "model_disagreement": {{
        "level": "<low|moderate|high>",
        "summary": "<1-2 sentences about model spread>",
        "biggest_spread_metric": "<temp|precip|snow|wind>",
        "biggest_spread_value": "<human-readable spread, e.g. '8F temp spread'>",
        "confidence_trend": "<improving|stable|degrading>"
    }},
    "dayparts": {{
        "am": "<1-3 sentence morning forecast>",
        "pm": "<1-3 sentence afternoon forecast>",
        "night": "<1-3 sentence evening/overnight forecast>"
    }},
    "changes": ["<string describing what changed vs prior run, e.g. 'GFS warmed 3F for tomorrow afternoon'>"],
    "model_disagreement": {{
        "level": "<low|moderate|high>",
        "summary": "<1-2 sentences about model spread>",
        "biggest_spread_metric": "<temp|precip|snow|wind>",
        "biggest_spread_value": "<human-readable spread, e.g. '8F temp spread'>",
        "confidence_trend": "<improving|stable|degrading>"
    }},
    "alerts": ["<any notable weather alerts or warnings>"],
    "updated_at": "<ISO timestamp>"
}}

Write naturally and engagingly. Don't just list numbers — interpret them. Say things like "the HRRR has been
flip-flopping on snow totals" or "all models are in rare agreement on a dry weekend." Reference specific
elevations in feet for US audiences. Mention local terrain features when relevant.

Critical guardrails:
- Do NOT claim "models are mute", "flying blind", "no usable model data", or similar unless
  the Data Availability Summary shows zero usable rows across all models.
- If data is partial/sparse, explicitly say which fields are available and provide a best-effort
  forecast from those fields.
- Avoid repeating "N/A" in prose.
"""
