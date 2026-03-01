<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import HazardBadge from './HazardBadge.svelte';

  const { Story } = defineMeta({
    title: 'Atoms/HazardBadge',
    component: HazardBadge
  });
</script>

<Story name="Snow" args={{ hazard: 'snow' }} />
<Story name="Wind" args={{ hazard: 'wind' }} />
<Story name="Whiteout" args={{ hazard: 'whiteout_risk' }} />
