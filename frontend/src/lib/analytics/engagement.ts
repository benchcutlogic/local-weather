/**
 * Engagement analytics for forecast intelligence modules.
 *
 * Tracks tone selection, card expansion, changes viewed, and daypart reads
 * to measure impact of carrot-inspired UX features.
 *
 * Closes #61: instrument engagement impact of carrot-inspired UX modules.
 */

import { browser } from '$app/environment';

export type EngagementEventName =
  | 'tone_selected'
  | 'card_expand'
  | 'changes_viewed'
  | 'daypart_read'
  | 'disagreement_card_viewed'
  | 'data_trust_panel_viewed'
  | 'verification_card_viewed'
  | 'alert_action_clicked'
  | 'microzone_selected';

export interface EngagementEvent {
  event_name: EngagementEventName;
  city_slug: string;
  tone?: string;
  card_id?: string;
  daypart?: string;
  zone_id?: string;
  timestamp: string;
  session_id: string;
}

const SESSION_KEY = 'wx:engagement_session';

function getSessionId(): string {
  if (!browser) return 'ssr';
  const existing = window.sessionStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const id = Math.random().toString(36).slice(2, 10);
  window.sessionStorage.setItem(SESSION_KEY, id);
  return id;
}

export function trackEngagement(
  eventName: EngagementEventName,
  citySlug: string,
  extra?: Partial<Pick<EngagementEvent, 'tone' | 'card_id' | 'daypart' | 'zone_id'>>
): void {
  if (!browser) return;

  const event: EngagementEvent = {
    event_name: eventName,
    city_slug: citySlug,
    timestamp: new Date().toISOString(),
    session_id: getSessionId(),
    ...extra,
  };

  // Emit via CustomEvent for any analytics listener (GA4, Amplitude, etc.)
  window.dispatchEvent(new CustomEvent('analytics:track', { detail: event }));

  if (import.meta.env.DEV) {
    console.debug('[engagement]', event);
  }
}
