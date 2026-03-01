import { browser } from '$app/environment';
import type { ZoneMetricKey } from '$lib/map/types';

export type MicroclimateMapEventName =
  | 'microclimate_map_load_start'
  | 'microclimate_map_load_success'
  | 'microclimate_map_load_error'
  | 'microclimate_map_fallback_visible'
  | 'microclimate_metric_changed'
  | 'microclimate_layer_toggled'
  | 'microclimate_zone_selected'
  | 'microclimate_aoi_selected'
  | 'microclimate_detail_closed';

interface EventContext {
  city_slug: string;
  session_id: string;
  timestamp: string;
}

export interface MicroclimateMapLoadStartEvent extends EventContext {
  event_name: 'microclimate_map_load_start';
}

export interface MicroclimateMapLoadSuccessEvent extends EventContext {
  event_name: 'microclimate_map_load_success';
  zone_count: number;
  aoi_count: number;
  load_ms: number;
}

export interface MicroclimateMapLoadErrorEvent extends EventContext {
  event_name: 'microclimate_map_load_error';
  error_message: string;
}

export interface MicroclimateMapFallbackVisibleEvent extends EventContext {
  event_name: 'microclimate_map_fallback_visible';
  reason: string;
}

export interface MicroclimateMetricChangedEvent extends EventContext {
  event_name: 'microclimate_metric_changed';
  metric: ZoneMetricKey;
}

export interface MicroclimateLayerToggledEvent extends EventContext {
  event_name: 'microclimate_layer_toggled';
  layer: 'aoi' | 'confidence' | 'hazards';
  enabled: boolean;
}

export interface MicroclimateZoneSelectedEvent extends EventContext {
  event_name: 'microclimate_zone_selected';
  zone_id: string;
}

export interface MicroclimateAoiSelectedEvent extends EventContext {
  event_name: 'microclimate_aoi_selected';
  aoi_slug: string;
  zone_id: string;
}

export interface MicroclimateDetailClosedEvent extends EventContext {
  event_name: 'microclimate_detail_closed';
  detail_type: 'zone' | 'aoi';
}

export type MicroclimateMapEvent =
  | MicroclimateMapLoadStartEvent
  | MicroclimateMapLoadSuccessEvent
  | MicroclimateMapLoadErrorEvent
  | MicroclimateMapFallbackVisibleEvent
  | MicroclimateMetricChangedEvent
  | MicroclimateLayerToggledEvent
  | MicroclimateZoneSelectedEvent
  | MicroclimateAoiSelectedEvent
  | MicroclimateDetailClosedEvent;

const SESSION_STORAGE_KEY = 'microclimate_map_session_id';

function randomId(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function getMapSessionId(): string {
  if (!browser) return 'ssr';

  const existing = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) return existing;

  const created = randomId();
  window.sessionStorage.setItem(SESSION_STORAGE_KEY, created);
  return created;
}

export function trackMicroclimateMapEvent(event: MicroclimateMapEvent) {
  if (!browser) return;

  window.dispatchEvent(new CustomEvent('analytics:track', { detail: event }));

  if (import.meta.env.DEV) {
    // Keep local visibility for analytics wiring during development.
    console.debug('[analytics]', event);
  }
}
