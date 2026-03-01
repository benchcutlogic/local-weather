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
    high: 'bg-green-100 text-green-800 border-green-300',
    moderate: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    low: 'bg-orange-100 text-orange-800 border-orange-300'
  };

  const confidenceShapes: Record<string, string> = {
    high: '●●●',
    moderate: '●●○',
    low: '●○○'
  };

  const modelColors: Record<string, string> = {
    HRRR: 'bg-wx-500',
    GFS: 'bg-emerald-500',
    NAM: 'bg-amber-500',
    ECMWF: 'bg-purple-500'
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
<nav class="text-sm text-wx-500 mb-5" aria-label="Breadcrumb">
  <ol class="flex items-center gap-1">
    <li><a href="/" class="hover:text-wx-700 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-wx-500 rounded">Cities</a></li>
    <li aria-hidden="true" class="mx-1 text-wx-300">&rsaquo;</li>
    <li class="text-wx-900 font-medium" aria-current="page">
      {data.cityConfig.name}, {data.cityConfig.state}
    </li>
  </ol>
</nav>

{#if data.commentary}
  <!-- ===== HERO BANNER ===== -->
  <section class="bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white rounded-2xl p-6 md:p-8 mb-6 shadow-xl ring-1 ring-indigo-800/30">
    <div class="flex items-start gap-4">
      <div class="hidden sm:block shrink-0 mt-1">
        <WeatherIcon condition="cloudy" size="lg" label="Current weather" />
      </div>
      <div class="flex-1 min-w-0">
        <h1 class="text-3xl md:text-4xl font-extrabold leading-tight mb-3 tracking-tight">{data.commentary.headline}</h1>
        <div class="flex flex-wrap items-center gap-2 text-sm">
          <span class="text-wx-300">Updated {timeAgo(data.commentary.updated_at)}</span>
          <span
            class="px-2.5 py-0.5 rounded-full text-xs font-bold border {confidenceColors[data.commentary.confidence.level]}"
            aria-label="Confidence level: {data.commentary.confidence.level}"
          >
            <span aria-hidden="true">{confidenceShapes[data.commentary.confidence.level]}</span>
            {data.commentary.confidence.level.toUpperCase()} confidence
          </span>
          <span class="text-wx-300 text-xs">
            Best model: <span class="text-white font-semibold">{data.commentary.best_model}</span>
          </span>
          {#if data.commentary.tone}
            <span class="px-2 py-0.5 rounded-full text-xs font-medium bg-wx-700/50 text-wx-200 border border-wx-600">
              {data.commentary.tone}
            </span>
          {/if}
        </div>
      </div>
    </div>

    <!-- Alert banner -->
    {#if data.commentary.alerts && data.commentary.alerts.length > 0}
      <div class="mt-4 bg-amber-500/20 border border-amber-400/40 rounded-lg px-4 py-2.5 text-sm text-amber-100" role="alert">
        {#each data.commentary.alerts as alert}
          <p>{alert}</p>
        {/each}
      </div>
    {/if}

    <!-- Confidence explanation -->
    {#if data.commentary.confidence.explanation}
      <p class="mt-3 text-xs text-wx-300 leading-relaxed">{data.commentary.confidence.explanation}</p>
    {/if}
  </section>

  <!-- ===== AT-A-GLANCE CARDS ===== -->
  <div
    class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6"
    aria-label="At-a-glance forecast metrics"
  >
    <MetricCard
      label="Confidence"
      value={quickMetrics?.confidence.toUpperCase() ?? '—'}
      loading={commentaryLoading}
      icon="confidence"
      class="border-l-[4px] border-l-sky-500"
    />
    <MetricCard
      label="Best Model"
      value={quickMetrics?.bestModel ?? '—'}
      loading={commentaryLoading}
      icon="model"
      class="border-l-[4px] border-l-emerald-500"
    />
    <MetricCard
      label="Elevation Bands"
      value={data.cityConfig.elevBandsM.length}
      unit="bands"
      loading={commentaryLoading}
      icon="elevation"
      class="border-l-[4px] border-l-amber-500"
    />
    <MetricCard
      label="Last Updated"
      value={quickMetrics ? timeAgo(quickMetrics.updatedAt) : '—'}
      loading={commentaryLoading}
      icon="clock"
      class="border-l-[4px] border-l-violet-500"
    />
  </div>

  <!-- ===== MODEL DISAGREEMENT BANNER ===== -->
  {#if data.commentary.model_disagreement}
    <div class="mb-6 bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3" role="status">
      <svg class="w-5 h-5 text-amber-500 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
        <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
      </svg>
      <div class="text-sm">
        <p class="font-semibold text-amber-900">
          Model Disagreement: {data.commentary.model_disagreement.level.toUpperCase()}
        </p>
        <p class="text-amber-800 mt-0.5">{data.commentary.model_disagreement.summary}</p>
        <div class="mt-1 flex flex-wrap gap-3 text-xs text-amber-700">
          <span>Biggest spread: {data.commentary.model_disagreement.biggest_spread_metric} ({data.commentary.model_disagreement.biggest_spread_value})</span>
          <span>Trend: {data.commentary.model_disagreement.confidence_trend}</span>
        </div>
      </div>
    </div>
  {/if}

  <!-- ===== TABBED NAVIGATION ===== -->
  <ForecastTabs {activeTab} onTabChange={handleTabChange} />

  <!-- ===== FORECAST TAB ===== -->
  <div
    id="tabpanel-forecast"
    role="tabpanel"
    aria-labelledby="tab-forecast"
    class={activeTab === 'forecast' ? 'block mt-6' : 'hidden'}
    tabindex="0"
  >
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- ===== LEFT COLUMN (2/3) ===== -->
      <div class="lg:col-span-2 space-y-5">
        <!-- Current Conditions -->
        <section class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
          <div class="border-l-4 border-l-wx-500 p-5">
            <h2 class="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2 flex items-center gap-2">
              <svg class="w-4 h-4 text-wx-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="5"/><path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
              Current Conditions
            </h2>
            {#if commentaryLoading}
              <div class="space-y-2" aria-busy="true" aria-label="Loading current conditions">
                <Skeleton height="h-4" /><Skeleton height="h-4" width="w-4/5" /><Skeleton height="h-4" width="w-3/5" />
              </div>
            {:else}
              <p class="text-wx-700 leading-relaxed text-sm">{data.commentary.current_conditions}</p>
            {/if}
          </div>
        </section>

        <!-- Today's Forecast -->
        <section class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
          <div class="border-l-4 border-l-emerald-500 p-5">
            <h2 class="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2 flex items-center gap-2">
              <svg class="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 15a4 4 0 004 4h9a5 5 0 10-.9-9.95A7 7 0 103 15z"/></svg>
              Today's Forecast
            </h2>
            {#if commentaryLoading}
              <div class="space-y-2" aria-busy="true" aria-label="Loading forecast">
                <Skeleton height="h-4" /><Skeleton height="h-4" width="w-5/6" /><Skeleton height="h-4" width="w-2/3" />
              </div>
            {:else}
              <p class="text-wx-700 leading-relaxed text-sm">{data.commentary.todays_forecast}</p>
            {/if}
          </div>
        </section>

        <!-- Model Analysis -->
        <section class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
          <div class="border-l-4 border-l-purple-500 p-5">
            <h2 class="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2 flex items-center gap-2">
              <svg class="w-4 h-4 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
              Model Analysis
            </h2>
            {#if commentaryLoading}
              <div class="space-y-2" aria-busy="true" aria-label="Loading model analysis">
                <Skeleton height="h-4" /><Skeleton height="h-4" width="w-5/6" />
              </div>
            {:else}
              <p class="text-wx-700 leading-relaxed text-sm">{data.commentary.model_analysis}</p>
            {/if}
          </div>
        </section>

        <!-- Horizon Confidence Timeline -->
        {#if data.commentary.horizon_confidence}
          <section class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
            <div class="border-l-4 border-l-cyan-500 p-5">
              <h2 class="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3 flex items-center gap-2">
                <svg class="w-4 h-4 text-cyan-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                Action Windows
              </h2>
              <div class="flex flex-col sm:flex-row gap-3">
                <!-- Now – 6h: green pill -->
                <div class="flex-1 rounded-2xl bg-green-500 text-white p-4 shadow-sm">
                  <div class="flex items-center gap-2 mb-2">
                    <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                    <span class="text-xs font-bold uppercase tracking-wide opacity-90">Now – 6h</span>
                  </div>
                  <p class="text-sm leading-snug">{data.commentary.horizon_confidence.immediate_0_6h}</p>
                </div>
                <!-- 6h – 48h: amber pill -->
                <div class="flex-1 rounded-2xl bg-amber-500 text-white p-4 shadow-sm">
                  <div class="flex items-center gap-2 mb-2">
                    <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
                    <span class="text-xs font-bold uppercase tracking-wide opacity-90">6h – 48h</span>
                  </div>
                  <p class="text-sm leading-snug">{data.commentary.horizon_confidence.short_6_48h}</p>
                </div>
                <!-- 48h+: red pill -->
                <div class="flex-1 rounded-2xl bg-red-500 text-white p-4 shadow-sm">
                  <div class="flex items-center gap-2 mb-2">
                    <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    <span class="text-xs font-bold uppercase tracking-wide opacity-90">48h+</span>
                  </div>
                  <p class="text-sm leading-snug">{data.commentary.horizon_confidence.extended_48h_plus}</p>
                </div>
              </div>
            </div>
          </section>
        {/if}

        <!-- Dayparts -->
        {#if data.commentary.dayparts}
          <section class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
            <div class="border-l-4 border-l-orange-400 p-5">
              <h2 class="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3 flex items-center gap-2">
                <svg class="w-4 h-4 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707"/></svg>
                Day Breakdown
              </h2>
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div class="rounded-lg bg-amber-50 border border-amber-200 p-3">
                  <p class="text-xs font-bold text-amber-800 uppercase tracking-wide mb-1">Morning</p>
                  <p class="text-sm text-amber-900">{data.commentary.dayparts.am}</p>
                </div>
                <div class="rounded-lg bg-orange-50 border border-orange-200 p-3">
                  <p class="text-xs font-bold text-orange-800 uppercase tracking-wide mb-1">Afternoon</p>
                  <p class="text-sm text-orange-900">{data.commentary.dayparts.pm}</p>
                </div>
                <div class="rounded-lg bg-indigo-50 border border-indigo-200 p-3">
                  <p class="text-xs font-bold text-indigo-800 uppercase tracking-wide mb-1">Night</p>
                  <p class="text-sm text-indigo-900">{data.commentary.dayparts.night}</p>
                </div>
              </div>
            </div>
          </section>
        {/if}

        <!-- Elevation Breakdown -->
        <section class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
          <div class="border-l-4 border-l-teal-500 p-5">
            <h2 class="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2 flex items-center gap-2">
              <svg class="w-4 h-4 text-teal-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>
              Elevation Breakdown
            </h2>
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
              <p class="text-wx-700 leading-relaxed text-sm mb-4">{data.commentary.elevation_breakdown.summary}</p>
              <div class="space-y-3">
                {#each data.commentary.elevation_breakdown.bands as band}
                  <div class="flex items-start gap-3 pl-3 border-l-2 border-teal-300 hover:border-teal-500 transition-colors">
                    <span class="font-mono text-xs font-bold text-teal-700 whitespace-nowrap min-w-[80px] bg-teal-50 px-2 py-0.5 rounded">
                      {band.elevation_ft.toLocaleString()} ft
                    </span>
                    <p class="text-sm text-wx-700">{band.description}</p>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        </section>

        <!-- 7-Day Outlook -->
        <section class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
          <div class="border-l-4 border-l-indigo-500 p-5">
            <h2 class="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2 flex items-center gap-2">
              <svg class="w-4 h-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
              7-Day Outlook
            </h2>
            {#if commentaryLoading}
              <div class="space-y-2" aria-busy="true"><Skeleton height="h-4" /><Skeleton height="h-4" width="w-4/5" /></div>
            {:else}
              <p class="text-wx-700 leading-relaxed text-sm">{data.commentary.extended_outlook}</p>
            {/if}
          </div>
        </section>

        <!-- Changes / Playbook -->
        {#if data.commentary.changes && data.commentary.changes.length > 0}
          <section class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
            <div class="border-l-4 border-l-rose-500 p-5">
              <h2 class="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2 flex items-center gap-2">
                <svg class="w-4 h-4 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                What Changed
              </h2>
              <ul class="space-y-1.5">
                {#each data.commentary.changes as change}
                  <li class="flex items-start gap-2 text-sm text-wx-700">
                    <span class="text-rose-400 mt-0.5 shrink-0">&bull;</span>
                    {change}
                  </li>
                {/each}
              </ul>
            </div>
          </section>
        {/if}
      </div>

      <!-- ===== RIGHT SIDEBAR (1/3) ===== -->
      <div class="space-y-5">
        <!-- Data Trust -->
        {#if data.dataTrust}
          <section class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
            <div class="sidebar-header">
              <h2 class="text-xs font-semibold uppercase tracking-wide text-slate-500">Data Trust</h2>
            </div>
            <div class="p-5 space-y-3">
              {#if data.dataTrust.models && data.dataTrust.models.length > 0}
                {#each data.dataTrust.models as model}
                  <div class="text-sm">
                    <div class="flex justify-between items-center mb-1">
                      <span class="font-medium text-wx-800">{model.model_name}</span>
                      <span class="text-xs text-wx-500">{model.usable_rows}/{model.total_rows} rows</span>
                    </div>
                    <div class="w-full bg-wx-100 rounded-full h-2">
                      <div
                        class="h-2 rounded-full transition-all {modelColors[model.model_name] ?? 'bg-wx-400'}"
                        style="width: {model.total_rows > 0 ? Math.round((model.usable_rows / model.total_rows) * 100) : 0}%"
                      ></div>
                    </div>
                  </div>
                {/each}
              {:else}
                <p class="text-sm text-wx-500">
                  {data.dataTrust.status === 'missing'
                    ? 'Cannot reach ingestor — unable data coverage.'
                    : 'Trust metrics loading...'}
                </p>
              {/if}
            </div>
          </section>
        {/if}

        <!-- Model Accuracy -->
        <section class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
          <div class="sidebar-header">
            <h2 class="text-xs font-semibold uppercase tracking-wide text-slate-500">Model Accuracy</h2>
          </div>
          <div class="p-5">
            {#if data.dataTrust?.models && data.dataTrust.models.length > 0}
              <p class="text-xs text-wx-500 mb-3">Row-level verification (total vs. usable)</p>
              <div class="space-y-3">
                {#each data.dataTrust.models as model}
                  <div>
                    <div class="flex justify-between text-xs mb-1">
                      <span class="font-semibold text-wx-800">{model.model_name}</span>
                      <span class="text-wx-500">{model.total_rows > 0 ? Math.round((model.usable_rows / model.total_rows) * 100) : 0}%</span>
                    </div>
                    <div class="w-full bg-wx-100 rounded-full h-2.5">
                      <div
                        class="h-2.5 rounded-full transition-all {modelColors[model.model_name] ?? 'bg-wx-400'}"
                        style="width: {model.total_rows > 0 ? Math.round((model.usable_rows / model.total_rows) * 100) : 0}%"
                      ></div>
                    </div>
                  </div>
                {/each}
              </div>
            {:else}
              <p class="text-sm text-wx-500">No accuracy data available yet.</p>
            {/if}
          </div>
        </section>

        <!-- Model Drift -->
        {#if data.commentary.model_disagreement}
          <section class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
            <div class="sidebar-header flex items-center justify-between">
              <h2 class="text-xs font-semibold uppercase tracking-wide text-slate-500">Model Drift</h2>
              <span class="text-xs font-medium px-2 py-0.5 rounded-full {
                data.commentary.model_disagreement.confidence_trend === 'improving' ? 'bg-green-100 text-green-700' :
                data.commentary.model_disagreement.confidence_trend === 'degrading' ? 'bg-red-100 text-red-700' :
                'bg-wx-100 text-wx-600'
              }">
                {data.commentary.model_disagreement.confidence_trend}
              </span>
            </div>
            <div class="p-5 text-sm text-wx-700 space-y-2">
              <p>Drift chart placeholder</p>
              <p class="text-xs text-wx-500">Intraday model comparison charts will appear here.</p>
            </div>
          </section>
        {/if}

        <!-- Community Reports -->
        <section class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
          <div class="sidebar-header">
            <h2 class="text-xs font-semibold uppercase tracking-wide text-slate-500">Community Reports</h2>
          </div>
          <div class="p-5">
            {#if data.reports.length > 0}
              <div class="space-y-2 mb-4 max-h-48 overflow-y-auto" role="feed" aria-label="Community weather reports">
                {#each data.reports as report}
                  <article class="text-sm border-b border-wx-50 pb-2 last:border-0">
                    <div class="text-wx-500 text-xs">{timeAgo(report.created_at)}</div>
                    {#if report.notes}<p class="text-wx-700 mt-0.5">{report.notes}</p>{/if}
                  </article>
                {/each}
              </div>
            {:else}
              <p class="text-xs text-wx-500 mb-3">No reports yet. Be the first!</p>
            {/if}

            <form
              method="POST"
              action="?/report"
              use:enhance={() => {
                reportSubmitting = true;
                return async ({ update }) => {
                  reportSubmitting = false;
                  track('report_submitted', {
                    city_slug: data.citySlug,
                    has_temp: false,
                    has_snow: false
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
                class="w-full px-3 py-2 text-sm border border-wx-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-wx-400 bg-wx-50"
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
                    class="px-3 py-1.5 text-sm border border-wx-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-wx-400 bg-wx-50"
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
                    class="px-3 py-1.5 text-sm border border-wx-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-wx-400 bg-wx-50"
                    disabled={reportSubmitting}
                  />
                </label>
              </div>
              <button
                type="submit"
                disabled={reportSubmitting}
                class="w-full bg-wx-600 hover:bg-wx-500 disabled:opacity-60 text-white text-sm font-semibold py-2.5 rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-wx-400 shadow-sm"
              >
                {reportSubmitting ? 'Submitting...' : 'Submit Report'}
              </button>
            </form>
          </div>
        </section>

        <!-- Premium Access CTA -->
        <section class="bg-gradient-to-br from-indigo-700 to-indigo-900 text-white rounded-xl shadow-xl overflow-hidden ring-1 ring-indigo-500/20">
          <div class="p-5">
            <div class="flex items-center gap-2 mb-1">
              <svg class="w-4 h-4 text-indigo-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M5 3l14 9-14 9V3z"/></svg>
              <h2 class="text-sm font-bold tracking-wide uppercase text-indigo-100">Premium Access</h2>
            </div>
            <p class="text-xs text-indigo-200 mb-4">Ops-grade forecasting tools for professionals.</p>
            <ul class="space-y-2 text-xs text-indigo-100">
              <li class="flex items-start gap-2">
                <svg class="w-3.5 h-3.5 text-green-400 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                Extended model comparison charts
              </li>
              <li class="flex items-start gap-2">
                <svg class="w-3.5 h-3.5 text-green-400 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                Automated weather alert webhooks
              </li>
              <li class="flex items-start gap-2">
                <svg class="w-3.5 h-3.5 text-green-400 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                Push alerts for significant model drift
              </li>
              <li class="flex items-start gap-2">
                <svg class="w-3.5 h-3.5 text-green-400 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                API access for integrations
              </li>
              <li class="flex items-start gap-2">
                <svg class="w-3.5 h-3.5 text-green-400 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                Priority support & custom AOI alerts
              </li>
            </ul>
            <button
              type="button"
              class="mt-5 w-full bg-white text-indigo-800 font-extrabold text-sm py-3 rounded-lg hover:bg-indigo-50 transition-colors shadow-lg"
            >
              Subscribe &mdash; $5/mo
            </button>
          </div>
        </section>
      </div>
    </div>
  </div>

  <!-- ===== OUTLOOK TAB ===== -->
  <div
    id="tabpanel-outlook"
    role="tabpanel"
    aria-labelledby="tab-outlook"
    class={activeTab === 'outlook' ? 'block mt-6' : 'hidden'}
    tabindex="0"
  >
    <section class="bg-white rounded-xl shadow-md border border-slate-200 p-6">
      <h2 class="text-lg font-bold text-wx-900 mb-3">Extended Outlook</h2>
      <p class="text-wx-700 text-sm leading-relaxed">{data.commentary.extended_outlook}</p>
      {#if data.dataTrust}
        <div class="mt-6 border-t border-wx-100 pt-4">
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

  <!-- ===== MAP TAB ===== -->
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
