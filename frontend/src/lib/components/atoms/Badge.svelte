<script lang="ts">
  type Tone = 'default' | 'info' | 'warning';
  interface Props {
    text: string;
    tone?: Tone;
  }

  let { text, tone = 'default' }: Props = $props();

  const toneClasses: Record<Tone, string> = {
    default: 'bg-wx-100 text-wx-800',
    info: 'bg-blue-100 text-blue-800',
    warning: 'bg-yellow-100 text-yellow-800'
  };

  const toneClass = $derived(toneClasses[tone]);
</script>

<span class={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${toneClass}`}>
  {text}
</span>
