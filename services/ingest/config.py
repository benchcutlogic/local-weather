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
    state: str | None = None
    aliases: list[str] = field(default_factory=list)
    timezone: str = "America/Denver"
    elev_bands: list[int] = field(default_factory=list)
    terrain_profile: str | None = None
    seasonal_hazards: list[str] = field(default_factory=list)
    alert_thresholds: dict[str, float] = field(default_factory=dict)
    branding: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AoiConfig:
    name: str
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float
    polygon: list[tuple[float, float]] = field(default_factory=list)


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
            state=info.get("state"),
            aliases=info.get("aliases", []),
            timezone=info.get("timezone", "America/Denver"),
            elev_bands=info.get("elev_bands", info.get("elevation_bands", [])),
            terrain_profile=info.get("terrain_profile"),
            seasonal_hazards=info.get("seasonal_hazards", []),
            alert_thresholds=info.get("alert_thresholds", {}),
            branding=info.get("branding", {}),
        )
    return cities


def load_city_aoi_map() -> dict[str, str]:
    """Load city->AOI mapping from CITY_AOI_MAP env var or default Durango mapping."""
    default_map = {
        "durango": "la-plata-county",
    }
    raw = os.environ.get("CITY_AOI_MAP", json.dumps(default_map))
    data = json.loads(raw)
    return {str(k): str(v) for k, v in data.items()}


def load_aois() -> dict[str, AoiConfig]:
    """Load AOIs from AOI_CONFIG JSON env var or use a La Plata County default."""
    default_aois = {
        "la-plata-county": {
            "name": "La Plata County, CO",
            "min_lat": 37.00,
            "min_lon": -108.35,
            "max_lat": 37.50,
            "max_lon": -107.45,
            "polygon": [
                {"lat": 37.00, "lon": -108.35},
                {"lat": 37.00, "lon": -107.45},
                {"lat": 37.50, "lon": -107.45},
                {"lat": 37.50, "lon": -108.35},
            ],
        }
    }
    raw = os.environ.get("AOI_CONFIG", json.dumps(default_aois))
    data = json.loads(raw)
    aois: dict[str, AoiConfig] = {}
    for slug, info in data.items():
        polygon_raw = info.get("polygon", []) or []
        polygon = [(float(p["lat"]), float(p["lon"])) for p in polygon_raw if "lat" in p and "lon" in p]

        min_lat = info.get("min_lat")
        min_lon = info.get("min_lon")
        max_lat = info.get("max_lat")
        max_lon = info.get("max_lon")

        if polygon:
            lats = [p[0] for p in polygon]
            lons = [p[1] for p in polygon]
            min_lat = min_lat if min_lat is not None else min(lats)
            max_lat = max_lat if max_lat is not None else max(lats)
            min_lon = min_lon if min_lon is not None else min(lons)
            max_lon = max_lon if max_lon is not None else max(lons)

        aois[slug] = AoiConfig(
            name=info["name"],
            min_lat=float(min_lat),
            min_lon=float(min_lon),
            max_lat=float(max_lat),
            max_lon=float(max_lon),
            polygon=polygon,
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
