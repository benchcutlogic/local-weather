<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import CityCard from './CityCard.svelte';
  import type { City } from '$lib/cities';

  const { Story } = defineMeta({
    title: 'Molecules/CityCard',
    component: CityCard
  });

  const durango: City = {
    slug: 'durango',
    aliases: ['dgo'],
    name: 'Durango',
    state: 'CO',
    lat: 37.2753,
    lon: -107.8801,
    timezone: 'America/Denver',
    elevBandsM: [2000, 2200, 2500, 2800, 3000],
    aoiSlug: 'la-plata-county',
    terrainProfile: 'mountain',
    seasonalHazards: ['snowpack', 'monsoon_flooding', 'fire_smoke'],
    alertThresholds: { snowIn24hIn: 10, windGustMph: 50 },
    branding: { localTagline: 'Mountain weather for town, trails, and passes' }
  };

  const denver: City = {
    slug: 'denver',
    aliases: ['den'],
    name: 'Denver',
    state: 'CO',
    lat: 39.7392,
    lon: -104.9903,
    timezone: 'America/Denver',
    elevBandsM: [1500, 1600, 1700, 1800, 2000],
    terrainProfile: 'plains',
    seasonalHazards: ['snow', 'hail', 'high_wind'],
    branding: { localTagline: 'Front Range weather with elevation-aware detail' }
  };
</script>

<Story name="Mountain City" args={{ city: durango, href: '/durango' }} />
<Story name="Plains City" args={{ city: denver, href: '/denver' }} />
