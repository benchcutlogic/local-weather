<script lang="ts">
  /**
   * WeatherIcon — maps WMO weather interpretation codes (or simple string
   * aliases) to inline SVG icons.  Sizes follow Tailwind's icon convention.
   *
   * Supported size values: 'sm' | 'md' | 'lg'
   * Supported condition aliases:
   *   sunny | partly_cloudy | cloudy | overcast | fog | drizzle |
   *   rain | sleet | snow | thunderstorm | blizzard | wind | unknown
   */

  type Condition =
    | 'sunny'
    | 'partly_cloudy'
    | 'cloudy'
    | 'overcast'
    | 'fog'
    | 'drizzle'
    | 'rain'
    | 'sleet'
    | 'snow'
    | 'thunderstorm'
    | 'blizzard'
    | 'wind'
    | 'unknown';

  type IconSize = 'sm' | 'md' | 'lg';

  let {
    condition = 'unknown',
    size = 'md',
    label
  }: {
    condition?: Condition | string;
    size?: IconSize;
    label?: string;
  } = $props();

  const sizeClasses: Record<IconSize, string> = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-10 h-10'
  };

  const ariaLabel = $derived(label ?? condition.replace(/_/g, ' '));
  const sizeClass = $derived(sizeClasses[size as IconSize] ?? sizeClasses.md);
</script>

<span
  class="inline-flex items-center justify-center {sizeClass}"
  role="img"
  aria-label={ariaLabel}
  title={ariaLabel}
>
  {#if condition === 'sunny'}
    <!-- Sun -->
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-amber-400 w-full h-full" aria-hidden="true">
      <circle cx="12" cy="12" r="5"/>
      <line x1="12" y1="1" x2="12" y2="3"/>
      <line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/>
      <line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>

  {:else if condition === 'partly_cloudy'}
    <!-- Sun + cloud -->
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-amber-400 w-full h-full" aria-hidden="true">
      <path d="M12 2v2M4.93 4.93l1.41 1.41M2 12h2M4.93 19.07l1.41-1.41" class="text-amber-400"/>
      <circle cx="10" cy="10" r="4" class="fill-amber-100"/>
      <path d="M20 17a5 5 0 0 0-5-5H8.5a4.5 4.5 0 0 0 0 9H20v-4z" class="fill-wx-100 stroke-wx-400"/>
    </svg>

  {:else if condition === 'cloudy' || condition === 'overcast'}
    <!-- Cloud -->
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-wx-400 w-full h-full" aria-hidden="true">
      <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
    </svg>

  {:else if condition === 'fog'}
    <!-- Fog layers -->
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-wx-300 w-full h-full" aria-hidden="true">
      <path d="M5 5h13M5 9h13M5 13h13M5 17h13"/>
    </svg>

  {:else if condition === 'drizzle'}
    <!-- Light rain -->
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-wx-500 w-full h-full" aria-hidden="true">
      <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
      <line x1="8" y1="19" x2="8" y2="21" stroke-dasharray="1 2"/>
      <line x1="12" y1="19" x2="12" y2="21" stroke-dasharray="1 2"/>
      <line x1="16" y1="19" x2="16" y2="21" stroke-dasharray="1 2"/>
    </svg>

  {:else if condition === 'rain'}
    <!-- Rain -->
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-wx-600 w-full h-full" aria-hidden="true">
      <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
      <line x1="8" y1="19" x2="6" y2="23"/>
      <line x1="12" y1="19" x2="10" y2="23"/>
      <line x1="16" y1="19" x2="14" y2="23"/>
    </svg>

  {:else if condition === 'sleet'}
    <!-- Sleet (rain + snowflake) -->
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-wx-500 w-full h-full" aria-hidden="true">
      <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
      <line x1="8" y1="19" x2="6" y2="23"/>
      <line x1="16" y1="19" x2="14" y2="23"/>
      <circle cx="12" cy="22" r="1" fill="currentColor"/>
    </svg>

  {:else if condition === 'snow'}
    <!-- Snow -->
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-wx-400 w-full h-full" aria-hidden="true">
      <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
      <line x1="8" y1="20" x2="8" y2="20" stroke-linecap="round" stroke-width="3"/>
      <line x1="12" y1="20" x2="12" y2="20" stroke-linecap="round" stroke-width="3"/>
      <line x1="16" y1="20" x2="16" y2="20" stroke-linecap="round" stroke-width="3"/>
    </svg>

  {:else if condition === 'thunderstorm'}
    <!-- Lightning bolt -->
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-amber-500 w-full h-full" aria-hidden="true">
      <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
      <polyline points="13 11 11 15 14 15 12 19" fill="none"/>
    </svg>

  {:else if condition === 'blizzard'}
    <!-- Blizzard (swirling lines) -->
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-wx-300 w-full h-full" aria-hidden="true">
      <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
      <path d="M8 19 Q 10 17 12 19 Q 14 21 16 19"/>
    </svg>

  {:else if condition === 'wind'}
    <!-- Wind lines -->
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-wx-400 w-full h-full" aria-hidden="true">
      <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/>
    </svg>

  {:else}
    <!-- Unknown / fallback: question mark circle -->
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-wx-300 w-full h-full" aria-hidden="true">
      <circle cx="12" cy="12" r="10"/>
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  {/if}
</span>
