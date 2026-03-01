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

<main class="min-h-screen px-4 py-8 md:py-12">
  <div class="max-w-6xl mx-auto">
    <slot />
  </div>
</main>
