"""GRIB2 byte-range reader using idx files and xarray."""

from __future__ import annotations

import logging
import math
import re
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone

import fsspec
import numpy as np
import xarray as xr

from config import AoiConfig, GRIB2_VARIABLES, CityConfig

logger = logging.getLogger(__name__)


@dataclass
class ForecastPoint:
    """Extracted forecast data for a single city/time/elevation."""

    city_slug: str
    model_name: str
    run_time: datetime
    valid_time: datetime
    elevation_band: int | None
    temperature_2m: float | None
    precip_kg_m2: float | None
    wind_speed_10m: float | None
    wind_dir_10m: float | None
    snow_depth: float | None
    freezing_level_m: float | None
    cape: float | None
    relative_humidity: float | None


@dataclass
class GridSamplePoint:
    """Extracted grid sample point for AOI coverage."""

    aoi_slug: str
    model_name: str
    run_time: datetime
    valid_time: datetime
    lat: float
    lon: float
    temperature_2m: float | None
    precip_kg_m2: float | None
    wind_u_10m: float | None
    wind_v_10m: float | None
    snow_depth: float | None
    relative_humidity: float | None


def _parse_idx_file(idx_content: str) -> list[dict]:
    """Parse a GRIB2 .idx index file into byte-range entries.

    Each line format: NUM:BYTE_OFFSET:d=YYYYMMDDHH:VAR:LEVEL:fcst_info
    """
    entries: list[dict] = []
    lines = idx_content.strip().split("\n")

    for i, line in enumerate(lines):
        parts = line.split(":")
        if len(parts) < 6:
            continue

        offset = int(parts[1])
        date_str = parts[2]  # d=YYYYMMDDHH
        var_name = parts[3]
        level = parts[4]
        forecast = parts[5] if len(parts) > 5 else ""

        # Calculate length from next entry's offset
        end_offset = None
        if i + 1 < len(lines):
            next_parts = lines[i + 1].split(":")
            if len(next_parts) >= 2:
                end_offset = int(next_parts[1])

        # Some idx variants (observed on NAM) can emit non-integer sequence ids like
        # "8.1" in the first field. We don't rely on this id downstream, so coerce
        # safely instead of failing the whole forecast hour.
        try:
            entry_index = int(float(parts[0]))
        except ValueError:
            entry_index = i + 1

        entries.append({
            "index": entry_index,
            "offset": offset,
            "end_offset": end_offset,
            "date_str": date_str,
            "var_name": var_name,
            "level": level,
            "forecast": forecast,
        })

    return entries


def _match_idx_entry(entry: dict, var_config: dict) -> bool:
    """Check if an idx entry matches a desired variable config.

    Level matching must be precise: "2 m above ground" != "2 mb" (millibar).
    The substring "2 m" would incorrectly match the pressure-level entry "2 mb",
    resulting in cfgrib receiving a stratospheric GRIB message with wrong structure.
    """
    var_name = entry["var_name"]
    level = entry["level"].strip()

    short_name = var_config["shortName"]
    type_of_level = var_config.get("typeOfLevel", "")
    level_str = str(var_config.get("level", ""))

    # Canonical var name in .idx files
    name_map: dict[str, list[str]] = {
        "2t": ["TMP"],
        "10u": ["UGRD"],
        "10v": ["VGRD"],
        "tp": ["APCP", "PRATE"],
        "sde": ["SNOD"],
        "0deg": ["HGT"],
        "cape": ["CAPE"],
        "2r": ["RH"],
    }
    expected_names = name_map.get(short_name, [short_name])

    if var_name not in expected_names:
        return False

    # Precise level matching based on typeOfLevel —
    # avoids false matches like "2 m" matching "2 mb" (millibar pressure level)
    if type_of_level == "heightAboveGround" and level_str:
        # Must contain both the numeric height AND "above ground" to exclude mb levels
        return f"{level_str} m above ground" in level

    if type_of_level == "surface":
        return "surface" in level.lower()

    if type_of_level == "isothermZero":
        return "0C" in level or "isotherm" in level.lower()

    # Fallback: no level constraint
    return True


def _find_byte_ranges(idx_content: str) -> dict[str, tuple[int, int | None]]:
    """Find byte ranges for desired variables from idx file content."""
    entries = _parse_idx_file(idx_content)
    ranges: dict[str, tuple[int, int | None]] = {}

    for var_key, var_config in GRIB2_VARIABLES.items():
        for entry in entries:
            if _match_idx_entry(entry, var_config):
                ranges[var_key] = (entry["offset"], entry["end_offset"])
                break

    return ranges


def _extract_nearest_value(
    ds: xr.Dataset, lat: float, lon: float, var_name: str
) -> float | None:
    """Extract the nearest grid point value for a lat/lon."""
    try:
        # Handle longitude convention (some GRIB2 use 0-360)
        lon_360 = lon % 360

        if "latitude" in ds.dims:
            lat_dim, lon_dim = "latitude", "longitude"
        elif "lat" in ds.dims:
            lat_dim, lon_dim = "lat", "lon"
        else:
            # Try coordinate names
            for coord in ds.coords:
                if "lat" in coord.lower():
                    lat_dim = coord
                elif "lon" in coord.lower():
                    lon_dim = coord

        # Try both lon conventions
        for lon_val in [lon, lon_360]:
            try:
                point = ds.sel(
                    {lat_dim: lat, lon_dim: lon_val}, method="nearest"
                )
                for v in ds.data_vars:
                    if var_name.lower() in v.lower() or v.lower() in var_name.lower():
                        val = float(point[v].values)
                        if not math.isnan(val):
                            return val
                # If exact var name not found, take first data var
                first_var = list(ds.data_vars)[0]
                val = float(point[first_var].values)
                return None if math.isnan(val) else val
            except (KeyError, ValueError):
                continue

        return None
    except Exception as e:
        logger.warning("Failed to extract %s at (%s, %s): %s", var_name, lat, lon, e)
        return None


def _compute_wind(u: float | None, v: float | None) -> tuple[float | None, float | None]:
    """Compute wind speed and direction from U/V components."""
    if u is None or v is None:
        return None, None
    speed = math.sqrt(u**2 + v**2)
    direction = (270 - math.degrees(math.atan2(v, u))) % 360
    return round(speed, 2), round(direction, 1)


def _normalize_lon(lon: float) -> float:
    """Normalize longitude into [-180, 180]."""
    return ((lon + 180) % 360) - 180


def _point_in_polygon(lat: float, lon: float, polygon: list[tuple[float, float]]) -> bool:
    """Ray-casting point in polygon test for (lat, lon)."""
    inside = False
    n = len(polygon)
    if n < 3:
        return False

    j = n - 1
    for i in range(n):
        yi, xi = polygon[i]  # lat, lon
        yj, xj = polygon[j]
        intersects = ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) + 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _aoi_target_points(aoi: AoiConfig, resolution_deg: float = 0.25) -> list[tuple[float, float]]:
    """Generate a list of (lat, lon) sample points covering an AOI at the given resolution.

    If polygon coordinates are provided, points are clipped to that polygon (scaffolding for
    county/custom AOIs). Otherwise falls back to bbox coverage.
    """
    lat = aoi.min_lat
    points: list[tuple[float, float]] = []
    while lat <= aoi.max_lat + 1e-9:
        lon = aoi.min_lon
        while lon <= aoi.max_lon + 1e-9:
            point = (round(lat, 4), round(lon, 4))
            if not aoi.polygon or _point_in_polygon(point[0], point[1], aoi.polygon):
                points.append(point)
            lon = round(lon + resolution_deg, 4)
        lat = round(lat + resolution_deg, 4)
    return points


def _extract_aoi_grid_samples(
    var_data: dict[str, xr.Dataset],
    aoi_slug: str,
    aoi: AoiConfig,
    model: str,
    run_time: datetime,
    valid_time: datetime,
) -> list[GridSamplePoint]:
    """Extract forecast values for all grid points inside an AOI bounding box.

    Uses pre-generated target points at model resolution and `_extract_nearest_value`
    for each — same method used for city extraction, fully compatible with cfgrib.
    """
    if not var_data:
        return []

    target_points = _aoi_target_points(aoi)
    if not target_points:
        return []

    samples: list[GridSamplePoint] = []
    for lat, lon in target_points:
        t = _extract_nearest_value(var_data["temperature_2m"], lat, lon, "t2m") if "temperature_2m" in var_data else None
        p = _extract_nearest_value(var_data["precip"], lat, lon, "tp") if "precip" in var_data else None
        u = _extract_nearest_value(var_data["wind_u_10m"], lat, lon, "u10") if "wind_u_10m" in var_data else None
        v = _extract_nearest_value(var_data["wind_v_10m"], lat, lon, "v10") if "wind_v_10m" in var_data else None
        s = _extract_nearest_value(var_data["snow_depth"], lat, lon, "sde") if "snow_depth" in var_data else None
        rh = _extract_nearest_value(var_data["relative_humidity"], lat, lon, "r2") if "relative_humidity" in var_data else None

        samples.append(GridSamplePoint(
            aoi_slug=aoi_slug,
            model_name=model.upper(),
            run_time=run_time.replace(tzinfo=timezone.utc),
            valid_time=valid_time,
            lat=lat,
            lon=lon,
            temperature_2m=t,
            precip_kg_m2=p,
            wind_u_10m=u,
            wind_v_10m=v,
            snow_depth=s,
            relative_humidity=rh,
        ))

    logger.info(
        "Extracted %d AOI grid samples for %s (%s) at valid_time=%s",
        len(samples),
        aoi_slug,
        aoi.name,
        valid_time.isoformat(),
    )
    return samples


def _build_grib2_url(model: str, run_time: datetime, forecast_hour: int) -> str:
    """Build public HTTP URL for a GRIB2 file (AWS Open Data buckets)."""
    date_str = run_time.strftime("%Y%m%d")
    cycle = f"{run_time.hour:02d}"

    if model == "hrrr":
        return (
            f"https://noaa-hrrr-bdp-pds.s3.amazonaws.com/hrrr.{date_str}/conus/"
            f"hrrr.t{cycle}z.wrfsfcf{forecast_hour:02d}.grib2"
        )
    elif model == "gfs":
        return (
            f"https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{date_str}/{cycle}/atmos/"
            f"gfs.t{cycle}z.pgrb2.0p25.f{forecast_hour:03d}"
        )
    elif model == "nam":
        return (
            f"https://noaa-nam-pds.s3.amazonaws.com/nam.{date_str}/"
            f"nam.t{cycle}z.awphys{forecast_hour:02d}.tm00.grib2"
        )
    elif model == "ecmwf":
        return (
            f"https://noaa-ecmwf-pds.s3.amazonaws.com/{date_str}/{cycle}z/"
            f"0p25/oper/{forecast_hour:03d}.grib2"
        )
    else:
        raise ValueError(f"Unknown model: {model}")


def _build_idx_url(grib2_url: str) -> str:
    """Build the idx URL from the GRIB2 URL."""
    return grib2_url + ".idx"


async def read_grib2_for_cities(
    model: str,
    run_time: datetime,
    forecast_hours: list[int],
    cities: dict[str, CityConfig],
    aois: dict[str, AoiConfig] | None = None,
    city_aoi_map: dict[str, str] | None = None,
) -> tuple[list[ForecastPoint], list[GridSamplePoint]]:
    """Read GRIB2 data for all cities using byte-range requests.

    Returns forecast points and AOI grid samples for BigQuery insertion.
    """
    results: list[ForecastPoint] = []
    grid_samples: list[GridSamplePoint] = []

    for fhr in forecast_hours:
        grib2_url = _build_grib2_url(model, run_time, fhr)
        idx_url = _build_idx_url(grib2_url)

        valid_time = run_time.replace(tzinfo=timezone.utc)
        from datetime import timedelta
        valid_time = valid_time + timedelta(hours=fhr)

        logger.info("Processing %s f%03d: %s", model.upper(), fhr, grib2_url)

        try:
            # Read idx file to find byte ranges
            with fsspec.open(idx_url, "r") as f:
                idx_content = f.read()

            byte_ranges = _find_byte_ranges(idx_content)

            if not byte_ranges:
                logger.warning("No matching variables found in idx for %s", idx_url)
                continue

            # Read each variable's byte range
            var_data: dict[str, xr.Dataset] = {}

            import requests as _requests
            import tempfile
            import os

            for var_key, (start, end) in byte_ranges.items():
                try:
                    # Use HTTP Range header — fsspec doesn't do real range requests for http://
                    range_header = f"bytes={start}-{end - 1}" if end is not None else f"bytes={start}-"
                    resp = _requests.get(
                        grib2_url,
                        headers={"Range": range_header},
                        timeout=60,
                    )
                    resp.raise_for_status()
                    if resp.status_code not in (200, 206):
                        logger.warning("Unexpected HTTP %s for range %s on %s", resp.status_code, range_header, grib2_url)
                        continue
                    data = resp.content

                    # Write bytes to temp file and decode with cfgrib
                    with tempfile.NamedTemporaryFile(suffix=".grib2", delete=False) as tmp:
                        tmp.write(data)
                        tmp_path = tmp.name

                    try:
                        # Some cfgrib/eccodes combinations can assert on indexpath="".
                        # Try explicit no-index path first, then fall back to defaults.
                        try:
                            ds = xr.open_dataset(
                                tmp_path,
                                engine="cfgrib",
                                backend_kwargs={"indexpath": ""},
                            )
                        except AssertionError:
                            ds = xr.open_dataset(tmp_path, engine="cfgrib")

                        # NOTE: do not force ds.load() here; cfgrib can assert during eager load
                        # for certain slices. Keep lazy dataset and extract nearest values downstream.
                        var_data[var_key] = ds
                    except Exception as e:
                        logger.warning(
                            "Failed to decode %s for %s: %s: %r\n%s",
                            var_key,
                            grib2_url,
                            e.__class__.__name__,
                            e,
                            traceback.format_exc(limit=4),
                        )
                    finally:
                        # Keep temp file for the lifetime of this request because datasets are lazy.
                        # Cloud Run container FS is ephemeral; cleanup is handled by instance recycle.
                        pass

                except Exception as e:
                    logger.warning("Failed to read byte range for %s: %s", var_key, e)

            # Extract AOI-wide grid samples (county/custom coverage).
            # If city_aoi_map is provided, only sample mapped AOIs (deduped).
            if aois:
                selected_aoi_slugs = set(aois.keys())
                if city_aoi_map:
                    selected_aoi_slugs = {aoi_slug for aoi_slug in city_aoi_map.values() if aoi_slug in aois}

                for aoi_slug in selected_aoi_slugs:
                    aoi = aois[aoi_slug]
                    grid_samples.extend(
                        _extract_aoi_grid_samples(
                            var_data=var_data,
                            aoi_slug=aoi_slug,
                            aoi=aoi,
                            model=model,
                            run_time=run_time,
                            valid_time=valid_time,
                        )
                    )

            # Extract values for each city
            for city_slug, city in cities.items():
                temp_val = None
                wind_u = None
                wind_v = None
                precip_val = None
                snow_val = None
                freezing_val = None
                cape_val = None
                rh_val = None

                if "temperature_2m" in var_data:
                    temp_val = _extract_nearest_value(
                        var_data["temperature_2m"], city.lat, city.lon, "t2m"
                    )
                if "wind_u_10m" in var_data:
                    wind_u = _extract_nearest_value(
                        var_data["wind_u_10m"], city.lat, city.lon, "u10"
                    )
                if "wind_v_10m" in var_data:
                    wind_v = _extract_nearest_value(
                        var_data["wind_v_10m"], city.lat, city.lon, "v10"
                    )
                if "precip" in var_data:
                    precip_val = _extract_nearest_value(
                        var_data["precip"], city.lat, city.lon, "tp"
                    )
                if "snow_depth" in var_data:
                    snow_val = _extract_nearest_value(
                        var_data["snow_depth"], city.lat, city.lon, "sde"
                    )
                if "freezing_level" in var_data:
                    freezing_val = _extract_nearest_value(
                        var_data["freezing_level"], city.lat, city.lon, "gh"
                    )
                if "cape" in var_data:
                    cape_val = _extract_nearest_value(
                        var_data["cape"], city.lat, city.lon, "cape"
                    )
                if "relative_humidity" in var_data:
                    rh_val = _extract_nearest_value(
                        var_data["relative_humidity"], city.lat, city.lon, "r2"
                    )

                wind_speed, wind_dir = _compute_wind(wind_u, wind_v)

                if all(v is None for v in [temp_val, precip_val, wind_speed, snow_val, rh_val, freezing_val, cape_val]):
                    logger.warning(
                        "Skipping all-null city point for %s %s f%03d",
                        city_slug,
                        model.upper(),
                        fhr,
                    )
                    continue

                # Base-level point (no elevation band)
                results.append(ForecastPoint(
                    city_slug=city_slug,
                    model_name=model.upper(),
                    run_time=run_time.replace(tzinfo=timezone.utc),
                    valid_time=valid_time,
                    elevation_band=None,
                    temperature_2m=temp_val,
                    precip_kg_m2=precip_val,
                    wind_speed_10m=wind_speed,
                    wind_dir_10m=wind_dir,
                    snow_depth=snow_val,
                    freezing_level_m=freezing_val,
                    cape=cape_val,
                    relative_humidity=rh_val,
                ))

                # Generate points for each elevation band
                for band in city.elev_bands:
                    results.append(ForecastPoint(
                        city_slug=city_slug,
                        model_name=model.upper(),
                        run_time=run_time.replace(tzinfo=timezone.utc),
                        valid_time=valid_time,
                        elevation_band=band,
                        temperature_2m=_lapse_rate_adjust(temp_val, band) if temp_val else None,
                        precip_kg_m2=precip_val,
                        wind_speed_10m=wind_speed,
                        wind_dir_10m=wind_dir,
                        snow_depth=snow_val,
                        freezing_level_m=freezing_val,
                        cape=cape_val,
                        relative_humidity=rh_val,
                    ))

            # Close datasets
            for ds in var_data.values():
                ds.close()

        except Exception as e:
            logger.error("Failed to process %s f%03d: %s", model.upper(), fhr, e)
            continue

    return results, grid_samples


def _lapse_rate_adjust(temp_k: float, elevation_m: int, base_elev: int = 1500) -> float:
    """Apply standard atmospheric lapse rate (~6.5C/km) for elevation adjustment."""
    lapse_rate = 0.0065  # K per meter
    delta_elev = elevation_m - base_elev
    return round(temp_k - (lapse_rate * delta_elev), 2)


def get_default_forecast_hours(model: str) -> list[int]:
    """Get default forecast hours to extract for each model."""
    if model == "hrrr":
        return list(range(0, 19))  # 0-18h
    elif model == "gfs":
        return list(range(0, 121, 3))  # 0-120h, every 3h
    elif model == "nam":
        return list(range(0, 61, 3))  # 0-60h, every 3h
    elif model == "ecmwf":
        return list(range(0, 121, 6))  # 0-120h, every 6h
    else:
        return list(range(0, 25))


def get_latest_run_time(model: str) -> datetime:
    """Estimate the latest available model run time."""
    now = datetime.now(timezone.utc)
    if model == "hrrr":
        # HRRR runs every hour, available ~45min after
        run_hour = now.hour - 1 if now.minute < 45 else now.hour
        return now.replace(hour=run_hour, minute=0, second=0, microsecond=0)
    elif model in ("gfs", "nam"):
        # Runs at 00, 06, 12, 18z — available ~3.5h after
        cycles = [0, 6, 12, 18]
        available_hour = now.hour - 4
        cycle = max((c for c in cycles if c <= max(available_hour, 0)), default=18)
        if cycle > available_hour:
            from datetime import timedelta
            now = now - timedelta(days=1)
        return now.replace(hour=cycle, minute=0, second=0, microsecond=0)
    elif model == "ecmwf":
        cycles = [0, 12]
        available_hour = now.hour - 6
        cycle = max((c for c in cycles if c <= max(available_hour, 0)), default=12)
        if cycle > available_hour:
            from datetime import timedelta
            now = now - timedelta(days=1)
        return now.replace(hour=cycle, minute=0, second=0, microsecond=0)
    else:
        return now.replace(minute=0, second=0, microsecond=0)
