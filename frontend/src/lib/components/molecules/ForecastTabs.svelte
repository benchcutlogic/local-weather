<script lang="ts">
  /**
   * ForecastTabs — ARIA-compliant tab bar for the city page.
   * Tabs: Forecast | Outlook | Microclimate Map
   *
   * Keyboard accessible:
   *  - Arrow Left/Right navigate between tabs
   *  - Home/End jump to first/last tab
   *  - Enter/Space activate focused tab (via click handler)
   */

  export type TabId = 'forecast' | 'outlook' | 'map';

  interface Tab {
    id: TabId;
    label: string;
    icon: string;
  }

  let {
    activeTab = 'forecast',
    onTabChange
  }: {
    activeTab?: TabId;
    onTabChange?: (tab: TabId) => void;
  } = $props();

  const tabs: Tab[] = [
    { id: 'forecast', label: 'Forecast', icon: '☁️' },
    { id: 'outlook', label: 'Outlook', icon: '📅' },
    { id: 'map', label: 'Microclimate Map', icon: '🗺️' }
  ];

  let tabRefs: HTMLButtonElement[] = $state([]);

  function selectTab(tab: TabId) {
    onTabChange?.(tab);
  }

  function handleKeydown(event: KeyboardEvent, index: number) {
    let next = index;
    if (event.key === 'ArrowRight') {
      next = (index + 1) % tabs.length;
    } else if (event.key === 'ArrowLeft') {
      next = (index - 1 + tabs.length) % tabs.length;
    } else if (event.key === 'Home') {
      next = 0;
    } else if (event.key === 'End') {
      next = tabs.length - 1;
    } else {
      return;
    }
    event.preventDefault();
    tabRefs[next]?.focus();
    selectTab(tabs[next].id);
  }
</script>

<div class="border-b border-wx-100 bg-white sticky top-0 z-10">
  <div
    class="flex gap-1 px-1 -mb-px"
    role="tablist"
    aria-label="City forecast sections"
  >
    {#each tabs as tab, i}
      <button
        bind:this={tabRefs[i]}
        type="button"
        role="tab"
        id="tab-{tab.id}"
        aria-controls="tabpanel-{tab.id}"
        aria-selected={activeTab === tab.id}
        tabindex={activeTab === tab.id ? 0 : -1}
        class="flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-wx-500 focus-visible:ring-inset rounded-t-md
          {activeTab === tab.id
            ? 'border-wx-600 text-wx-900'
            : 'border-transparent text-wx-500 hover:text-wx-700 hover:border-wx-300'}"
        onclick={() => selectTab(tab.id)}
        onkeydown={(e) => handleKeydown(e, i)}
      >
        <span aria-hidden="true">{tab.icon}</span>
        {tab.label}
      </button>
    {/each}
  </div>
</div>
