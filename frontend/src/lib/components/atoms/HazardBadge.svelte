<script lang="ts">
  import type { HazardType } from '$lib/map/types';

  let { hazard }: { hazard: HazardType } = $props();

  const labels: Record<HazardType, string> = {
    snow: 'Snow',
    wind: 'Wind',
    flood: 'Flood',
    smoke: 'Smoke',
    fog: 'Fog',
    dry_air: 'Dry Air',
    whiteout_risk: 'Whiteout Risk'
  };

  const classes: Record<HazardType, string> = {
    snow: 'bg-sky-100 text-sky-900 border-sky-300',
    wind: 'bg-indigo-100 text-indigo-900 border-indigo-300',
    flood: 'bg-cyan-100 text-cyan-900 border-cyan-300',
    smoke: 'bg-orange-100 text-orange-900 border-orange-300',
    fog: 'bg-slate-100 text-slate-900 border-slate-300',
    dry_air: 'bg-yellow-100 text-yellow-900 border-yellow-300',
    whiteout_risk: 'bg-violet-100 text-violet-900 border-violet-300'
  };
</script>

<span class={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${classes[hazard]}`}>
  {labels[hazard]}
</span>
