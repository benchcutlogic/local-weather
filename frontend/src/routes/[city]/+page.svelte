<script lang="ts">
  import { onMount } from 'svelte';
  import { enhance } from '$app/forms';
  import { metersToFeet } from '$lib/cities';
  import ForecastTabs from '$lib/components/molecules/ForecastTabs.svelte';
  import MetricCard from '$lib/components/molecules/MetricCard.svelte';
  import WeatherIcon from '$lib/components/atoms/WeatherIcon.svelte';
  import Skeleton from '$lib/components/atoms/Skeleton.svelte';
  import MicroclimateMap from '$lib/components/organisms/MicroclimateMap.svelte';
  import { track } from '$lib/analytics/index';
  import type { TabId } from '$lib/components/molecules/ForecastTabs.svelte';

  let { data } = $props();

  let activeTab = $state<TabId>('forecast');
  let reportSubmitting = $state(false);
  let commentaryLoading = $state(true);

  const confidenceColors: Record<string, string> = {
    high: 'bg-green-100 text-green-800 border-green-200',
    moderate: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    low: 'bg-red-100 text-red-800 border-red-200'
  };

  // Non-color confidence signal (dots pattern for non-color reliance)
  const confidenceShapes: Record<string, string> = {
    high: '●●●',
    moderate: '●●○',
    low: '●○○'
  };

  function timeAgo(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  }

  function handleTabChange(tab: TabId) {
    activeTab = tab;
    track('forecast_tab_viewed', {
      city_slug: data.citySlug,
      tab
    });
  }

  onMount(() => {
    setTimeout(() => (commentaryLoading = false), 120);
    track('city_page_viewed', {
      city_slug: data.citySlug,
      has_commentary: !!data.commentary
    });
  });

  const quickMetrics = $derived.by(() => {
    const c = data.commentary;
    if (!c) return null;
    return {
      confidence: c.confidence.level,
      bestModel: c.best_model,
      updatedAt: c.updated_at
    };
  });
</script>

<svelte:head>
  <title>{data.cityConfig.name}, {data.cityConfig.state} Weather</title>
  <meta
    name="description"
    content={data.commentary?.headline ??
      `Hyperlocal weather forecast for ${data.cityConfig.name}, ${data.cityConfig.state}`}
  />
</svelte:head>

<!-- Breadcrumb -->
<nav class="text-sm text-wx-500 mb-4" aria-label="Breadcrumb">
  <ol class="flex items-center gap-1">
    <li><a href="/" class="hover:text-wx-700 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-wx-500 rounded">Cities</a></li>
    <li aria-hidden="true" class="mx-1">/</li>
    <li class="text-wx-900 font-medium" aria-current="page">
      {data.cityConfig.name}, {data.cityConfig.state}
    </li>
  </ol>
</nav>

{#if data.commentary}
  <!-- Hero header -->
  <div class="bg-gradient-to-r from-wx-800 to-wx-900 text-white rounded-xl p-6 mb-6">
    <div class="flex items-start gap-4">
      <WeatherIcon condition="cloudy" size="lg" label="Current weather" />
      <div class="flex-1 min-w-0">
        <h1 class="text-2xl md:text-3xl font-bold mb-2">{data.commentary.headline}</h1>
        <div class="flex flex-wrap items-center gap-3 text-sm text-wx-200">
          <span>Updated {timeAgo(data.commentary.updated_at)}</span>
          <span
            class="px-2 py-0.5 rounded-full text-xs font-medium border {confidenceColors[data.commentary.confidence.level]}"
            aria-label="Confidence level: {data.commentary.confidence.level}"
          >
            <span aria-hidden="true">{confidenceShapes[data.commentary.confidence.level]}</span>
            {data.commentary.confidence.level.toUpperCase()} confidence
          </span>
          <span class="text-wx-300">
            Best model: <span class="text-white font-medium">{data.commentary.best_model}</span>
          </span>
        </div>
      </div>
    </div>
  </div>

  <!-- At-a-glance MetricCards row -->
  <div
    class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6"
    aria-label="At-a-glance forecast metrics"
  >
    <MetricCard
      label="Confidence"
      value={quickMetrics?.confidence.toUpperCase() ?? '—'}
      loading={commentaryLoading}
    />
    <MetricCard
      label="Best Model"
      value={quickMetrics?.bestModel ?? '—'}
      loading={commentaryLoading}
    />
    <MetricCard
      label="Elevation Bands"
      value={data.cityConfig.elevBandsM.length}
      unit="bands"
      loading={commentaryLoading}
    />
    <MetricCard
      label="Last Updated"
      value={quickMetrics ? timeAgo(quickMetrics.updatedAt) : '—'}
      loading={commentaryLoading}
    />
  </div>

  <!-- Tabbed navigation -->
  <ForecastTabs {activeTab} onTabChange={handleTabChange} />

  <!-- Forecast tab panel -->
  <div
    id="tabpanel-forecast"
    role="tabpanel"
    aria-labelledby="tab-forecast"
    class={activeTab === 'forecast' ? 'block mt-6' : 'hidden'}
    tabindex="0"
  >
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 space-y-6">
        <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
          <h2 class="text-lg font-bold text-wx-900 mb-3">Current Conditions</h2>
          {#if commentaryLoading}
            <div class="space-y-2" aria-busy="true" aria-label="Loading current conditions">
              <Skeleton height="h-4" />
              <Skeleton height="h-4" width="w-4/5" />
              <Skeleton height="h-4" width="w-3/5" />
            </div>
          {:else}
            <p class="text-wx-700 leading-relaxed">{data.commentary.current_conditions}</p>
          {/if}
        </section>

        <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
          <h2 class="text-lg font-bold text-wx-900 mb-3">Today's Forecast</h2>
          {#if commentaryLoading}
            <div class="space-y-2" aria-busy="true" aria-label="Loading forecast">
              <Skeleton height="h-4" />
              <Skeleton height="h-4" width="w-5/6" />
              <Skeleton height="h-4" width="w-2/3" />
            </div>
          {:else}
            <p class="text-wx-700 leading-relaxed">{data.commentary.todays_forecast}</p>
          {/if}
        </section>

        <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
          <h2 class="text-lg font-bold text-wx-900 mb-3">Elevation Breakdown</h2>
          {#if commentaryLoading}
            <div class="space-y-3" aria-busy="true" aria-label="Loading elevation breakdown">
              {#each { length: 3 } as _}
                <div class="flex items-start gap-3 pl-3 border-l-2 border-wx-100">
                  <Skeleton height="h-4" width="w-20" />
                  <Skeleton height="h-4" />
                </div>
              {/each}
            </div>
          {:else}
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
          {/if}
        </section>
      </div>

      <div class="space-y-6">
        <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
          <h2 class="text-lg font-bold text-wx-900 mb-3">Community Reports</h2>
          {#if data.reports.length > 0}
            <div class="space-y-2 mb-4 max-h-48 overflow-y-auto" role="feed" aria-label="Community weather reports">
              {#each data.reports as report}
                <article class="text-sm border-b border-wx-50 pb-2 last:border-0">
                  <div class="text-wx-500 text-xs">{timeAgo(report.created_at)}</div>
                  {#if report.notes}<p class="text-wx-700 mt-0.5">{report.notes}</p>{/if}
                </article>
              {/each}
            </div>
          {/if}

          <form
            method="POST"
            action="?/report"
            use:enhance={({ formData }) => {
              reportSubmitting = true;
              const hasTemp = !!formData.get('temp_f');
              const hasSnow = !!formData.get('snow_in');
              return async ({ update }) => {
                reportSubmitting = false;
                track('report_submitted', {
                  city_slug: data.citySlug,
                  has_temp: hasTemp,
                  has_snow: hasSnow
                });
                await update();
              };
            }}
            class="space-y-2"
            aria-label="Submit community weather report"
          >
            <label for="report-notes" class="sr-only">Weather observation notes</label>
            <textarea
              id="report-notes"
              name="notes"
              placeholder="What's it like outside?"
              rows="2"
              class="w-full px-3 py-2 text-sm border border-wx-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-wx-400"
              disabled={reportSubmitting}
            ></textarea>
            <div class="grid grid-cols-2 gap-2">
              <label class="contents">
                <span class="sr-only">Temperature in Fahrenheit</span>
                <input
                  type="number"
                  name="temp_f"
                  placeholder="Temp (°F)"
                  step="1"
                  class="px-3 py-1.5 text-sm border border-wx-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-wx-400"
                  disabled={reportSubmitting}
                />
              </label>
              <label class="contents">
                <span class="sr-only">Snow depth in inches</span>
                <input
                  type="number"
                  name="snow_in"
                  placeholder="Snow (in)"
                  step="0.1"
                  class="px-3 py-1.5 text-sm border border-wx-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-wx-400"
                  disabled={reportSubmitting}
                />
              </label>
            </div>
            <button
              type="submit"
              disabled={reportSubmitting}
              class="w-full bg-wx-600 hover:bg-wx-500 disabled:opacity-60 text-white text-sm font-medium py-2 rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-wx-400"
            >
              {reportSubmitting ? 'Submitting...' : 'Submit Report'}
            </button>
          </form>
        </section>
      </div>
    </div>
  </div>

  <!-- Outlook tab panel -->
  <div
    id="tabpanel-outlook"
    role="tabpanel"
    aria-labelledby="tab-outlook"
    class={activeTab === 'outlook' ? 'block mt-6' : 'hidden'}
    tabindex="0"
  >
    <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
      <h2 class="text-lg font-bold text-wx-900 mb-3">Extended Outlook</h2>
      <p class="text-wx-500 text-sm">
        Extended multi-day outlook content will appear here once the backend supports
        multi-day commentary payloads.
      </p>
      {#if data.dataTrust}
        <div class="mt-6 border-t border-wx-50 pt-4">
          <h3 class="text-sm font-semibold text-wx-900 mb-3">Model Health</h3>
          <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
            {#each Object.entries(data.dataTrust) as [key, value]}
              {#if typeof value === 'string' || typeof value === 'number'}
                <MetricCard
                  label={key.replace(/_/g, ' ')}
                  value={String(value)}
                  loading={false}
                />
              {/if}
            {/each}
          </div>
        </div>
      {/if}
    </section>
  </div>

  <!-- Microclimate Map tab panel -->
  <div
    id="tabpanel-map"
    role="tabpanel"
    aria-labelledby="tab-map"
    class={activeTab === 'map' ? 'block mt-6' : 'hidden'}
    tabindex="0"
  >
    <MicroclimateMap citySlug={data.citySlug} fallbackAois={data.fallbackAois} />
  </div>

{:else}
  <!-- No commentary yet -->
  <div class="text-center py-16">
    <h1 class="text-3xl font-bold text-wx-900 mb-3">
      {data.cityConfig.name}, {data.cityConfig.state}
    </h1>
    <p class="text-wx-600 mb-2">Forecast commentary is being generated. Check back soon!</p>
    <p class="text-sm text-wx-400">
      Tracking {data.cityConfig.elevBandsM.length} elevation band{data.cityConfig.elevBandsM.length !== 1 ? 's' : ''} from
      {metersToFeet(data.cityConfig.elevBandsM[0]).toLocaleString()} ft to
      {metersToFeet(data.cityConfig.elevBandsM[data.cityConfig.elevBandsM.length - 1]).toLocaleString()} ft.
    </p>
    <div class="max-w-2xl mx-auto mt-8 space-y-3 text-left px-4" aria-busy="true">
      <Skeleton height="h-6" width="w-3/4" class="mx-auto" />
      <Skeleton height="h-4" />
      <Skeleton height="h-4" width="w-5/6" />
      <Skeleton height="h-4" width="w-4/5" />
    </div>
  </div>
{/if}
