<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import MetricSelector from './MetricSelector.svelte';

  const { Story } = defineMeta({
    title: 'Molecules/MetricSelector',
    component: MetricSelector
  });
</script>

<Story
  name="Default"
  args={{
    selected: 'temp_delta_f',
    onSelect: () => undefined
  }}
/>
