<script lang="ts">
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';
  import type { AoiCard, ZoneSummaryResponse } from '$lib/map/types';

  let {
    citySlug,
    fallbackAois = []
  }: {
    citySlug: string;
    fallbackAois?: AoiCard[];
  } = $props();

  let mapContainer: HTMLDivElement | null = null;
  let mapLoaded = $state(false);
  let mapError = $state<string | null>(null);
  let summary = $state<ZoneSummaryResponse | null>(null);

  const showFallbackCards = $derived(!mapLoaded || !!mapError);

  function createDiagonalPattern(size = 8): ImageData {
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Failed to create pattern context');

    ctx.clearRect(0, 0, size, size);
    ctx.strokeStyle = 'rgba(15, 23, 42, 0.45)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, size);
    ctx.lineTo(size, 0);
    ctx.stroke();

    return ctx.getImageData(0, 0, size, size);
  }

  onMount(() => {
    if (!browser || !mapContainer) return;

    let destroyed = false;
    let cleanup: (() => void) | undefined;

    const observer = new IntersectionObserver(
      async (entries) => {
        const entry = entries[0];
        if (!entry?.isIntersecting || destroyed) return;

        observer.disconnect();

        try {
          const maplibre = await import('maplibre-gl');
          await import('maplibre-gl/dist/maplibre-gl.css');

          if (!mapContainer || destroyed) return;

          const map = new maplibre.Map({
            container: mapContainer,
            style: 'https://demotiles.maplibre.org/style.json',
            center: [-107.88, 37.28],
            zoom: 9.3
          });

          map.addControl(new maplibre.NavigationControl(), 'top-right');

          map.on('load', async () => {
            if (destroyed) return;

            map.addSource('zones', {
              type: 'geojson',
              data: `/maps/${citySlug}-zones.geojson`,
              promoteId: 'zone_id'
            });

            map.addLayer({
              id: 'zone-fills',
              type: 'fill',
              source: 'zones',
              paint: {
                'fill-color': [
                  'interpolate',
                  ['linear'],
                  ['coalesce', ['feature-state', 'temp_delta_f'], 0],
                  -10,
                  '#313695',
                  0,
                  '#ffffbf',
                  10,
                  '#a50026'
                ],
                'fill-opacity': 0.68
              }
            });

            map.addImage('confidence-low-hatch', createDiagonalPattern(), {
              pixelRatio: 2
            });

            map.addLayer({
              id: 'zone-confidence-hatch',
              type: 'fill',
              source: 'zones',
              paint: {
                'fill-pattern': 'confidence-low-hatch',
                'fill-opacity': [
                  'case',
                  ['==', ['feature-state', 'confidence'], 'low'],
                  0.45,
                  0
                ]
              }
            });

            map.addLayer({
              id: 'zone-lines',
              type: 'line',
              source: 'zones',
              paint: {
                'line-color': '#0b3f6e',
                'line-width': 1.2
              }
            });

            const response = await fetch(`/api/map/${citySlug}/summary`);
            const summaryData = (await response.json()) as ZoneSummaryResponse;
            summary = summaryData;

            for (const zone of summaryData.zones) {
              map.setFeatureState(
                { source: 'zones', id: zone.zone_id },
                {
                  temp_delta_f: zone.temp_delta_f,
                  confidence: zone.confidence_level
                }
              );
            }

            mapLoaded = true;
          });

          map.on('error', (event) => {
            if (destroyed) return;
            mapError = event.error?.message || 'Map rendering failed';
          });

          cleanup = () => {
            map.remove();
          };
        } catch (error) {
          mapError = error instanceof Error ? error.message : 'Unable to load map';
        }
      },
      {
        rootMargin: '300px'
      }
    );

    observer.observe(mapContainer);

    return () => {
      destroyed = true;
      observer.disconnect();
      cleanup?.();
    };
  });
</script>

<section class="bg-white rounded-xl shadow-sm border border-wx-100 p-6 space-y-4">
  <div class="flex items-center justify-between gap-3">
    <div>
      <h2 class="text-lg font-bold text-wx-900">Microclimate Zones</h2>
      <p class="text-sm text-wx-600">
        Static zone geometry with dynamic forecast metrics (client-side join).
      </p>
    </div>
    <div class="text-xs text-wx-600 bg-wx-50 border border-wx-100 rounded-full px-3 py-1">
      {mapLoaded ? 'Map loaded' : 'Fallback mode'}
    </div>
  </div>

  <div bind:this={mapContainer} class="h-80 md:h-96 w-full rounded-lg border border-wx-100 overflow-hidden"></div>

  <div class="flex flex-wrap gap-3 text-xs">
    <span class="inline-flex items-center gap-2"><span class="w-3 h-3 rounded bg-[#313695]"></span>Much colder</span>
    <span class="inline-flex items-center gap-2"><span class="w-3 h-3 rounded bg-[#ffffbf] border border-wx-200"></span>Baseline</span>
    <span class="inline-flex items-center gap-2"><span class="w-3 h-3 rounded bg-[#a50026]"></span>Much warmer</span>
    <span class="inline-flex items-center gap-2"><span class="w-3 h-3 rounded bg-wx-100 border border-wx-300" style="background-image: repeating-linear-gradient(135deg, rgba(15,23,42,0.45) 0 1px, transparent 1px 4px);"></span>Low confidence (models disagree)</span>
  </div>

  {#if showFallbackCards}
    <div class="space-y-2">
      <h3 class="text-sm font-semibold text-wx-900">Areas of Interest</h3>
      {#if (summary?.aois?.length ?? 0) > 0}
        {#each summary?.aois ?? [] as aoi}
          <article class="rounded-lg border border-wx-100 p-3 bg-wx-50">
            <p class="font-medium text-wx-900 text-sm">{aoi.aoi_name}</p>
            <p class="text-xs text-wx-600 mt-1">{aoi.note}</p>
          </article>
        {/each}
      {:else if fallbackAois.length > 0}
        {#each fallbackAois as aoi}
          <article class="rounded-lg border border-wx-100 p-3 bg-wx-50">
            <p class="font-medium text-wx-900 text-sm">{aoi.aoi_name}</p>
            <p class="text-xs text-wx-600 mt-1">{aoi.note}</p>
          </article>
        {/each}
      {:else}
        <p class="text-sm text-wx-500">AOI summaries unavailable.</p>
      {/if}
    </div>
  {/if}

  {#if mapError}
    <p class="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">
      Map fallback active: {mapError}
    </p>
  {/if}
</section>
