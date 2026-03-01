<script lang="ts">
  import type { ConfidenceLevel } from '$lib/map/types';

  let {
    level,
    score = undefined
  }: {
    level: ConfidenceLevel;
    score?: number;
  } = $props();

  const classes: Record<ConfidenceLevel, string> = {
    high: 'bg-emerald-100 text-emerald-900 border-emerald-300',
    moderate: 'bg-amber-100 text-amber-900 border-amber-300',
    low: 'bg-rose-100 text-rose-900 border-rose-300'
  };
</script>

<span
  class={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold ${classes[level]}`}
  aria-label={score != null ? `Confidence ${level} (${Math.round(score * 100)} percent)` : `Confidence ${level}`}
>
  {level}
  {#if score != null}
    <span class="font-mono text-[10px]">{Math.round(score * 100)}%</span>
  {/if}
</span>
