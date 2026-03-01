<script lang="ts">
  let {
    showAoi,
    showConfidence,
    showHazards,
    onToggle
  }: {
    showAoi: boolean;
    showConfidence: boolean;
    showHazards: boolean;
    onToggle: (layer: 'aoi' | 'confidence' | 'hazards', enabled: boolean) => void;
  } = $props();

  const toggleDefs: Array<{
    key: 'aoi' | 'confidence' | 'hazards';
    label: string;
    help: string;
  }> = [
    { key: 'aoi', label: 'AOI boundaries', help: 'Show areas of interest' },
    { key: 'confidence', label: 'Confidence texture', help: 'Show low-confidence hatch overlay' },
    { key: 'hazards', label: 'Hazard points', help: 'Show zone hazard markers' }
  ];

  function isChecked(key: 'aoi' | 'confidence' | 'hazards'): boolean {
    if (key === 'aoi') return showAoi;
    if (key === 'confidence') return showConfidence;
    return showHazards;
  }
</script>

<div class="flex flex-wrap gap-3" aria-label="Map layers">
  {#each toggleDefs as toggle}
    <label class="inline-flex items-center gap-2 rounded-md border border-wx-200 bg-white px-2.5 py-1.5 text-xs text-wx-800">
      <input
        type="checkbox"
        checked={isChecked(toggle.key)}
        aria-label={toggle.help}
        onchange={(event) => onToggle(toggle.key, (event.currentTarget as HTMLInputElement).checked)}
      />
      <span>{toggle.label}</span>
    </label>
  {/each}
</div>
