"""Tests for tone-aware alert templates."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from alert_templates import render_alert, ALERT_TEMPLATES


def test_render_snow_professional():
    msg = render_alert(
        "snow_event",
        "professional",
        metric_value="14 in",
        threshold="10 in",
        model="HRRR",
        confidence="high",
        city="Durango",
        timeframe="next 12h",
    )
    assert "Durango" in msg
    assert "14 in" in msg
    assert "HRRR" in msg
    assert "high" in msg


def test_render_snow_spicy():
    msg = render_alert(
        "snow_event",
        "spicy",
        metric_value="14 in",
        threshold="10 in",
        model="HRRR",
        confidence="high",
        city="Durango",
        timeframe="next 12h",
    )
    assert "🌨️" in msg
    assert "14 in" in msg


def test_render_unknown_type_uses_general():
    msg = render_alert(
        "unknown_event_type",
        "friendly",
        metric_value="test",
        threshold="test",
        model="GFS",
        confidence="moderate",
        city="Denver",
        timeframe="tomorrow",
    )
    assert "Denver" in msg
    assert "GFS" in msg


def test_render_unknown_tone_uses_professional():
    msg = render_alert(
        "wind_event",
        "unknown_tone",
        metric_value="60 mph",
        threshold="45 mph",
        model="NAM",
        confidence="moderate",
        city="SLC",
        timeframe="tonight",
    )
    assert "SLC" in msg
    assert "60 mph" in msg


def test_all_alert_types_have_all_tones():
    for alert_type, templates in ALERT_TEMPLATES.items():
        for tone in ("professional", "friendly", "spicy"):
            assert tone in templates, f"{alert_type} missing {tone} template"
