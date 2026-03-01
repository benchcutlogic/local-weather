# Microclimate Map Analytics Event Schema

This document defines frontend analytics events emitted by `frontend/src/lib/components/organisms/MicroclimateMap.svelte`.

## Common fields

All events include:

- `event_name` (string)
- `city_slug` (string)
- `session_id` (string, per-tab session key)
- `timestamp` (ISO-8601 string)

## Event catalog

### `microclimate_map_load_start`
Emitted when map lazy-load starts after section becomes visible.

### `microclimate_map_load_success`
Emitted after geometry loads and summary metrics are joined.

Additional fields:
- `zone_count` (number)
- `aoi_count` (number)
- `load_ms` (number)

### `microclimate_map_load_error`
Emitted when map library init, asset loading, or summary fetch fails.

Additional fields:
- `error_message` (string)

### `microclimate_map_fallback_visible`
Emitted when fallback card mode is shown.

Additional fields:
- `reason` (string)

### `microclimate_metric_changed`
Emitted when user switches active metric.

Additional fields:
- `metric` (`temp_delta_f` | `wind_delta_mph` | `precip_delta_pct` | `snow_delta_in`)

### `microclimate_layer_toggled`
Emitted when AOI/confidence/hazard overlay visibility changes.

Additional fields:
- `layer` (`aoi` | `confidence` | `hazards`)
- `enabled` (boolean)

### `microclimate_zone_selected`
Emitted when a zone is selected from map interaction.

Additional fields:
- `zone_id` (string)

### `microclimate_aoi_selected`
Emitted when an AOI is selected from map interaction.

Additional fields:
- `aoi_slug` (string)
- `zone_id` (string)

### `microclimate_detail_closed`
Emitted when user closes a zone/AOI detail card.

Additional fields:
- `detail_type` (`zone` | `aoi`)
