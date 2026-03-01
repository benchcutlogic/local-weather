<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import WeatherIcon from './WeatherIcon.svelte';

  const { Story } = defineMeta({
    title: 'Atoms/WeatherIcon',
    component: WeatherIcon
  });
</script>

<Story name="Sunny" args={{ condition: 'sunny', size: 'lg' }} />
<Story name="Partly Cloudy" args={{ condition: 'partly_cloudy', size: 'lg' }} />
<Story name="Cloudy" args={{ condition: 'cloudy', size: 'lg' }} />
<Story name="Rain" args={{ condition: 'rain', size: 'lg' }} />
<Story name="Snow" args={{ condition: 'snow', size: 'lg' }} />
<Story name="Thunderstorm" args={{ condition: 'thunderstorm', size: 'lg' }} />
<Story name="Fog" args={{ condition: 'fog', size: 'lg' }} />
<Story name="Wind" args={{ condition: 'wind', size: 'lg' }} />
<Story name="Blizzard" args={{ condition: 'blizzard', size: 'lg' }} />
<Story name="Unknown" args={{ condition: 'unknown', size: 'lg' }} />
<Story name="Small" args={{ condition: 'sunny', size: 'sm' }} />
<Story name="Medium" args={{ condition: 'rain', size: 'md' }} />
