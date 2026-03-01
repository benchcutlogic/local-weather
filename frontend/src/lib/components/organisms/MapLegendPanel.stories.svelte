<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import MapLegendPanel from './MapLegendPanel.svelte';

  const { Story } = defineMeta({
    title: 'Organisms/MapLegendPanel',
    component: MapLegendPanel
  });
</script>

<Story name="Temperature" args={{ metric: 'temp_delta_f' }} />
<Story name="Snow" args={{ metric: 'snow_delta_in' }} />
