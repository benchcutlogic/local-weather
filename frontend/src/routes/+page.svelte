<script lang="ts">
  import { metersToFeet } from '$lib/cities';

  let { data } = $props();
  let query = $state('');

  const filteredCities = $derived.by(() => {
    const q = query.trim().toLowerCase();
    return data.cities.filter((city) => {
      if (!q) return true;
      return (
        city.name.toLowerCase().includes(q) ||
        city.slug.includes(q) ||
        city.aliases.some((alias) => alias.includes(q))
      );
    });
  });
</script>

<svelte:head>
  <title>Hyperlocal Weather Forecasts</title>
  <meta
    name="description"
    content="Multi-model forecasts with terrain-aware AI analysis across elevation bands."
  />
</svelte:head>

<div class="text-center mb-10">
  <h1 class="text-4xl md:text-5xl font-bold text-wx-900 mb-3">Mountain Weather, Decoded</h1>
  <p class="text-lg text-wx-700 max-w-2xl mx-auto">
    Multi-model forecasts with terrain-aware AI analysis. Know what's happening at every elevation
    band — from the valley floor to the peaks.
  </p>
</div>

<div class="max-w-md mx-auto mb-10">
  <input
    bind:value={query}
    type="text"
    placeholder="Search cities..."
    class="w-full px-4 py-3 rounded-xl border border-wx-200 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-wx-500"
  />
</div>

<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {#each filteredCities as city (city.slug)}
    <a
      href={`/${city.slug}`}
      class="group block bg-white rounded-xl shadow-sm border border-wx-100 hover:shadow-md hover:border-wx-300 transition-all duration-200"
    >
      <div class="p-6">
        <h2 class="text-xl font-bold text-wx-900 group-hover:text-wx-600 transition-colors">
          {city.name}, {city.state}
        </h2>
        <p class="text-sm text-wx-500 mt-0.5">{city.lat.toFixed(2)}°N, {Math.abs(city.lon).toFixed(2)}°W</p>

        <div class="flex flex-wrap gap-1.5 mt-4">
          {#each city.elevBandsM as band}
            <span class="inline-block px-2 py-0.5 bg-wx-50 text-wx-700 text-xs rounded-full font-medium">
              {metersToFeet(band).toLocaleString()} ft
            </span>
          {/each}
        </div>

        <div class="mt-4 pt-3 border-t border-wx-50">
          <p class="text-sm text-wx-500">{city.elevBandsM.length} elevation bands tracked</p>
        </div>
      </div>
    </a>
  {/each}
</div>
