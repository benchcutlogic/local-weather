"""Tone-aware action alert copy templates.

Generates concise, actionable alert messages adapted to the user's selected
tone profile. Thresholds, numbers, and source model references are never
modified by tone — only wording.

Closes #60: tone-aware action alert copy.
"""

from __future__ import annotations

from dataclasses import dataclass

# Each template has {placeholders} that are filled by the alert engine.
# Available placeholders:
#   {metric_value}  - the raw number (e.g. "14 in")
#   {threshold}     - the threshold that was exceeded
#   {model}         - source model name
#   {confidence}    - confidence level
#   {city}          - city name
#   {timeframe}     - when (e.g. "next 12h", "tonight")

ALERT_TEMPLATES: dict[str, dict[str, str]] = {
    "snow_event": {
        "professional": (
            "{city}: {metric_value} snow expected {timeframe} (threshold: {threshold}). "
            "Source: {model}. Confidence: {confidence}."
        ),
        "friendly": (
            "Heads up, {city}! We're looking at {metric_value} of snow {timeframe}. "
            "That's above our {threshold} watch level. {model} is the lead model here. "
            "Confidence is {confidence}."
        ),
        "spicy": (
            "🌨️ {city} snow alert: {metric_value} incoming {timeframe} — that blows past "
            "the {threshold} threshold. {model} is driving this call. "
            "Confidence? {confidence}."
        ),
    },
    "wind_event": {
        "professional": (
            "{city}: Wind gusts to {metric_value} forecast {timeframe} (threshold: {threshold}). "
            "Source: {model}. Confidence: {confidence}."
        ),
        "friendly": (
            "Windy times ahead in {city}! Gusts could hit {metric_value} {timeframe}. "
            "Our {threshold} alert level is exceeded. {model} confidence: {confidence}."
        ),
        "spicy": (
            "💨 Hold onto your hat, {city}. {metric_value} gusts {timeframe}. "
            "Way past the {threshold} line. {model} says so — confidence: {confidence}."
        ),
    },
    "precip_event": {
        "professional": (
            "{city}: Heavy precipitation expected — {metric_value} {timeframe} "
            "(threshold: {threshold}). Source: {model}. Confidence: {confidence}."
        ),
        "friendly": (
            "Rain alert for {city}! {metric_value} possible {timeframe}. "
            "That's above our {threshold} watch level. Per {model}, confidence: {confidence}."
        ),
        "spicy": (
            "🌧️ {city} is about to get soaked — {metric_value} {timeframe}. "
            "{threshold} threshold? Crushed. {model} confidence: {confidence}."
        ),
    },
    "general": {
        "professional": (
            "{city} weather alert: {metric_value} {timeframe}. "
            "Source: {model}. Confidence: {confidence}."
        ),
        "friendly": (
            "Weather heads-up for {city}: {metric_value} expected {timeframe}. "
            "From {model}, confidence: {confidence}."
        ),
        "spicy": (
            "⚠️ {city}: {metric_value} {timeframe}. "
            "{model} says it, confidence is {confidence}."
        ),
    },
}


def render_alert(
    alert_type: str,
    tone: str,
    *,
    metric_value: str,
    threshold: str,
    model: str,
    confidence: str,
    city: str,
    timeframe: str,
) -> str:
    """Render an alert message for the given type and tone."""
    templates = ALERT_TEMPLATES.get(alert_type, ALERT_TEMPLATES["general"])
    template = templates.get(tone, templates["professional"])
    return template.format(
        metric_value=metric_value,
        threshold=threshold,
        model=model,
        confidence=confidence,
        city=city,
        timeframe=timeframe,
    )
