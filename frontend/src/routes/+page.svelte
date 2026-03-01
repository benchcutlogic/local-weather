<script lang="ts">
  import { onMount } from 'svelte';
  import CityCard from '$lib/components/molecules/CityCard.svelte';
  import { track } from '$lib/analytics/index';

  let { data } = $props();
  let query = $state('');

  // Location CTA state
  type LocationState = 'idle' | 'loading' | 'success' | 'error';
  let locationState = $state<LocationState>('idle');
  let locationError = $state<string | null>(null);

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

  // Debounced analytics on search
  let searchTimer: ReturnType<typeof setTimeout> | null = null;
  $effect(() => {
    const q = query; // reactive dependency
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      if (q.trim()) {
        track('city_searched', {
          query_length: q.trim().length,
          result_count: filteredCities.length
        });
      }
    }, 600);
  });

  function detectLocation() {
    if (!navigator.geolocation) {
      locationState = 'error';
      locationError = 'Geolocation is not supported by your browser.';
      track('location_detect_error', { error_code: null });
      return;
    }

    locationState = 'loading';
    locationError = null;
    track('location_detect_started', {});

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        track('location_detect_success', {
          lat_approx: Math.round(lat * 100) / 100,
          lon_approx: Math.round(lon * 100) / 100
        });

        let best: (typeof data.cities)[0] | null = null;
        let bestDist = Infinity;
        for (const city of data.cities) {
          const d = Math.hypot(city.lat - lat, city.lon - lon);
          if (d < bestDist) {
            bestDist = d;
            best = city;
          }
        }

        if (best) {
          locationState = 'success';
          setTimeout(() => {
            window.location.href = `/${best!.slug}`;
          }, 700);
        } else {
          locationState = 'error';
          locationError = 'No cities found near your location.';
        }
      },
      (err) => {
        locationState = 'error';
        locationError =
          err.code === 1
            ? 'Location access was denied. Please allow location access and try again.'
            : 'Unable to determine your location. Please try again.';
        track('location_detect_error', { error_code: err.code });
      },
      { timeout: 10_000, maximumAge: 60_000 }
    );
  }
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

<!-- Search + Location CTA -->
<div class="max-w-md mx-auto mb-10 space-y-3">
  <div class="relative">
    <label for="city-search" class="sr-only">Search cities</label>
    <svg
      class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-wx-400"
      fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"
    >
      <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
    <input
      id="city-search"
      bind:value={query}
      type="search"
      placeholder="Search cities..."
      autocomplete="off"
      aria-label="Search cities"
      class="w-full pl-10 pr-4 py-3 rounded-xl border border-wx-200 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-wx-500 focus:border-transparent"
    />
  </div>

  <!-- Location CTA -->
  <button
    type="button"
    onclick={detectLocation}
    disabled={locationState === 'loading' || locationState === 'success'}
    aria-live="polite"
    aria-label="Detect my location to find the nearest city"
    class="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-wx-500
      {locationState === 'error'
        ? 'border-red-300 bg-red-50 text-red-700'
        : locationState === 'success'
          ? 'border-green-300 bg-green-50 text-green-700'
          : 'border-wx-200 bg-white text-wx-700 hover:border-wx-400 hover:text-wx-900'}"
  >
    {#if locationState === 'loading'}
      <svg class="w-4 h-4 animate-spin text-wx-500" fill="none" viewBox="0 0 24 24" aria-hidden="true">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      Detecting your location...
    {:else if locationState === 'success'}
      <svg class="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
      Heading to nearest city...
    {:else if locationState === 'error'}
      <svg class="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      Try again
    {:else}
      <svg class="w-4 h-4 text-wx-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path d="M12 2a7 7 0 0 1 7 7c0 5.25-7 13-7 13S5 14.25 5 9a7 7 0 0 1 7-7z"/><circle cx="12" cy="9" r="2.5"/>
      </svg>
      Detect my location
    {/if}
  </button>

  {#if locationState === 'error' && locationError}
    <p class="text-xs text-red-600 text-center px-2" role="alert">{locationError}</p>
  {/if}
</div>

<!-- City card grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {#each filteredCities as city (city.slug)}
    <CityCard {city} href={`/${city.slug}`} />
  {/each}

  {#if filteredCities.length === 0}
    <div class="col-span-full text-center py-12">
      <p class="text-wx-500">No cities match "<span class="font-medium text-wx-700">{query}</span>".</p>
      <button
        type="button"
        class="mt-2 text-sm text-wx-600 underline hover:text-wx-800"
        onclick={() => (query = '')}
      >
        Clear search
      </button>
    </div>
  {/if}
</div>
