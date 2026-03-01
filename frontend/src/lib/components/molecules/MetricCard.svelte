<script lang="ts">
  /**
   * MetricCard — compact card for a single weather metric.
   * Used in the city page "at a glance" row and elsewhere.
   *
   * Supports:
   *  - label + value + optional unit
   *  - optional trend indicator (up / down / stable)
   *  - optional disagreement chip (model spread signal)
   *  - optional secondary note
   */

  import Skeleton from '$lib/components/atoms/Skeleton.svelte';

  type Trend = 'up' | 'down' | 'stable';
  type IconName = 'confidence' | 'model' | 'elevation' | 'clock' | 'temp' | 'wind' | 'snow' | 'alert';

  const iconPaths: Record<IconName, string> = {
    confidence: '<circle cx="12" cy="12" r="9"/><path d="m9 12 2 2 4-4"/>',
    model: '<path d="M9 19v-6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2zm0 0V9a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v10m-6 0a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2m0 0V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2z"/>',
    elevation: '<path d="M3 20 L9 8 L14 14 L18 6 L22 20 Z"/>',
    clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    temp: '<path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/>',
    wind: '<path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/><path d="M12.6 19.4A2 2 0 1 0 14 16H2"/>',
    snow: '<path d="M20 17.58A5 5 0 0 0 18 8h-1.26A8 8 0 1 0 4 16.25"/><line x1="8" y1="16" x2="8.01" y2="16"/><line x1="8" y1="20" x2="8.01" y2="20"/><line x1="12" y1="18" x2="12.01" y2="18"/><line x1="12" y1="22" x2="12.01" y2="22"/><line x1="16" y1="16" x2="16.01" y2="16"/><line x1="16" y1="20" x2="16.01" y2="20"/>',
    alert: '<path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'
  };

  let {
    label,
    value,
    unit,
    trend,
    disagreement,
    note,
    icon,
    loading = false,
    class: cls = ''
  }: {
    label: string;
    value?: string | number;
    unit?: string;
    /** Trend direction vs. yesterday / prior run. */
    trend?: Trend;
    /** Model disagreement label, e.g. "HRRR vs GFS: ±4°F". */
    disagreement?: string;
    note?: string;
    /** Optional icon name to display in the card header. */
    icon?: IconName;
    loading?: boolean;
    class?: string;
  } = $props();

  const trendIcon: Record<Trend, { symbol: string; cls: string; ariaLabel: string }> = {
    up: { symbol: '↑', cls: 'text-orange-500', ariaLabel: 'trending up' },
    down: { symbol: '↓', cls: 'text-wx-600', ariaLabel: 'trending down' },
    stable: { symbol: '→', cls: 'text-wx-400', ariaLabel: 'stable' }
  };

  const trendMeta = $derived(trend ? trendIcon[trend] : null);
</script>

<div
  class="card-stitch p-3.5 flex flex-col gap-0.5 {cls}"
  role="region"
  aria-label={label}
>
  <div class="flex items-center gap-1.5 mb-0.5">
    {#if icon && iconPaths[icon]}
      <svg class="w-3.5 h-3.5 text-wx-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">{@html iconPaths[icon]}</svg>
    {/if}
    <p class="text-[11px] font-semibold text-wx-500 uppercase tracking-wider">{label}</p>
  </div>

  {#if loading}
    <Skeleton height="h-7" width="w-2/3" class="mt-1" />
    <Skeleton height="h-3" width="w-full" class="mt-2" />
  {:else}
    <div class="flex items-baseline gap-1">
      <span class="text-xl font-extrabold text-wx-900">{value ?? '—'}</span>
      {#if unit}
        <span class="text-sm text-wx-500">{unit}</span>
      {/if}
      {#if trendMeta}
        <span
          class="ml-1 text-sm font-semibold {trendMeta.cls}"
          aria-label={trendMeta.ariaLabel}
          title={trendMeta.ariaLabel}
        >
          {trendMeta.symbol}
        </span>
      {/if}
    </div>

    {#if disagreement}
      <span
        class="self-start inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200"
        title="Model disagreement signal"
      >
        <svg class="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
        </svg>
        {disagreement}
      </span>
    {/if}

    {#if note}
      <p class="text-xs text-wx-500 mt-0.5">{note}</p>
    {/if}
  {/if}
</div>
