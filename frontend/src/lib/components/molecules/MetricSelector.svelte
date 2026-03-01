<script lang="ts">
  import type { ZoneMetricKey } from '$lib/map/types';

  let {
    selected,
    onSelect
  }: {
    selected: ZoneMetricKey;
    onSelect: (metric: ZoneMetricKey) => void;
  } = $props();

  const options: Array<{ key: ZoneMetricKey; label: string }> = [
    { key: 'temp_delta_f', label: 'Temp' },
    { key: 'wind_delta_mph', label: 'Wind' },
    { key: 'precip_delta_pct', label: 'Precip' },
    { key: 'snow_delta_in', label: 'Snow' }
  ];
</script>

<div class="flex flex-wrap items-center gap-2" role="radiogroup" aria-label="Map metric">
  {#each options as option}
    <button
      type="button"
      role="radio"
      aria-checked={selected === option.key}
      class={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
        selected === option.key
          ? 'border-wx-700 bg-wx-700 text-white'
          : 'border-wx-200 bg-white text-wx-700 hover:border-wx-400'
      }`}
      onclick={() => onSelect(option.key)}
    >
      {option.label}
    </button>
  {/each}
</div>
