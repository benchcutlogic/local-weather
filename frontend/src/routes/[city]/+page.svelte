<script lang="ts">
  import { browser } from '$app/environment';
  import { enhance } from '$app/forms';
  import { page } from '$app/state';
  import { metersToFeet } from '$lib/cities';
  import MicroclimateMap from '$lib/components/organisms/MicroclimateMap.svelte';
  import { trackToneSelected, trackChangesViewed } from '$lib/analytics/cityPage';

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

  function storedTone(): Tone | null {
    if (!browser) return null;
    try {
      const v = window.localStorage.getItem('wx:tone');
      if (v === 'professional' || v === 'friendly' || v === 'spicy') return v;
    } catch { /* ignore */ }
    return null;
  }

  let selectedTone = $derived(
    (page.url.searchParams.get('tone') as Tone) || storedTone() || 'professional'
  );

  $effect(() => {
    if (!browser) return;
    try { window.localStorage.setItem('wx:tone', selectedTone); } catch { /* ignore */ }
    trackToneSelected(data.citySlug, selectedTone);
  });
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

  type RiskLevel = 'Low' | 'Watch' | 'Elevated' | 'High';

  function riskLevel(commentary: (typeof data.commentary) | null): RiskLevel {
    if (!commentary) return 'Low';
    const confidence = commentary.confidence.level;
    const alerts = commentary.alerts?.length || 0;
    if (alerts >= 3 || (alerts >= 2 && confidence === 'low')) return 'High';
    if (alerts >= 2 || confidence === 'low') return 'Elevated';
    if (alerts === 1 || confidence === 'moderate') return 'Watch';
    return 'Low';
  }

  function riskLabel(commentary: (typeof data.commentary) | null): string {
    if (!commentary) return 'No risk signal yet';
    const level = riskLevel(commentary);
    if (level === 'High' || level === 'Elevated') return 'Elevated risk';
    if (level === 'Watch') return 'Watch conditions';
    return 'Low operational risk';
  }

  let currentRisk = $derived(riskLevel(data.commentary));

  function modelDisagreementLabel(): string | null {
    if (!data.dataTrust?.models?.length) return null;
    const coverages = data.dataTrust.models.map(
      (m: { usable_rows: number; total_rows: number }) =>
        m.total_rows > 0 ? m.usable_rows / m.total_rows : 0
    );
    const lowest = Math.min(...coverages);
    if (lowest < 0.60) return 'High model disagreement';
    if (coverages.every((c: number) => c >= 0.80)) return 'Models agree';
    return 'Moderate model spread';
  }

  let disagreementLabel = $derived(modelDisagreementLabel());

  function windowStatus(daypart: 'am' | 'pm' | 'night'): 'stable' | 'watch' | 'critical' {
    if (daypart === 'pm' && (currentRisk === 'Elevated' || currentRisk === 'High')) return 'critical';
    if (currentRisk === 'Watch') return 'watch';
    if (currentRisk === 'Elevated' || currentRisk === 'High') return 'watch';
    return 'stable';
  }

  const statusColors: Record<string, string> = {
    stable: 'bg-green-100 text-green-800',
    watch: 'bg-yellow-100 text-yellow-800',
    critical: 'bg-red-100 text-red-800'
  };

  function playbookItems(audience: 'residents' | 'race_organizers' | 'crews'): string[] {
    const level = currentRisk;
    if (audience === 'residents') {
      if (level === 'High') return ['Stay indoors during peak hours', 'Monitor emergency channels', 'Secure outdoor items'];
      if (level === 'Elevated' || level === 'Watch') return ['Check forecasts before outdoor plans', 'Allow extra travel time'];
      return ['Normal outdoor activities OK', 'Stay hydrated'];
    }
    if (audience === 'race_organizers') {
      if (level === 'High') return ['Consider postponement', 'Brief all staff on safety plan', 'Stage medical resources'];
      if (level === 'Elevated' || level === 'Watch') return ['Review course hazard points', 'Prepare contingency schedule'];
      return ['Routine event prep', 'Confirm aid station staffing'];
    }
    // crews
    if (level === 'High') return ['Suspend non-essential field work', 'Recall crews from exposed areas', 'Check emergency gear'];
    if (level === 'Elevated' || level === 'Watch') return ['Shorten outdoor shifts', 'Monitor conditions hourly'];
    return ['Standard operations', 'Hydration and sun protection'];
  }

  function dayparts(commentary: (typeof data.commentary) | null): { am: string; pm: string; night: string } {
    if (!commentary) {
      return {
        am: 'No morning guidance yet.',
        pm: 'No afternoon guidance yet.',
        night: 'No evening guidance yet.'
      };
    }

    if (commentary.dayparts) {
      return {
        am: commentary.dayparts.am || 'Morning trend is still stabilizing.',
        pm: commentary.dayparts.pm || 'Afternoon model spread is still coming in.',
        night: commentary.dayparts.night || 'Evening trend guidance is limited right now.'
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

  $effect(() => {
    if (!browser || !data.commentary) return;

    // #57: prefer structured changes payload when present
    if (data.commentary.changes && data.commentary.changes.length > 0) {
      changes = data.commentary.changes;
      if (changes.length > 0) trackChangesViewed(data.citySlug, changes.length);
      return;
    }

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
      if (changes.length > 0) trackChangesViewed(data.citySlug, changes.length);
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
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <h2 class="text-base font-bold text-wx-900">Narration style</h2>
      <div class="flex items-center gap-2">
        {#each Object.entries(toneLabels) as [tone, label]}
          <a
            href={`?tone=${tone}`}
            onclick={() => { try { window.localStorage.setItem('wx:tone', tone); } catch { /* ignore */ } }}
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

  {#if disagreementLabel}
    <div class="flex justify-center mb-6">
      <span class="px-3 py-1 rounded-full text-xs font-medium border {
        disagreementLabel === 'Models agree'
          ? 'bg-green-50 text-green-700 border-green-200'
          : disagreementLabel === 'Moderate model spread'
            ? 'bg-yellow-50 text-yellow-700 border-yellow-200'
            : 'bg-red-50 text-red-700 border-red-200'
      }">{disagreementLabel}</span>
    </div>
  {/if}

  {#if data.commentary.alerts && data.commentary.alerts.length > 0}
    <section class="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
      <h2 class="text-sm font-bold text-amber-900 mb-2">Active Alerts</h2>
      <ul class="space-y-1 text-sm text-amber-800">
        {#each data.commentary.alerts as alert}
          <li class="pl-3 border-l-2 border-amber-300">{toneText(alert, selectedTone)}</li>
        {/each}
      </ul>
    </section>
  {/if}

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
        <h2 class="text-lg font-bold text-wx-900 mb-3">Action Windows</h2>
        <div class="space-y-2">
          {#each [{ key: 'am' as const, label: 'AM', time: '6 AM – 12 PM' }, { key: 'pm' as const, label: 'PM', time: '12 PM – 6 PM' }, { key: 'night' as const, label: 'Night', time: '6 PM – 6 AM' }] as window}
            {@const status = windowStatus(window.key)}
            <div class="flex items-center gap-3 py-2 {window.key !== 'night' ? 'border-b border-wx-100' : ''}">
              <span class="font-mono text-xs font-semibold text-wx-500 min-w-[90px]">{window.time}</span>
              <span class="px-2 py-0.5 rounded-full text-xs font-medium {statusColors[status]}">{status === 'critical' ? 'critical window' : status}</span>
              <span class="text-sm text-wx-700 flex-1">{toneText(daypartSummary[window.key], selectedTone)}</span>
            </div>
          {/each}
        </div>
      </section>

      <section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6">
        <h2 class="text-lg font-bold text-wx-900 mb-3">Ops Playbook</h2>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {#each [{ key: 'residents' as const, label: 'Residents' }, { key: 'race_organizers' as const, label: 'Race Organizers' }, { key: 'crews' as const, label: 'Crews' }] as audience}
            <div>
              <h3 class="text-xs uppercase tracking-wide text-wx-500 mb-2">{audience.label}</h3>
              <ul class="space-y-1 text-sm text-wx-700">
                {#each playbookItems(audience.key) as item}
                  <li class="pl-2 border-l-2 border-wx-200">{item}</li>
                {/each}
              </ul>
            </div>
          {/each}
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
