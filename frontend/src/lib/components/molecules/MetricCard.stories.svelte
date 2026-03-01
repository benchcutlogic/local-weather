<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import MetricCard from './MetricCard.svelte';

  const { Story } = defineMeta({
    title: 'Molecules/MetricCard',
    component: MetricCard
  });
</script>

<Story name="Default" args={{ label: 'Temperature', value: '32', unit: '°F' }} />
<Story name="Trending Up" args={{ label: 'Wind Speed', value: '45', unit: 'mph', trend: 'up', note: 'Gusts possible' }} />
<Story name="Trending Down" args={{ label: 'Snowpack', value: '18', unit: 'in', trend: 'down' }} />
<Story name="With Disagreement" args={{ label: 'High Temp', value: '54', unit: '°F', disagreement: 'HRRR vs GFS: ±6°F' }} />
<Story name="Loading" args={{ label: 'Confidence', value: 'HIGH', loading: true }} />
<Story name="No Value" args={{ label: 'Extended Outlook', value: undefined }} />
