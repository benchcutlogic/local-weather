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

  let {
    label,
    value,
    unit,
    trend,
    disagreement,
    note,
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
  class="bg-white rounded-xl border border-wx-100 shadow-sm p-4 flex flex-col gap-1 {cls}"
  role="region"
  aria-label={label}
>
  <p class="text-xs font-medium text-wx-500 uppercase tracking-wide">{label}</p>

  {#if loading}
    <Skeleton height="h-7" width="w-2/3" class="mt-1" />
    <Skeleton height="h-3" width="w-full" class="mt-2" />
  {:else}
    <div class="flex items-baseline gap-1">
      <span class="text-2xl font-bold text-wx-900">{value ?? '—'}</span>
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
