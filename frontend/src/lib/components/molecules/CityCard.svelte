<script lang="ts">
  /**
   * CityCard — homepage card for a city.
   * Shows city name/state, coordinates, elevation bands, and a quick-meta row.
   * Fires analytics on mount/click via the parent page (analytics at route level).
   */
  import { metersToFeet } from '$lib/cities';
  import type { City } from '$lib/cities';

  let {
    city,
    href
  }: {
    city: City;
    href: string;
  } = $props();
</script>

<a
  {href}
  class="group block bg-white rounded-xl shadow-sm border border-wx-100 hover:shadow-md hover:border-wx-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-wx-500 focus-visible:ring-offset-2 transition-all duration-200"
  aria-label="{city.name}, {city.state} weather forecast"
>
  <div class="p-6">
    <h2 class="text-xl font-bold text-wx-900 group-hover:text-wx-600 transition-colors">
      {city.name}, {city.state}
    </h2>
    <p class="text-sm text-wx-500 mt-0.5" aria-label="Coordinates">
      {city.lat.toFixed(2)}°N, {Math.abs(city.lon).toFixed(2)}°W
    </p>

    {#if city.branding?.localTagline}
      <p class="text-xs text-wx-600 italic mt-1">{city.branding.localTagline}</p>
    {/if}

    <div class="flex flex-wrap gap-1.5 mt-4" aria-label="Elevation bands">
      {#each city.elevBandsM as band}
        <span
          class="inline-block px-2 py-0.5 bg-wx-50 text-wx-700 text-xs rounded-full font-medium"
          title="{metersToFeet(band).toLocaleString()} ft elevation band"
        >
          {metersToFeet(band).toLocaleString()} ft
        </span>
      {/each}
    </div>

    <div class="mt-4 pt-3 border-t border-wx-50 flex items-center justify-between">
      <p class="text-sm text-wx-500">
        {city.elevBandsM.length} elevation band{city.elevBandsM.length !== 1 ? 's' : ''} tracked
      </p>
      {#if city.terrainProfile}
        <span class="text-xs px-2 py-0.5 bg-wx-100 text-wx-700 rounded-full capitalize">
          {city.terrainProfile}
        </span>
      {/if}
    </div>

    {#if city.seasonalHazards.length > 0}
      <div class="mt-2 flex flex-wrap gap-1" aria-label="Seasonal hazards">
        {#each city.seasonalHazards.slice(0, 3) as hazard}
          <span class="text-[10px] text-wx-400 uppercase tracking-wide">{hazard.replace(/_/g, ' ')}</span>
        {/each}
      </div>
    {/if}
  </div>
</a>
