<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import LayerToggleGroup from './LayerToggleGroup.svelte';

  const { Story } = defineMeta({
    title: 'Molecules/LayerToggleGroup',
    component: LayerToggleGroup
  });
</script>

<Story
  name="Default"
  args={{
    showAoi: true,
    showConfidence: true,
    showHazards: false,
    onToggle: () => undefined
  }}
/>
