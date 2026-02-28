"""Configuration for the commentary service."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CityConfig:
    name: str
    lat: float
    lon: float
    elev_bands: list[int] = field(default_factory=list)


def load_cities() -> dict[str, CityConfig]:
    """Load city configs from CITIES_CONFIG env var (JSON)."""
    raw = os.environ.get("CITIES_CONFIG", "{}")
    data = json.loads(raw)
    cities: dict[str, CityConfig] = {}
    for slug, info in data.items():
        cities[slug] = CityConfig(
            name=info["name"],
            lat=info["lat"],
            lon=info["lon"],
            elev_bands=info.get("elev_bands", info.get("elevation_bands", [])),
        )
    return cities


BQ_DATASET = os.environ.get("BQ_DATASET", "weather_core")
GCP_PROJECT = os.environ.get("GCP_PROJECT", "hyperlocal-wx-prod")
GCS_BUCKET = os.environ.get("COMMENTARY_BUCKET", "hyperlocal-wx-commentary")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
