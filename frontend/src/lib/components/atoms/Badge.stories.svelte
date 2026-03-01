<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import Badge from './Badge.svelte';

  const { Story } = defineMeta({
    title: 'Atoms/Badge',
    component: Badge
  });
</script>

<Story name="Default" args={{ text: 'Example badge', tone: 'default' }} />
<Story name="Info" args={{ text: 'Info badge', tone: 'info' }} />
<Story name="Warning" args={{ text: 'Warning badge', tone: 'warning' }} />
