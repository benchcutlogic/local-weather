<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import ConfidenceBadge from './ConfidenceBadge.svelte';

  const { Story } = defineMeta({
    title: 'Atoms/ConfidenceBadge',
    component: ConfidenceBadge
  });
</script>

<Story name="High" args={{ level: 'high', score: 0.86 }} />
<Story name="Moderate" args={{ level: 'moderate', score: 0.62 }} />
<Story name="Low" args={{ level: 'low', score: 0.33 }} />
