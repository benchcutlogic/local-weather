<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import ZoneDetailCard from './ZoneDetailCard.svelte';
  import type { ZoneMetric, AoiCard } from '$lib/map/types';

  const { Story } = defineMeta({
    title: 'Organisms/ZoneDetailCard',
    component: ZoneDetailCard
  });

  const zone: ZoneMetric = {
    zone_id: 'dgo-z-003',
    zone_label: 'Upper North-Facing Ridge',
    temp_delta_f: -8,
    wind_delta_mph: 14,
    precip_delta_pct: 24,
    snow_delta_in: 4.1,
    confidence_level: 'low',
    confidence_score: 0.37,
    confidence_reason_codes: ['high_spread', 'verification_noise'],
    hazards: ['snow', 'wind'],
    updated_at: new Date().toISOString()
  };

  const aoi: AoiCard = {
    aoi_slug: 'purgatory-resort',
    aoi_name: 'Purgatory Resort',
    note: 'Located within Upper North-Facing Ridge',
    zone_id: 'dgo-z-003'
  };
</script>

<Story
  name="With AOI"
  args={{
    zone,
    aoi,
    activeMetric: 'snow_delta_in',
    onClose: () => undefined
  }}
/>
