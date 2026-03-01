<script lang="ts">
  import Skeleton from '$lib/components/atoms/Skeleton.svelte';
</script>

<!--
  CityPageSkeleton — shown while city page data is loading.
  Mirrors the structure of the actual city page layout so there
  is no visual jump when data arrives.
-->
<div class="space-y-6" aria-busy="true" aria-label="Loading city forecast…">
  <!-- Hero card -->
  <Skeleton class="h-28 w-full" rounded="rounded-xl" />

  <!-- Metric cards row -->
  <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
    {#each { length: 4 } as _}
      <Skeleton class="h-24" rounded="rounded-xl" />
    {/each}
  </div>

  <!-- Tab bar -->
  <Skeleton class="h-10 w-72" rounded="rounded" />

  <!-- Content area -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div class="lg:col-span-2 space-y-4">
      <Skeleton class="h-32" rounded="rounded-xl" />
      <Skeleton class="h-40" rounded="rounded-xl" />
    </div>
    <div>
      <Skeleton class="h-72" rounded="rounded-xl" />
    </div>
  </div>
</div>
