/**
 * Core analytics module for local-weather UI journeys.
 *
 * Events are dispatched as `analytics:track` CustomEvents so any future
 * analytics backend (PostHog, Plausible, etc.) can subscribe without changing
 * call-sites.  No PII is ever included in payloads.
 */

import { browser } from '$app/environment';

// ─── Session helpers ──────────────────────────────────────────────────────────

const SESSION_KEY = 'wx_session_id';

function randomId(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function getSessionId(): string {
  if (!browser) return 'ssr';
  const existing = window.sessionStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const id = randomId();
  window.sessionStorage.setItem(SESSION_KEY, id);
  return id;
}

// ─── Event types ──────────────────────────────────────────────────────────────

/** All event names tracked across the app. */
export type WxEventName =
  // Homepage
  | 'city_searched'
  | 'location_detect_started'
  | 'location_detect_success'
  | 'location_detect_error'
  // City page
  | 'city_page_viewed'
  | 'forecast_tab_viewed'
  | 'report_submitted'
  | 'report_generated'
  // Microclimate map
  | 'microclimate_map_load_start'
  | 'microclimate_map_load_success'
  | 'microclimate_map_load_error'
  | 'microclimate_map_fallback_visible'
  | 'microclimate_metric_changed'
  | 'microclimate_layer_toggled'
  | 'zone_selected'
  | 'aoi_selected'
  | 'aoi_drawn'
  | 'detail_closed'
  // Engagement impact events (#61)
  | 'tone_selected'
  | 'card_expand'
  | 'changes_viewed'
  | 'daypart_read'
  | 'disagreement_card_viewed'
  | 'data_trust_panel_viewed'
  | 'verification_card_viewed'
  | 'alert_action_clicked'
  | 'microzone_selected';

interface BaseEvent {
  event_name: WxEventName;
  session_id: string;
  timestamp: string;
}

// ── Homepage events ──────────────────────────────────────────────────────────

export interface CitySearchedEvent extends BaseEvent {
  event_name: 'city_searched';
  /** Non-sensitive: length of query only, never the query string itself. */
  query_length: number;
  result_count: number;
}

export interface LocationDetectStartedEvent extends BaseEvent {
  event_name: 'location_detect_started';
}

export interface LocationDetectSuccessEvent extends BaseEvent {
  event_name: 'location_detect_success';
  /** Coarse resolution only – rounded to 2 decimal places. */
  lat_approx: number;
  lon_approx: number;
}

export interface LocationDetectErrorEvent extends BaseEvent {
  event_name: 'location_detect_error';
  error_code: number | null;
}

// ── City page events ─────────────────────────────────────────────────────────

export interface CityPageViewedEvent extends BaseEvent {
  event_name: 'city_page_viewed';
  city_slug: string;
  has_commentary: boolean;
}

export interface ForecastTabViewedEvent extends BaseEvent {
  event_name: 'forecast_tab_viewed';
  city_slug: string;
  tab: 'forecast' | 'outlook' | 'map';
}

export interface ReportSubmittedEvent extends BaseEvent {
  event_name: 'report_submitted';
  city_slug: string;
  has_temp: boolean;
  has_snow: boolean;
}

export interface ReportGeneratedEvent extends BaseEvent {
  event_name: 'report_generated';
  city_slug: string;
}

// ── Microclimate map events ──────────────────────────────────────────────────

export interface MapLoadStartEvent extends BaseEvent {
  event_name: 'microclimate_map_load_start';
  city_slug: string;
}

export interface MapLoadSuccessEvent extends BaseEvent {
  event_name: 'microclimate_map_load_success';
  city_slug: string;
  zone_count: number;
  aoi_count: number;
  load_ms: number;
}

export interface MapLoadErrorEvent extends BaseEvent {
  event_name: 'microclimate_map_load_error';
  city_slug: string;
  error_message: string;
}

export interface MapFallbackVisibleEvent extends BaseEvent {
  event_name: 'microclimate_map_fallback_visible';
  city_slug: string;
  reason: string;
}

export interface MetricChangedEvent extends BaseEvent {
  event_name: 'microclimate_metric_changed';
  city_slug: string;
  metric: string;
}

export interface LayerToggledEvent extends BaseEvent {
  event_name: 'microclimate_layer_toggled';
  city_slug: string;
  layer: 'aoi' | 'confidence' | 'hazards';
  enabled: boolean;
}

export interface ZoneSelectedEvent extends BaseEvent {
  event_name: 'zone_selected';
  city_slug: string;
  zone_id: string;
}

export interface AoiSelectedEvent extends BaseEvent {
  event_name: 'aoi_selected';
  city_slug: string;
  aoi_slug: string;
  zone_id: string;
}

export interface AoiDrawnEvent extends BaseEvent {
  event_name: 'aoi_drawn';
  city_slug: string;
}

export interface DetailClosedEvent extends BaseEvent {
  event_name: 'detail_closed';
  city_slug: string;
  detail_type: 'zone' | 'aoi';
}

export type WxEvent =
  | CitySearchedEvent
  | LocationDetectStartedEvent
  | LocationDetectSuccessEvent
  | LocationDetectErrorEvent
  | CityPageViewedEvent
  | ForecastTabViewedEvent
  | ReportSubmittedEvent
  | ReportGeneratedEvent
  | MapLoadStartEvent
  | MapLoadSuccessEvent
  | MapLoadErrorEvent
  | MapFallbackVisibleEvent
  | MetricChangedEvent
  | LayerToggledEvent
  | ZoneSelectedEvent
  | AoiSelectedEvent
  | AoiDrawnEvent
  | DetailClosedEvent;

// ─── Track function ───────────────────────────────────────────────────────────

/**
 * Emit an analytics event.  No PII is ever included in any payload.
 * Dispatches a `analytics:track` CustomEvent so backends can be swapped.
 */
export function track<E extends WxEvent>(
  eventName: E['event_name'],
  payload: Omit<E, 'event_name' | 'session_id' | 'timestamp'>
): void {
  if (!browser) return;

  const event: WxEvent = {
    event_name: eventName,
    session_id: getSessionId(),
    timestamp: new Date().toISOString(),
    ...(payload as Record<string, unknown>)
  } as WxEvent;

  window.dispatchEvent(new CustomEvent('analytics:track', { detail: event }));

  if (import.meta.env.DEV) {
    console.debug('[analytics]', event);
  }
}
