/** Analytics stubs for the city forecast page. */

export function trackToneSelected(city: string, tone: string): void {
  console.log('[analytics]', 'tone_selected', { city, tone });
}

export function trackCardExpand(city: string, card: string): void {
  console.log('[analytics]', 'card_expand', { city, card });
}

export function trackChangesViewed(city: string, count: number): void {
  console.log('[analytics]', 'changes_viewed', { city, count });
}

export function trackDaypartRead(city: string, daypart: string): void {
  console.log('[analytics]', 'daypart_read', { city, daypart });
}
