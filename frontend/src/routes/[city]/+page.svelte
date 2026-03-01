<script lang="ts">
  import { browser } from '$app/environment';
  import { enhance } from '$app/forms';
  import { page } from '$app/state';
  import { metersToFeet } from '$lib/cities';
  import MicroclimateMap from '$lib/components/organisms/MicroclimateMap.svelte';

  type Tone = 'professional' | 'friendly' | 'spicy';

  let { data } = $props();

  const confidenceColors: Record<string, string> = {
    high: 'bg-green-100 text-green-800 border-green-200',
    moderate: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    low: 'bg-red-100 text-red-800 border-red-200'
  };

  const toneLabels: Record<Tone, string> = {
    professional: 'Professional',
    friendly: 'Friendly',
    spicy: 'Spicy'
  };

  let selectedTone = $derived((page.url.searchParams.get('tone') as Tone) || 'professional');
  let daypartSummary = $derived(dayparts(data.commentary));
  let changes: string[] = $state([]);

  function timeAgo(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  }

  function firstSentence(text: string, fallback = 'No update yet.'): string {
    const trimmed = (text || '').trim();
    if (!trimmed) return fallback;
    const parts = trimmed.split(/(?<=[.!?])\s+/);
    return parts[0] || fallback;
  }

  function toneText(text: string, tone: Tone): string {
    if (!text) return text;

    if (tone === 'professional') return text;

    if (tone === 'friendly') {
      return text
        .replace(/\bprecipitation\b/gi, 'precip')
        .replace(/\bapproximately\b/gi, 'about')
        .replace(/\bconditions\b/gi, 'weather');
    }

    return text
      .replace(/\bmoderate confidence\b/gi, 'confidence is a bit shaky')
      .replace(/\blow confidence\b/gi, 'confidence is sketchy')
      .replace(/\bhigh confidence\b/gi, 'confidence is solid')
      .replace(/\bmodel disagreement\b/gi, 'models are arguing')
      .replace(/\belevated\b/gi, 'spicy');
  }

  function riskLabel(commentary: (typeof data.commentary) | null): string {
    if (!commentary) return 'No risk signal yet';
    const confidence = commentary.confidence.level;
    const alerts = commentary.alerts?.length || 0;

    if (alerts >= 2 || confidence === 'low') return 'Elevated risk';
    if (alerts === 1 || confidence === 'moderate') return 'Watch conditions';
    return 'Low operational risk';
  }

  function dayparts(commentary: (typeof data.commentary) | null): { am: string; pm: string; night: string } {
    if (!commentary) {
      return {
        am: 'No morning guidance yet.',
        pm: 'No afternoon guidance yet.',
        night: 'No evening guidance yet.'
      };
    }

    const today = commentary.todays_forecast || '';
    const extended = commentary.extended_outlook || '';
    const model = commentary.model_analysis || '';

    return {
      am: firstSentence(today, 'Morning trend is still stabilizing.'),
      pm: firstSentence(model, 'Afternoon model spread is still coming in.'),
      night: firstSentence(extended, 'Evening trend guidance is limited right now.')
    };
  }

  type ThresholdStatus = 'triggered' | 'near' | 'clear';

  function thresholdStatus(key: string, text: string): ThresholdStatus {
    const has = (patterns: RegExp[]) => patterns.some((pattern) => pattern.test(text));

    if (key === 'snowIn24hIn') {
      if (has([/winter storm/i, /heavy snow/i, /blizzard/i])) return 'triggered';
      if (has([/snow/i])) return 'near';
      return 'clear';
    }

    if (key === 'windGustMph') {
      if (has([/high wind/i, /wind advisory/i, /gusts?\s*(to|over)?\s*\d+/i])) return 'triggered';
      if (has([/wind/i])) return 'near';
      return 'clear';
    }

    if (key === 'rainIn1hIn') {
      if (has([/flash flood/i, /flood/i, /monsoon/i, /heavy rain/i])) return 'triggered';
      if (has([/rain/i, /storm/i])) return 'near';
      return 'clear';
    }

    if (key === 'heatIndexF') {
      if (has([/excessive heat/i, /dangerous heat/i])) return 'triggered';
      if (has([/hot/i, /heat/i])) return 'near';
      return 'clear';
    }

    if (key === 'freezingLevelFt') {
      if (has([/freezing level/i, /rain\s*to\s*snow/i, /flash freeze/i])) return 'triggered';
      if (has([/freezing/i, /snow line/i])) return 'near';
      return 'clear';
    }

    return 'clear';
  }

  const thresholdRows = $derived.by(() => {
    const thresholds = data.cityConfig.alertThresholds;
    if (!thresholds || !data.commentary) return [] as { key: string; label: string; value: string; status: ThresholdStatus }[];

    const text = [
      data.commentary.headline,
      data.commentary.current_conditions,
      data.commentary.todays_forecast,
      data.commentary.model_analysis,
      data.commentary.extended_outlook,
      ...(data.commentary.alerts || [])
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();

    const pretty: Record<string, string> = {
      snowIn24hIn: 'Snow (24h)',
      windGustMph: 'Wind gust',
      rainIn1hIn: 'Rain (1h)',
      heatIndexF: 'Heat index',
      freezingLevelFt: 'Freezing level'
    };

    const units: Record<string, string> = {
      snowIn24hIn: 'in',
      windGustMph: 'mph',
      rainIn1hIn: 'in',
      heatIndexF: '°F',
      freezingLevelFt: 'ft'
    };

    return Object.entries(thresholds).map(([key, raw]) => ({
      key,
      label: pretty[key] || key,
      value: `${raw} ${units[key] || ''}`.trim(),
      status: thresholdStatus(key, text)
    }));
  });

  const riskSummary = $derived.by(() => {
    if (!data.commentary) {
      return { level: 'Watch', score: 1, drivers: ['Forecast generation in progress'] };
    }

    let score = 0;
    const drivers: string[] = [];

    if (data.commentary.confidence.level === 'low') {
      score += 2;
      drivers.push('Low confidence forecast');
    } else if (data.commentary.confidence.level === 'moderate') {
      score += 1;
      drivers.push('Moderate confidence forecast');
    }

    const alertCount = data.commentary.alerts?.length || 0;
    if (alertCount > 0) {
      score += Math.min(2, alertCount);
      drivers.push(`${alertCount} active alert${alertCount > 1 ? 's' : ''}`);
    }

    const triggered = thresholdRows.filter((row) => row.status === 'triggered').length;
    const near = thresholdRows.filter((row) => row.status === 'near').length;
    if (triggered > 0) {
      score += 2;
      drivers.push(`${triggered} threshold${triggered > 1 ? 's' : ''} triggered`);
    } else if (near > 0) {
      score += 1;
      drivers.push(`${near} threshold${near > 1 ? 's' : ''} near trigger`);
    }

    if (data.commentaryResult?.state === 'stale') {
      score += 1;
      drivers.push('Forecast feed is stale');
    }

    if (data.dataTrust?.models?.length) {
      const weakCoverage = data.dataTrust.models.some(
        (model) => model.total_rows > 0 && model.usable_rows / model.total_rows < 0.75
      );
      if (weakCoverage) {
        score += 1;
        drivers.push('Low usable model coverage');
      }
    }

    const level = score >= 5 ? 'High' : score >= 3 ? 'Elevated' : score >= 1 ? 'Watch' : 'Low';
    return { level, score, drivers: drivers.slice(0, 3) };
  });

  const riskStyles: Record<string, string> = {
    Low: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    Watch: 'bg-amber-50 text-amber-700 border-amber-200',
    Elevated: 'bg-orange-50 text-orange-700 border-orange-200',
    High: 'bg-red-50 text-red-700 border-red-200'
  };

  $effect(() => {
    if (!browser || !data.commentary) return;

    const key = `wx:last:${data.citySlug}`;
    const current = {
      updated_at: data.commentary.updated_at,
      confidence: data.commentary.confidence.level,
      best_model: data.commentary.best_model,
      alerts_count: data.commentary.alerts?.length || 0,
      headline: data.commentary.headline
    };

    try {
      const priorRaw = window.localStorage.getItem(key);
      const prior = priorRaw ? JSON.parse(priorRaw) : null;

      const nextChanges: string[] = [];
      if (prior) {
        if (prior.best_model !== current.best_model) {
          nextChanges.push(`Best model changed: ${prior.best_model} → ${current.best_model}`);
        }
        if (prior.confidence !== current.confidence) {
          nextChanges.push(
            `Confidence moved: ${String(prior.confidence).toUpperCase()} → ${String(current.confidence).toUpperCase()}`
          );
        }
        if (prior.alerts_count !== current.alerts_count) {
          nextChanges.push(`Alert count changed: ${prior.alerts_count} → ${current.alerts_count}`);
        }
        if (prior.headline !== current.headline) {
          nextChanges.push('Forecast headline changed since the previous update');
        }
      }

      changes = nextChanges;
      window.localStorage.setItem(key, JSON.stringify(current));
    } catch {
      changes = [];
    }
  });
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
      <span class="text-wx-300"
        >Best model: <span class="text-white font-medium">{data.commentary.best_model}</span></span
      >
    </div>
  </div>

  <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-4 mb-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h2 class="text-base font-bold text-wx-900 mb-1">Risk Summary</h2>
        <p class="text-sm text-wx-600">Operational risk synthesized from confidence, alerts, thresholds, and feed health.</p>
      </div>
      <span class={`px-3 py-1 rounded-full text-xs font-semibold border ${riskStyles[riskSummary.level]}`}>
        {riskSummary.level} risk
      </span>
    </div>

    {#if riskSummary.drivers.length > 0}
      <ul class="mt-3 grid gap-2 md:grid-cols-3">
        {#each riskSummary.drivers as driver}
          <li class="text-sm text-wx-700 bg-wx-50 border border-wx-100 rounded-md px-3 py-2">{driver}</li>
        {/each}
      </ul>
    {/if}
  </section>

  <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-4 mb-6">
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <h2 class="text-base font-bold text-wx-900">Narration style</h2>
      <div class="flex items-center gap-2">
        {#each Object.entries(toneLabels) as [tone, label]}
          <a
            href={`?tone=${tone}`}
            class={`px-3 py-1.5 rounded-full text-sm border transition ${
              selectedTone === tone
                ? 'bg-wx-700 text-white border-wx-700'
                : 'bg-white text-wx-700 border-wx-200 hover:border-wx-400'
            }`}
          >
            {label}
          </a>
        {/each}
      </div>
    </div>
  </section>

  <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
    <article class="bg-white rounded-xl border border-wx-100 p-4">
      <h3 class="text-xs uppercase tracking-wide text-wx-500 mb-1">Now</h3>
      <p class="text-sm text-wx-800">{toneText(firstSentence(data.commentary.current_conditions), selectedTone)}</p>
    </article>
    <article class="bg-white rounded-xl border border-wx-100 p-4">
      <h3 class="text-xs uppercase tracking-wide text-wx-500 mb-1">Next 6h</h3>
      <p class="text-sm text-wx-800">{toneText(firstSentence(data.commentary.todays_forecast), selectedTone)}</p>
    </article>
    <article class="bg-white rounded-xl border border-wx-100 p-4">
      <h3 class="text-xs uppercase tracking-wide text-wx-500 mb-1">Tomorrow Risk</h3>
      <p class="text-sm font-semibold text-wx-900">{riskLabel(data.commentary)}</p>
      <p class="text-xs text-wx-600 mt-1">Based on confidence + active alerts</p>
    </article>
    <article class="bg-white rounded-xl border border-wx-100 p-4">
      <h3 class="text-xs uppercase tracking-wide text-wx-500 mb-1">Confidence</h3>
      <p class="text-sm text-wx-800">{toneText(data.commentary.confidence.explanation, selectedTone)}</p>
    </article>
  </section>

  <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6 mb-6">
    <h2 class="text-lg font-bold text-wx-900 mb-3">What changed since last update?</h2>
    {#if changes.length === 0}
      <p class="text-sm text-wx-600">No major shifts detected since your last visit for this city.</p>
    {:else}
      <ul class="space-y-2 text-sm text-wx-700">
        {#each changes as change}
          <li class="pl-3 border-l-2 border-wx-200">{change}</li>
        {/each}
      </ul>
    {/if}
  </section>

  <div class="mb-6">
    <MicroclimateMap citySlug={data.citySlug} fallbackAois={data.fallbackAois} />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div class="lg:col-span-2 space-y-6">
      <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
        <h2 class="text-lg font-bold text-wx-900 mb-3">Current Conditions</h2>
        <p class="text-wx-700 leading-relaxed">{toneText(data.commentary.current_conditions, selectedTone)}</p>
      </section>

      <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
        <h2 class="text-lg font-bold text-wx-900 mb-3">Daypart Narrative</h2>
        <div class="space-y-3 text-sm text-wx-700">
          <p><span class="font-semibold text-wx-900">AM:</span> {toneText(daypartSummary.am, selectedTone)}</p>
          <p><span class="font-semibold text-wx-900">PM:</span> {toneText(daypartSummary.pm, selectedTone)}</p>
          <p><span class="font-semibold text-wx-900">Night:</span> {toneText(daypartSummary.night, selectedTone)}</p>
        </div>
      </section>

      <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
        <h2 class="text-lg font-bold text-wx-900 mb-3">Today's Forecast</h2>
        <p class="text-wx-700 leading-relaxed">{toneText(data.commentary.todays_forecast, selectedTone)}</p>
      </section>

      <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
        <h2 class="text-lg font-bold text-wx-900 mb-3">Elevation Breakdown</h2>
        <p class="text-wx-700 leading-relaxed mb-4">{toneText(data.commentary.elevation_breakdown.summary, selectedTone)}</p>
        <div class="space-y-3">
          {#each data.commentary.elevation_breakdown.bands as band}
            <div class="flex items-start gap-3 pl-3 border-l-2 border-wx-200">
              <span class="font-mono text-sm font-semibold text-wx-600 whitespace-nowrap min-w-[80px]">
                {band.elevation_ft.toLocaleString()} ft
              </span>
              <p class="text-sm text-wx-700">{toneText(band.description, selectedTone)}</p>
            </div>
          {/each}
        </div>
      </section>
    </div>

    <div class="space-y-6">
      <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
        <h2 class="text-lg font-bold text-wx-900 mb-3">Alert Thresholds</h2>
        {#if thresholdRows.length === 0}
          <p class="text-sm text-wx-600">No city thresholds configured yet.</p>
        {:else}
          <ul class="space-y-2">
            {#each thresholdRows as row}
              <li class="flex items-center justify-between gap-2 rounded-md border border-wx-100 px-3 py-2">
                <div>
                  <p class="text-sm font-medium text-wx-900">{row.label}</p>
                  <p class="text-xs text-wx-500">Trigger: {row.value}</p>
                </div>
                <span
                  class={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                    row.status === 'triggered'
                      ? 'bg-red-100 text-red-700'
                      : row.status === 'near'
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-emerald-100 text-emerald-700'
                  }`}
                >
                  {row.status === 'triggered' ? 'Triggered' : row.status === 'near' ? 'Near' : 'Clear'}
                </span>
              </li>
            {/each}
          </ul>
        {/if}
      </section>

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
