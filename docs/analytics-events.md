# Analytics Events — local-weather UI

All events are emitted via `window.dispatchEvent(new CustomEvent('analytics:track', { detail: event }))`.
No PII is ever included in any payload.

## Transport contract

```ts
interface BaseEvent {
  event_name: WxEventName;  // stable snake_case string
  session_id: string;        // random per-session ID stored in sessionStorage
  timestamp: string;         // ISO 8601 UTC
}
```

Backend/analytics sinks listen for `analytics:track` and forward to their platform (PostHog, Plausible, BigQuery, etc.).

---

## Event reference

### Homepage

| Event | When | Key payload fields |
|-------|------|-------------------|
| `city_searched` | User types in the search box (debounced 600 ms) | `query_length` (number, not the query string), `result_count` |
| `location_detect_started` | User clicks "Detect my location" | — |
| `location_detect_success` | Geolocation succeeds | `lat_approx` (rounded to 2dp), `lon_approx` (rounded to 2dp) |
| `location_detect_error` | Geolocation fails or is denied | `error_code` (GeolocationPositionError.code or null) |

> **Privacy note**: `city_searched` logs only the length of the query, never the query string itself.
> `location_detect_success` rounds coordinates to ~1 km precision.

---

### City page

| Event | When | Key payload fields |
|-------|------|-------------------|
| `city_page_viewed` | City page mounts (onMount) | `city_slug`, `has_commentary` (boolean) |
| `forecast_tab_viewed` | User switches tabs | `city_slug`, `tab` (`forecast` \| `outlook` \| `map`) |
| `report_submitted` | User submits a community weather report | `city_slug`, `has_temp` (boolean), `has_snow` (boolean) |
| `report_generated` | (Reserved) Backend-generated report created | `city_slug` |

---

### Microclimate map

| Event | When | Key payload fields |
|-------|------|-------------------|
| `microclimate_map_load_start` | Map begins loading | `city_slug` |
| `microclimate_map_load_success` | Map + zone data fully loaded | `city_slug`, `zone_count`, `aoi_count`, `load_ms` |
| `microclimate_map_load_error` | Map or zone data fails | `city_slug`, `error_message` |
| `microclimate_map_fallback_visible` | Fallback card mode shown | `city_slug`, `reason` |
| `microclimate_metric_changed` | User selects a different map metric | `city_slug`, `metric` |
| `microclimate_layer_toggled` | User toggles a map layer | `city_slug`, `layer` (`aoi` \| `confidence` \| `hazards`), `enabled` |
| `zone_selected` | User clicks a zone on the map | `city_slug`, `zone_id` |
| `aoi_selected` | Zone with an AOI is selected, or AOI fallback card clicked | `city_slug`, `aoi_slug`, `zone_id` |
| `aoi_drawn` | (Reserved) User draws a custom AOI | `city_slug` |
| `detail_closed` | User closes the zone/AOI detail card | `city_slug`, `detail_type` (`zone` \| `aoi`) |

---

## Baseline metrics to track (product)

- **Return rate** — users who view a city page more than once in the same week
- **Session length** — time from first event to last event per session
- **Alert opt-in rate** — `report_submitted` / unique `city_page_viewed` sessions
- **Tab distribution** — share of `forecast_tab_viewed` by `tab`
- **Map engagement** — `zone_selected` / `microclimate_map_load_success`

---

## Recommended weekly review query (BigQuery / Redash example)

```sql
SELECT
  DATE_TRUNC(timestamp, WEEK) AS week,
  event_name,
  COUNT(*) AS event_count,
  COUNT(DISTINCT session_id) AS unique_sessions
FROM analytics_events
WHERE event_name IN (
  'city_page_viewed', 'forecast_tab_viewed',
  'zone_selected', 'aoi_selected', 'report_submitted'
)
GROUP BY 1, 2
ORDER BY 1 DESC, 3 DESC;
```
