<script lang="ts">
  import ConfidenceBadge from '$lib/components/atoms/ConfidenceBadge.svelte';
  import HazardBadge from '$lib/components/atoms/HazardBadge.svelte';
  import type { AoiCard, ZoneMetric, ZoneMetricKey } from '$lib/map/types';

  let {
    zone,
    aoi,
    activeMetric,
    onClose
  }: {
    zone: ZoneMetric;
    aoi: AoiCard | null;
    activeMetric: ZoneMetricKey;
    onClose: () => void;
  } = $props();

  const metricLabels: Record<ZoneMetricKey, string> = {
    temp_delta_f: 'Temp delta',
    wind_delta_mph: 'Wind delta',
    precip_delta_pct: 'Precip delta',
    snow_delta_in: 'Snow delta'
  };

  function displayMetricValue(metric: ZoneMetricKey, currentZone: ZoneMetric): string {
    const value = currentZone[metric];

    if (metric === 'temp_delta_f') return `${value > 0 ? '+' : ''}${value} °F`;
    if (metric === 'wind_delta_mph') return `${value > 0 ? '+' : ''}${value} mph`;
    if (metric === 'precip_delta_pct') return `${value > 0 ? '+' : ''}${value}%`;
    return `${value > 0 ? '+' : ''}${value} in`;
  }
</script>

<aside class="rounded-xl border border-wx-200 bg-white p-4 shadow-sm" aria-live="polite">
  <div class="mb-3 flex items-start justify-between gap-2">
    <div>
      <p class="text-sm font-semibold text-wx-900">{zone.zone_label}</p>
      {#if aoi}
        <p class="text-xs text-wx-600">AOI: {aoi.aoi_name}</p>
      {/if}
    </div>
    <button
      type="button"
      class="rounded border border-wx-200 px-2 py-1 text-xs text-wx-700 hover:border-wx-400"
      onclick={onClose}
      aria-label="Close map detail"
    >
      Close
    </button>
  </div>

  <div class="mb-3 flex flex-wrap items-center gap-2">
    <ConfidenceBadge level={zone.confidence_level} score={zone.confidence_score} />
    <span class="rounded-full border border-wx-200 bg-wx-50 px-2 py-0.5 text-xs text-wx-800">
      {metricLabels[activeMetric]}: {displayMetricValue(activeMetric, zone)}
    </span>
  </div>

  <div class="mb-3 text-xs text-wx-700">
    <p class="font-semibold text-wx-900">Confidence rationale</p>
    <p>{zone.confidence_reason_codes?.join(', ') ?? '—'}</p>
  </div>

  <div class="flex flex-wrap gap-2" aria-label="Zone hazards">
    {#if zone.hazards.length > 0}
      {#each zone.hazards as hazard}
        <HazardBadge {hazard} />
      {/each}
    {:else}
      <p class="text-xs text-wx-500">No active hazards.</p>
    {/if}
  </div>
</aside>
