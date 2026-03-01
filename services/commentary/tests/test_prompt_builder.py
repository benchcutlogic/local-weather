"""Tests for prompt builder — especially new structured output fields."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from prompt_builder import build_commentary_prompt, _model_disagreement_summary


def test_prompt_includes_dayparts_schema():
    prompt = build_commentary_prompt(
        city_slug="durango",
        city_name="Durango",
        forecasts=[],
        drift_data=[],
        terrain=None,
        verification_scores=[],
    )
    assert '"dayparts"' in prompt
    assert '"am"' in prompt
    assert '"pm"' in prompt
    assert '"night"' in prompt


def test_prompt_includes_changes_schema():
    prompt = build_commentary_prompt(
        city_slug="durango",
        city_name="Durango",
        forecasts=[],
        drift_data=[],
        terrain=None,
        verification_scores=[],
    )
    assert '"changes"' in prompt


def test_prompt_includes_model_disagreement_schema():
    prompt = build_commentary_prompt(
        city_slug="durango",
        city_name="Durango",
        forecasts=[],
        drift_data=[],
        terrain=None,
        verification_scores=[],
    )
    assert '"model_disagreement"' in prompt
    assert '"biggest_spread_metric"' in prompt
    assert '"confidence_trend"' in prompt


def test_prompt_includes_tone_instruction():
    prompt = build_commentary_prompt(
        city_slug="durango",
        city_name="Durango",
        forecasts=[],
        drift_data=[],
        terrain=None,
        verification_scores=[],
        tone_instruction="Write with attitude and personality.",
    )
    assert "Write with attitude and personality." in prompt


def test_prompt_includes_microzones():
    zones = [
        {
            "zone_id": "dgo-valley",
            "name": "Animas Valley",
            "elevation_range_m": [1980, 2100],
            "terrain_notes": "River valley",
        }
    ]
    prompt = build_commentary_prompt(
        city_slug="durango",
        city_name="Durango",
        forecasts=[],
        drift_data=[],
        terrain=None,
        verification_scores=[],
        microzones=zones,
    )
    assert "Animas Valley" in prompt
    assert "City Microzones" in prompt


def test_model_disagreement_summary_with_data():
    forecasts = [
        {"valid_time": "2025-01-01T12:00:00Z", "model_name": "GFS", "temperature_2m": 270, "precip_kg_m2": 1.0},
        {"valid_time": "2025-01-01T12:00:00Z", "model_name": "HRRR", "temperature_2m": 275, "precip_kg_m2": 2.0},
    ]
    result = _model_disagreement_summary(forecasts)
    assert "temp_spread" in result
    assert "precip_spread" in result


def test_model_disagreement_summary_empty():
    result = _model_disagreement_summary([])
    assert "No model disagreement" in result
