<script lang="ts">
  import { enhance } from '$app/forms';
  import { metersToFeet } from '$lib/cities';
  import MicroclimateMap from '$lib/components/organisms/MicroclimateMap.svelte';

  let { data } = $props();

  const confidenceColors: Record<string, string> = {
    high: 'bg-green-100 text-green-800 border-green-200',
    moderate: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    low: 'bg-red-100 text-red-800 border-red-200'
  };

  function timeAgo(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  }
</script>

<svelte:head>
  <title>{data.cityConfig.name}, {data.cityConfig.state} Weather</title>
  <meta
    name="description"
    content={data.commentary?.headline ||
      `Hyperlocal weather forecast for ${data.cityConfig.name}, ${data.cityConfig.state}`}
  />
</svelte:head>

<nav class="text-sm text-wx-500 mb-4">
  <a href="/" class="hover:text-wx-700">Cities</a>
  <span class="mx-1">/</span>
  <span class="text-wx-900 font-medium">{data.cityConfig.name}, {data.cityConfig.state}</span>
</nav>

{#if data.commentary}
  <div class="bg-gradient-to-r from-wx-800 to-wx-900 text-white rounded-xl p-6 mb-6">
    <h1 class="text-2xl md:text-3xl font-bold mb-2">{data.commentary.headline}</h1>
    <div class="flex flex-wrap items-center gap-3 text-sm text-wx-200">
      <span>Updated {timeAgo(data.commentary.updated_at)}</span>
      <span
        class={`px-2 py-0.5 rounded-full text-xs font-medium border ${confidenceColors[data.commentary.confidence.level]}`}
      >
        {data.commentary.confidence.level.toUpperCase()} confidence
      </span>
      <span class="text-wx-300">Best model: <span class="text-white font-medium">{data.commentary.best_model}</span></span>
    </div>
  </div>

  <div class="mb-6">
    <MicroclimateMap citySlug={data.citySlug} fallbackAois={data.fallbackAois} />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div class="lg:col-span-2 space-y-6">
      <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
        <h2 class="text-lg font-bold text-wx-900 mb-3">Current Conditions</h2>
        <p class="text-wx-700 leading-relaxed">{data.commentary.current_conditions}</p>
      </section>

      <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
        <h2 class="text-lg font-bold text-wx-900 mb-3">Today's Forecast</h2>
        <p class="text-wx-700 leading-relaxed">{data.commentary.todays_forecast}</p>
      </section>

      <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
        <h2 class="text-lg font-bold text-wx-900 mb-3">Elevation Breakdown</h2>
        <p class="text-wx-700 leading-relaxed mb-4">{data.commentary.elevation_breakdown.summary}</p>
        <div class="space-y-3">
          {#each data.commentary.elevation_breakdown.bands as band}
            <div class="flex items-start gap-3 pl-3 border-l-2 border-wx-200">
              <span class="font-mono text-sm font-semibold text-wx-600 whitespace-nowrap min-w-[80px]">
                {band.elevation_ft.toLocaleString()} ft
              </span>
              <p class="text-sm text-wx-700">{band.description}</p>
            </div>
          {/each}
        </div>
      </section>
    </div>

    <div class="space-y-6">
      <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
        <h2 class="text-lg font-bold text-wx-900 mb-3">Community Reports</h2>
        {#if data.reports.length > 0}
          <div class="space-y-2 mb-4 max-h-48 overflow-y-auto">
            {#each data.reports as report}
              <div class="text-sm border-b border-wx-50 pb-2 last:border-0">
                <div class="text-wx-500 text-xs">{timeAgo(report.created_at)}</div>
                {#if report.notes}<p class="text-wx-700 mt-0.5">{report.notes}</p>{/if}
              </div>
            {/each}
          </div>
        {/if}

        <form method="POST" action="?/report" use:enhance class="space-y-2">
          <textarea
            name="notes"
            placeholder="What's it like outside?"
            rows="2"
            class="w-full px-3 py-2 text-sm border border-wx-200 rounded-lg"
          ></textarea>
          <div class="grid grid-cols-2 gap-2">
            <input type="number" name="temp_f" placeholder="Temp (°F)" step="1" class="px-3 py-1.5 text-sm border border-wx-200 rounded-lg" />
            <input type="number" name="snow_in" placeholder="Snow (in)" step="0.1" class="px-3 py-1.5 text-sm border border-wx-200 rounded-lg" />
          </div>
          <button type="submit" class="w-full bg-wx-600 hover:bg-wx-500 text-white text-sm font-medium py-2 rounded-lg">Submit Report</button>
        </form>
      </section>
    </div>
  </div>
{:else}
  <div class="text-center py-16">
    <h1 class="text-3xl font-bold text-wx-900 mb-3">{data.cityConfig.name}, {data.cityConfig.state}</h1>
    <p class="text-wx-600 mb-2">Forecast commentary is being generated. Check back soon!</p>
    <p class="text-sm text-wx-400">
      Tracking {data.cityConfig.elevBandsM.length} elevation bands from
      {metersToFeet(data.cityConfig.elevBandsM[0]).toLocaleString()} ft to
      {metersToFeet(data.cityConfig.elevBandsM[data.cityConfig.elevBandsM.length - 1]).toLocaleString()} ft.
    </p>
  </div>
{/if}
