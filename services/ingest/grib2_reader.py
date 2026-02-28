"""GRIB2 byte-range reader using idx files and xarray."""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import fsspec
import numpy as np
import xarray as xr

from config import GRIB2_VARIABLES, CityConfig

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

        entries.append({
            "index": int(parts[0]),
            "offset": offset,
            "end_offset": end_offset,
            "date_str": date_str,
            "var_name": var_name,
            "level": level,
            "forecast": forecast,
        })

    return entries


def _match_idx_entry(entry: dict, var_config: dict) -> bool:
    """Check if an idx entry matches a desired variable config."""
    var_name = entry["var_name"]
    level = entry["level"]

    short_name = var_config["shortName"]
    type_of_level = var_config.get("typeOfLevel", "")

    # Map shortName to common idx variable names
    name_map = {
        "2t": ["TMP", "TMP:2 m"],
        "10u": ["UGRD", "UGRD:10 m"],
        "10v": ["VGRD", "VGRD:10 m"],
        "tp": ["APCP", "PRATE"],
        "sde": ["SNOD"],
        "0deg": ["HGT:0C isotherm", "HGT"],
        "cape": ["CAPE"],
        "2r": ["RH", "RH:2 m"],
    }

    expected_names = name_map.get(short_name, [short_name])

    for name in expected_names:
        if ":" in name:
            n, l = name.split(":", 1)
            if var_name == n and l in level:
                return True
        elif var_name == name:
            # Check level match
            level_str = var_config.get("level", "")
            if type_of_level == "heightAboveGround" and level_str:
                if f"{level_str} m" in level:
                    return True
            elif type_of_level == "surface" and "surface" in level.lower():
                return True
            elif type_of_level == "isothermZero" and "0C" in level:
                return True
            elif not level_str:
                return True

    return False


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
) -> list[ForecastPoint]:
    """Read GRIB2 data for all cities using byte-range requests.

    Returns a list of ForecastPoint objects ready for BigQuery insertion.
    """
    results: list[ForecastPoint] = []

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
                    resp = _requests.get(grib2_url, headers={"Range": range_header}, timeout=60)
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
                        ds = xr.open_dataset(
                            tmp_path,
                            engine="cfgrib",
                            backend_kwargs={"indexpath": ""},
                        )
                        ds.load()  # materialize before removing temp file
                        var_data[var_key] = ds
                    except Exception as e:
                        logger.warning("Failed to decode %s for %s: %r", var_key, grib2_url, e)
                    finally:
                        os.unlink(tmp_path)

                except Exception as e:
                    logger.warning("Failed to read byte range for %s: %s", var_key, e)

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

    return results


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
