<script lang="ts">
  import type { ZoneMetricKey } from '$lib/map/types';

  let { metric }: { metric: ZoneMetricKey } = $props();

  const labels: Record<ZoneMetricKey, string> = {
    temp_delta_f: 'Temperature delta (°F)',
    wind_delta_mph: 'Wind delta (mph)',
    precip_delta_pct: 'Precipitation delta (%)',
    snow_delta_in: 'Snow delta (in)'
  };
</script>

<div class="rounded-lg border border-wx-100 bg-wx-50 p-3 text-xs text-wx-800" aria-label="Map legend">
  <p class="mb-2 font-semibold">{labels[metric]}</p>
  <div class="mb-3 flex flex-wrap gap-3">
    <span class="inline-flex items-center gap-2"><span class="h-3 w-3 rounded bg-[#313695]"></span>Lower</span>
    <span class="inline-flex items-center gap-2"><span class="h-3 w-3 rounded border border-wx-200 bg-[#ffffbf]"></span>Near baseline</span>
    <span class="inline-flex items-center gap-2"><span class="h-3 w-3 rounded bg-[#a50026]"></span>Higher</span>
  </div>
  <div class="flex flex-wrap gap-3">
    <span class="inline-flex items-center gap-2">
      <span
        class="h-3 w-3 rounded border border-wx-300 bg-wx-100"
        style="background-image: repeating-linear-gradient(135deg, rgba(15,23,42,0.45) 0 1px, transparent 1px 4px);"
      ></span>
      Low confidence texture
    </span>
    <span class="inline-flex items-center gap-2"><span class="h-2 w-2 rounded-full bg-orange-500"></span>Hazard marker</span>
  </div>
</div>
