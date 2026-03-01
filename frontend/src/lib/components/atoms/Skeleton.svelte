<script lang="ts">
  /**
   * Skeleton — animated loading placeholder.
   * Uses CSS-only pulse animation, no JS required.
   * Accessible: the parent section should carry aria-busy="true" while loading.
   */

  let {
    class: cls = '',
    height = 'h-4',
    width = 'w-full',
    rounded = 'rounded-md'
  }: {
    class?: string;
    height?: string;
    width?: string;
    rounded?: string;
  } = $props();
</script>

<div
  class="animate-pulse bg-wx-100 {height} {width} {rounded} {cls}"
  aria-hidden="true"
></div>
