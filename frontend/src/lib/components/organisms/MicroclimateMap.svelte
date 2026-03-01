<script lang="ts">
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';
  import type { AoiCard, ZoneMetric, ZoneSummaryResponse, ZoneMetricKey } from '$lib/map/types';
  import LayerToggleGroup from '$lib/components/molecules/LayerToggleGroup.svelte';
  import MetricSelector from '$lib/components/molecules/MetricSelector.svelte';
  import MapLegendPanel from '$lib/components/organisms/MapLegendPanel.svelte';
  import ZoneDetailCard from '$lib/components/organisms/ZoneDetailCard.svelte';
  import Skeleton from '$lib/components/atoms/Skeleton.svelte';
  import { track } from '$lib/analytics/index';

  let {
    citySlug,
    fallbackAois = []
  }: {
    citySlug: string;
    fallbackAois?: AoiCard[];
  } = $props();

  // ── Map state ────────────────────────────────────────────────────────────────

  let mapContainer: HTMLDivElement | null = null;
  let mapLoaded = $state(false);
  let mapLoading = $state(false);
  let mapError = $state<string | null>(null);
  let summary = $state<ZoneSummaryResponse | null>(null);

  // ── Layer / control state ─────────────────────────────────────────────────────

  let activeMetric = $state<ZoneMetricKey>('temp_delta_f');
  let showAoi = $state(true);
  let showConfidence = $state(true);
  let showHazards = $state(true);
  let controlsExpanded = $state(true);
  let legendExpanded = $state(true);

  // ── Selected zone/AOI state ───────────────────────────────────────────────────

  let selectedZone = $state<ZoneMetric | null>(null);
  let selectedAoi = $state<AoiCard | null>(null);

  const showFallbackCards = $derived(!mapLoaded || !!mapError);

  // MapLibre map reference (kept outside $state to avoid reactivity on the raw object)
  let mapRef: import('maplibre-gl').Map | null = null;
  let loadStartMs = 0;

  // ── Helpers ───────────────────────────────────────────────────────────────────

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

  function getMetricPaintExpression(metric: ZoneMetricKey) {
    const rangeMap: Record<ZoneMetricKey, [number, number]> = {
      temp_delta_f: [-10, 10],
      wind_delta_mph: [-20, 20],
      precip_delta_pct: [-40, 40],
      snow_delta_in: [0, 10]
    };
    const [min, max] = rangeMap[metric];
    return [
      'interpolate', ['linear'],
      ['coalesce', ['feature-state', metric], 0],
      min, '#313695',
      0, '#ffffbf',
      max, '#a50026'
    ];
  }

  /** Apply current metric paint to zone-fills layer. */
  function applyMetricToMap(metric: ZoneMetricKey) {
    if (!mapRef) return;
    try {
      mapRef.setPaintProperty('zone-fills', 'fill-color', getMetricPaintExpression(metric));
    } catch {
      // Layer may not be loaded yet; ignore.
    }
  }

  /** Apply layer visibility flags to map. */
  function applyLayerVisibility() {
    if (!mapRef) return;
    try {
      mapRef.setLayoutProperty('zone-confidence-hatch', 'visibility', showConfidence ? 'visible' : 'none');
      mapRef.setLayoutProperty('aoi-fills', 'visibility', showAoi ? 'visible' : 'none');
      mapRef.setLayoutProperty('aoi-lines', 'visibility', showAoi ? 'visible' : 'none');
    } catch {
      // Layers may not exist for all cities; ignore.
    }
  }

  /** Select a zone by id and (optionally) surface its AOI. */
  function selectZone(zoneId: string) {
    if (!summary) return;
    const zone = summary.zones.find((z) => z.zone_id === zoneId) ?? null;
    const aoi = summary.aois.find((a) => a.zone_id === zoneId) ?? null;

    selectedZone = zone;
    selectedAoi = aoi;

    if (zone) {
      track('zone_selected', { city_slug: citySlug, zone_id: zoneId });
    }
    if (aoi) {
      track('aoi_selected', { city_slug: citySlug, aoi_slug: aoi.aoi_slug, zone_id: zoneId });
    }
  }

  function closeDetail() {
    if (selectedAoi) {
      track('detail_closed', { city_slug: citySlug, detail_type: 'aoi' });
    } else if (selectedZone) {
      track('detail_closed', { city_slug: citySlug, detail_type: 'zone' });
    }
    selectedZone = null;
    selectedAoi = null;
  }

  // ── Reactive effects for live control changes ──────────────────────────────

  $effect(() => {
    if (mapLoaded) applyMetricToMap(activeMetric);
  });

  $effect(() => {
    if (mapLoaded) applyLayerVisibility();
  });

  // ── Mount: lazy-load MapLibre when visible ────────────────────────────────────

  onMount(() => {
    if (!browser || !mapContainer) return;

    let destroyed = false;
    let cleanup: (() => void) | undefined;

    const observer = new IntersectionObserver(
      async (entries) => {
        const entry = entries[0];
        if (!entry?.isIntersecting || destroyed) return;
        observer.disconnect();

        mapLoading = true;
        loadStartMs = Date.now();
        track('microclimate_map_load_start', { city_slug: citySlug });

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

          mapRef = map;

          map.addControl(new maplibre.NavigationControl(), 'top-right');

          map.on('load', async () => {
            if (destroyed) return;

            try {
              // ── Zone source + layers ───────────────────────────────────────
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
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  'fill-color': getMetricPaintExpression(activeMetric) as any,
                  'fill-opacity': 0.68
                }
              });

              map.addImage('confidence-low-hatch', createDiagonalPattern(), { pixelRatio: 2 });

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
                paint: { 'line-color': '#0b3f6e', 'line-width': 1.2 }
              });

              // ── Hover highlight ──────────────────────────────────────────
              map.addLayer({
                id: 'zone-highlight',
                type: 'line',
                source: 'zones',
                paint: {
                  'line-color': '#ffffff',
                  'line-width': ['case', ['boolean', ['feature-state', 'hover'], false], 2.5, 0]
                }
              });

              let hoveredZoneId: string | null = null;
              map.on('mousemove', 'zone-fills', (e) => {
                if (!e.features?.length) return;
                if (hoveredZoneId) {
                  map.setFeatureState({ source: 'zones', id: hoveredZoneId }, { hover: false });
                }
                hoveredZoneId = String(e.features[0].id);
                map.setFeatureState({ source: 'zones', id: hoveredZoneId }, { hover: true });
                map.getCanvas().style.cursor = 'pointer';
              });
              map.on('mouseleave', 'zone-fills', () => {
                if (hoveredZoneId) {
                  map.setFeatureState({ source: 'zones', id: hoveredZoneId }, { hover: false });
                }
                hoveredZoneId = null;
                map.getCanvas().style.cursor = '';
              });

              // ── Click: select zone ────────────────────────────────────────
              map.on('click', 'zone-fills', (e) => {
                const id = e.features?.[0]?.id;
                if (id != null) selectZone(String(id));
              });

              // ── AOI source + layers (placeholder) ──────────────────────────
              // AOI geometry is fetched from the summary; in a future iteration
              // these will be real GeoJSON polygons. For now we add an empty source.
              map.addSource('aois', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
              map.addLayer({
                id: 'aoi-fills',
                type: 'fill',
                source: 'aois',
                paint: { 'fill-color': '#fbbf24', 'fill-opacity': 0.15 }
              });
              map.addLayer({
                id: 'aoi-lines',
                type: 'line',
                source: 'aois',
                paint: { 'line-color': '#d97706', 'line-width': 1.5, 'line-dasharray': [2, 2] }
              });

              // ── Fetch zone summary ─────────────────────────────────────────
              const response = await fetch(`/api/map/${citySlug}/summary`);
              if (!response.ok) throw new Error(`Zone summary ${response.status}`);
              const summaryData = (await response.json()) as ZoneSummaryResponse;
              summary = summaryData;

              for (const zone of summaryData.zones) {
                map.setFeatureState(
                  { source: 'zones', id: zone.zone_id },
                  {
                    temp_delta_f: zone.temp_delta_f,
                    wind_delta_mph: zone.wind_delta_mph,
                    precip_delta_pct: zone.precip_delta_pct,
                    snow_delta_in: zone.snow_delta_in,
                    confidence: zone.confidence_level
                  }
                );
              }

              mapLoaded = true;
              mapLoading = false;

              track('microclimate_map_load_success', {
                city_slug: citySlug,
                zone_count: summaryData.zones.length,
                aoi_count: summaryData.aois.length,
                load_ms: Date.now() - loadStartMs
              });
            } catch (err) {
              if (!destroyed) {
                mapError = err instanceof Error ? err.message : 'Failed to load zone data';
                mapLoading = false;
                track('microclimate_map_load_error', {
                  city_slug: citySlug,
                  error_message: mapError
                });
                track('microclimate_map_fallback_visible', {
                  city_slug: citySlug,
                  reason: mapError
                });
              }
            }
          });

          map.on('error', (event) => {
            if (destroyed) return;
            mapError = event.error?.message ?? 'Map rendering failed';
            mapLoading = false;
          });

          cleanup = () => map.remove();
        } catch (error) {
          mapError = error instanceof Error ? error.message : 'Unable to load map';
          mapLoading = false;
          track('microclimate_map_load_error', {
            city_slug: citySlug,
            error_message: mapError
          });
          track('microclimate_map_fallback_visible', {
            city_slug: citySlug,
            reason: mapError
          });
        }
      },
      { rootMargin: '300px' }
    );

    if (mapContainer) observer.observe(mapContainer);

    return () => {
      destroyed = true;
      observer.disconnect();
      cleanup?.();
      mapRef = null;
    };
  });

  // ── Control handlers ──────────────────────────────────────────────────────────

  function handleMetricChange(metric: ZoneMetricKey) {
    activeMetric = metric;
    track('microclimate_metric_changed', { city_slug: citySlug, metric });
  }

  function handleLayerToggle(layer: 'aoi' | 'confidence' | 'hazards', enabled: boolean) {
    if (layer === 'aoi') showAoi = enabled;
    else if (layer === 'confidence') showConfidence = enabled;
    else showHazards = enabled;
    track('microclimate_layer_toggled', { city_slug: citySlug, layer, enabled });
  }
</script>

<section
  class="bg-white rounded-xl shadow-sm border border-wx-100 p-4 md:p-6 space-y-4"
  aria-label="Microclimate zone map for {citySlug}"
>
  <!-- Header row -->
  <div class="flex items-center justify-between gap-3 flex-wrap">
    <div>
      <h2 class="text-lg font-bold text-wx-900">Microclimate Zones</h2>
      <p class="text-sm text-wx-600">Terrain-aware zone map with dynamic forecast metrics.</p>
    </div>
    <span
      class="text-xs px-3 py-1 rounded-full border {mapLoaded ? 'bg-green-50 text-green-700 border-green-200' : 'bg-wx-50 text-wx-600 border-wx-100'}"
      aria-live="polite"
    >
      {mapLoaded ? '✓ Live' : mapLoading ? 'Loading…' : 'Fallback mode'}
    </span>
  </div>

  <!-- Floating control panel -->
  <div class="rounded-lg border border-wx-100 bg-wx-50 p-3 space-y-3">
    <!-- Controls header with expand toggle -->
    <div class="flex items-center justify-between">
      <span class="text-xs font-semibold text-wx-700 uppercase tracking-wide">Map Controls</span>
      <button
        type="button"
        onclick={() => (controlsExpanded = !controlsExpanded)}
        class="text-xs text-wx-500 hover:text-wx-700 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-wx-500 rounded px-1"
        aria-expanded={controlsExpanded}
        aria-controls="map-controls-body"
      >
        {controlsExpanded ? 'Collapse ▲' : 'Expand ▼'}
      </button>
    </div>

    {#if controlsExpanded}
      <div id="map-controls-body" class="space-y-3">
        <!-- Metric selector -->
        <div>
          <p class="text-xs text-wx-500 mb-1.5 font-medium">Active metric</p>
          <MetricSelector
            selected={activeMetric}
            onSelect={handleMetricChange}
          />
        </div>

        <!-- Layer toggles -->
        <div>
          <p class="text-xs text-wx-500 mb-1.5 font-medium">Layers</p>
          <LayerToggleGroup
            {showAoi}
            {showConfidence}
            {showHazards}
            onToggle={handleLayerToggle}
          />
        </div>
      </div>
    {/if}
  </div>

  <!-- Map canvas -->
  <div class="relative">
    <div
      bind:this={mapContainer}
      class="h-72 sm:h-80 md:h-96 w-full rounded-lg border border-wx-100 overflow-hidden"
      aria-label="Interactive microclimate zone map"
      role="application"
    ></div>

    <!-- Loading skeleton overlay -->
    {#if mapLoading && !mapLoaded}
      <div
        class="absolute inset-0 rounded-lg bg-wx-50 flex items-center justify-center"
        aria-busy="true"
        aria-label="Loading map"
      >
        <div class="text-center space-y-3 p-6 w-full max-w-xs">
          <Skeleton height="h-4" width="w-3/4" class="mx-auto" />
          <Skeleton height="h-3" width="w-1/2" class="mx-auto" />
        </div>
      </div>
    {/if}

    <!-- Zone/AOI detail popover — overlaid bottom-left on desktop, inline below on mobile -->
    {#if selectedZone}
      <div class="absolute bottom-3 left-3 right-3 md:right-auto md:max-w-xs z-10">
        <ZoneDetailCard
          zone={selectedZone}
          aoi={selectedAoi}
          {activeMetric}
          onClose={closeDetail}
        />
      </div>
    {/if}
  </div>

  <!-- Legend -->
  <div>
    <div class="flex items-center justify-between mb-1.5">
      <span class="text-xs font-semibold text-wx-700 uppercase tracking-wide">Legend</span>
      <button
        type="button"
        onclick={() => (legendExpanded = !legendExpanded)}
        class="text-xs text-wx-500 hover:text-wx-700 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-wx-500 rounded px-1"
        aria-expanded={legendExpanded}
        aria-controls="map-legend-body"
      >
        {legendExpanded ? 'Hide ▲' : 'Show ▼'}
      </button>
    </div>
    {#if legendExpanded}
      <div id="map-legend-body">
        <MapLegendPanel metric={activeMetric} />
      </div>
    {/if}
  </div>

  <!-- Fallback AOI cards (shown when map fails or is loading) -->
  {#if showFallbackCards}
    <div class="space-y-2" aria-label="Areas of interest">
      <h3 class="text-sm font-semibold text-wx-900">Areas of Interest</h3>
      {#if (summary?.aois?.length ?? 0) > 0}
        {#each summary!.aois as aoi}
          <button
            type="button"
            class="w-full text-left rounded-lg border border-wx-100 p-3 bg-wx-50 hover:border-wx-300 hover:bg-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-wx-500"
            onclick={() => {
              selectedZone = summary?.zones.find((z) => z.zone_id === aoi.zone_id) ?? null;
              selectedAoi = aoi;
              track('aoi_selected', { city_slug: citySlug, aoi_slug: aoi.aoi_slug, zone_id: aoi.zone_id });
            }}
            aria-label="View details for {aoi.aoi_name}"
          >
            <p class="font-medium text-wx-900 text-sm">{aoi.aoi_name}</p>
            <p class="text-xs text-wx-600 mt-1">{aoi.note}</p>
          </button>
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

    <!-- Inline zone/AOI detail when above a selected fallback card -->
    {#if selectedZone && showFallbackCards}
      <div class="mt-2">
        <ZoneDetailCard
          zone={selectedZone}
          aoi={selectedAoi}
          {activeMetric}
          onClose={closeDetail}
        />
      </div>
    {/if}
  {/if}

  <!-- Map error notice -->
  {#if mapError}
    <p class="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3" role="alert">
      Map fallback active: {mapError}
    </p>
  {/if}
</section>
