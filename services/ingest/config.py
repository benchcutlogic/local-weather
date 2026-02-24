"""Configuration for the GRIB2 ingest service."""

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


# NOAA GCS bucket paths for each model
MODEL_BUCKETS: dict[str, str] = {
    "hrrr": "gs://noaa-hrrr-bdp-pds",
    "gfs": "gs://noaa-gfs-bdp-pds",
    "nam": "gs://noaa-nam-bdp-pds",
    "ecmwf": "gs://noaa-ecmwf-bdp-pds",
}

# GRIB2 variable names to extract and their short names for byte-range filtering
GRIB2_VARIABLES: dict[str, dict[str, str]] = {
    "temperature_2m": {"shortName": "2t", "typeOfLevel": "heightAboveGround", "level": "2"},
    "wind_u_10m": {"shortName": "10u", "typeOfLevel": "heightAboveGround", "level": "10"},
    "wind_v_10m": {"shortName": "10v", "typeOfLevel": "heightAboveGround", "level": "10"},
    "precip": {"shortName": "tp", "typeOfLevel": "surface"},
    "snow_depth": {"shortName": "sde", "typeOfLevel": "surface"},
    "freezing_level": {"shortName": "0deg", "typeOfLevel": "isothermZero"},
    "cape": {"shortName": "cape", "typeOfLevel": "surface"},
    "relative_humidity": {"shortName": "2r", "typeOfLevel": "heightAboveGround", "level": "2"},
}

# BigQuery config
BQ_DATASET = os.environ.get("BQ_DATASET", "weather_core")
GCP_PROJECT = os.environ.get("GCP_PROJECT", "hyperlocal-wx-prod")
BQ_TABLE = "forecast_runs"
