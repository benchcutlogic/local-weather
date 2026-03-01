/**
 * Tests for analytics emitter paths.
 * Verifies: event schema, session ID, no-PII constraint, and CustomEvent dispatch.
 *
 * Related issues: #54 (Basic test coverage for emitter paths)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock SvelteKit browser module BEFORE importing the module under test
vi.mock('$app/environment', () => ({ browser: true }));

// Now import after mock is in place
const { track, getSessionId } = await import('./index');

describe('analytics/index', () => {
  let emittedEvents: CustomEvent[] = [];
  let listener: (e: Event) => void;

  beforeEach(() => {
    emittedEvents = [];
    window.sessionStorage.clear();
    listener = (e) => emittedEvents.push(e as CustomEvent);
    window.addEventListener('analytics:track', listener);
  });

  afterEach(() => {
    window.removeEventListener('analytics:track', listener);
    window.sessionStorage.clear();
  });

  // ── Session ID ─────────────────────────────────────────────────────────────

  it('generates a stable session_id within a session', () => {
    const id1 = getSessionId();
    const id2 = getSessionId();
    expect(id1).toBe(id2);
    expect(id1.length).toBeGreaterThan(0);
  });

  it('generates a new session_id after storage is cleared', () => {
    const id1 = getSessionId();
    window.sessionStorage.clear();
    const id2 = getSessionId();
    expect(id2).not.toBe(id1);
  });

  // ── Event emission ─────────────────────────────────────────────────────────

  it('dispatches a CustomEvent on window when track() is called', () => {
    track('city_searched', { query_length: 5, result_count: 3 });
    expect(emittedEvents).toHaveLength(1);
    expect(emittedEvents[0].type).toBe('analytics:track');
  });

  it('includes event_name, session_id, and timestamp in every event', () => {
    track('city_page_viewed', { city_slug: 'durango', has_commentary: true });
    const detail = emittedEvents[0].detail;
    expect(detail.event_name).toBe('city_page_viewed');
    expect(typeof detail.session_id).toBe('string');
    expect(detail.session_id.length).toBeGreaterThan(0);
    expect(typeof detail.timestamp).toBe('string');
    // Timestamp should be a valid ISO 8601 date
    expect(new Date(detail.timestamp).getTime()).not.toBeNaN();
  });

  it('includes payload fields alongside base fields', () => {
    track('city_searched', { query_length: 7, result_count: 2 });
    const detail = emittedEvents[0].detail;
    expect(detail.query_length).toBe(7);
    expect(detail.result_count).toBe(2);
  });

  // ── No PII constraint ──────────────────────────────────────────────────────

  it('does not include raw location query string in city_searched events', () => {
    // Only query_length (a number), NOT the literal text the user typed
    track('city_searched', { query_length: 12, result_count: 1 });
    const detail = emittedEvents[0].detail;
    expect(detail).not.toHaveProperty('query');
    expect(detail).not.toHaveProperty('query_text');
    expect(detail).toHaveProperty('query_length');
    expect(typeof detail.query_length).toBe('number');
  });

  it('accepts only approximate coordinates in location events', () => {
    track('location_detect_success', {
      lat_approx: 37.28,
      lon_approx: -107.88
    });
    const detail = emittedEvents[0].detail;
    expect(typeof detail.lat_approx).toBe('number');
    expect(typeof detail.lon_approx).toBe('number');
    // Coarse-only: ≤ 2 decimal places
    expect(String(detail.lat_approx).split('.')[1]?.length ?? 0).toBeLessThanOrEqual(2);
  });

  // ── Multiple events ────────────────────────────────────────────────────────

  it('emits distinct events for successive track() calls', () => {
    track('city_page_viewed', { city_slug: 'durango', has_commentary: true });
    track('forecast_tab_viewed', { city_slug: 'durango', tab: 'forecast' });
    track('zone_selected', { city_slug: 'durango', zone_id: 'dgo-z-001' });

    expect(emittedEvents).toHaveLength(3);
    const names = emittedEvents.map((e) => e.detail.event_name);
    expect(names).toEqual(['city_page_viewed', 'forecast_tab_viewed', 'zone_selected']);
  });

  // ── Stable schema ──────────────────────────────────────────────────────────

  it('session_id is consistent across multiple events in the same session', () => {
    track('city_page_viewed', { city_slug: 'durango', has_commentary: false });
    track('forecast_tab_viewed', { city_slug: 'durango', tab: 'outlook' });
    const ids = emittedEvents.map((e) => e.detail.session_id);
    expect(ids[0]).toBe(ids[1]);
  });
});
