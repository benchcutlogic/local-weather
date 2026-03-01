<script lang="ts">
  import '../app.css';
</script>

<svelte:head>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<!-- Top nav -->
<nav class="bg-wx-950 text-white sticky top-0 z-50 shadow-lg">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-12">
    <a href="/" class="flex items-center gap-2 font-bold text-base tracking-tight hover:opacity-90 transition-opacity">
      <svg class="w-5 h-5 text-wx-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
        <path d="M3 15a4 4 0 0 0 4 4h9a5 5 0 1 0-.9-9.95A7 7 0 1 0 3 15z" />
      </svg>
      HyperlocalWx
    </a>
    <div class="flex items-center gap-4 text-sm">
      <a href="/" class="text-wx-300 hover:text-white transition-colors">Cities</a>
      <a
        href="/#subscribe"
        class="bg-wx-500 hover:bg-wx-400 text-white text-xs font-semibold px-3 py-1.5 rounded-md transition-colors"
      >
        Subscribe
      </a>
    </div>
  </div>
</nav>

<main class="min-h-[calc(100vh-96px)] px-4 py-8 md:py-10">
  <div class="max-w-7xl mx-auto">
    <slot />
  </div>
</main>

<!-- Footer -->
<footer class="bg-wx-950 text-wx-400 text-xs py-6 mt-auto">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
    <div>
      <span class="text-white font-semibold">HyperlocalWx</span>
      <span class="ml-2">Multi-model weather analysis with terrain-aware AI commentary.</span>
    </div>
    <div class="text-wx-500 text-right">
      Data: HRRR, GFS, NAM, ECMWF via NOAA.
      <span class="ml-1">Verification: RTMA + community reports.</span>
    </div>
  </div>
</footer>
