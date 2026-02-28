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


@dataclass(frozen=True)
class AoiConfig:
    name: str
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float


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


def load_aois() -> dict[str, AoiConfig]:
    """Load AOIs from AOI_CONFIG JSON env var or use a La Plata County default."""
    default_aois = {
        "la-plata-county": {
            "name": "La Plata County, CO",
            "min_lat": 37.00,
            "min_lon": -108.35,
            "max_lat": 37.50,
            "max_lon": -107.45,
        }
    }
    raw = os.environ.get("AOI_CONFIG", json.dumps(default_aois))
    data = json.loads(raw)
    aois: dict[str, AoiConfig] = {}
    for slug, info in data.items():
        aois[slug] = AoiConfig(
            name=info["name"],
            min_lat=info["min_lat"],
            min_lon=info["min_lon"],
            max_lat=info["max_lat"],
            max_lon=info["max_lon"],
        )
    return aois


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
BQ_GRID_TILES_TABLE = "grid_tiles"
BQ_GRID_TILE_FIELDS_TABLE = "grid_tile_fields"
BQ_GRID_POINTS_SAMPLED_TABLE = "grid_points_sampled"
