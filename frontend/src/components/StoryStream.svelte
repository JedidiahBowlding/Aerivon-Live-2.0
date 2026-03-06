<script lang="ts">
  import type { StreamMessage } from '$lib/agentStore';

  export let messages: StreamMessage[] = [];
  export let latestStoryText = '';

  function formatStory(text: string): string[] {
    const stripped = (text || '')
      .replace(/^\[[^\]]+\]\s*/i, '')
      .replace(/^create a compelling response for:\s*/i, '')
      .trim();

    if (!stripped) {
      return [];
    }

    const normalized = stripped
      .replace(/\bcontext:\s*/gi, '\n\n')
      .replace(/\s{2,}/g, ' ')
      .replace(/\n{3,}/g, '\n\n')
      .trim();

    return normalized
      .split(/\n\n+/)
      .map((p) => p.trim())
      .filter(Boolean);
  }

  $: storyParagraphs = formatStory(latestStoryText);

  function shouldHideFromRawLog(msg: StreamMessage): boolean {
    if (msg.type !== 'text') {
      return false;
    }
    const text = msg.text.trim().toLowerCase();
    if (!text) {
      return true;
    }
    if (text.startsWith('navigator:') || text.startsWith('interrupt ack:')) {
      return false;
    }
    // Narrative text is shown in the dedicated Latest Story card.
    return true;
  }

  $: visibleMessages = messages.filter((msg) => !shouldHideFromRawLog(msg));
  $: latestAudioMessage = [...messages].reverse().find((msg) => msg.type === 'audio') as
    | Extract<StreamMessage, { type: 'audio' }>
    | undefined;
  $: audioReceivedAt = latestAudioMessage ? new Date(latestAudioMessage.ts).toLocaleTimeString() : null;
  $: isPcmAudio =
    !!latestAudioMessage &&
    (
      (typeof latestAudioMessage.mime_type === 'string' && latestAudioMessage.mime_type.toLowerCase().includes('audio/l16')) ||
      latestAudioMessage.url.toLowerCase().startsWith('data:audio/l16')
    );
</script>

<section class="glass-panel p-4 md:p-5">
  <div class="mb-4 flex items-center justify-between">
    <h2 class="panel-title text-sm uppercase tracking-[0.18em] text-cyan-200">Agent Output Stream</h2>
    <span class="text-xs text-cyan-100/70">Multimodal</span>
  </div>

  {#if storyParagraphs.length > 0}
    <article class="mb-4 rounded-xl border border-cyan-300/30 bg-gradient-to-br from-cyan-400/10 to-slate-950/40 p-4">
      <div class="mb-2 text-[11px] uppercase tracking-[0.14em] text-cyan-200/85">Latest Story</div>
      <div class="space-y-3 text-sm leading-relaxed text-cyan-50">
        {#each storyParagraphs as paragraph}
          <p>{paragraph}</p>
        {/each}
      </div>
    </article>
  {/if}

  {#if latestAudioMessage}
    <div class="mb-4 rounded-lg border border-emerald-300/35 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-200">
      <span class="font-semibold">Audio received</span>
      <span class="text-emerald-100/80"> at {audioReceivedAt}</span>
      {#if isPcmAudio}
        <span class="ml-2 rounded border border-emerald-300/30 px-1.5 py-0.5 text-[10px] uppercase tracking-wide">PCM L16</span>
      {/if}
    </div>
  {/if}

  <div class="stream-scroll max-h-[500px] space-y-3 overflow-y-auto pr-1">
    {#if visibleMessages.length === 0}
      <p class="text-sm text-cyan-100/70">Waiting for streamed text, image, audio, video, and action events.</p>
    {/if}

    {#each visibleMessages as msg}
      <article class="rounded-lg border border-cyan-300/15 bg-slate-950/45 p-3 text-sm">
        {#if msg.type === 'text'}
          <p>{msg.text}</p>
        {:else if msg.type === 'image'}
          <img src={msg.url} alt="Generated scene" class="w-full rounded-md" />
        {:else if msg.type === 'audio'}
          <audio controls src={msg.url} class="w-full"></audio>
        {:else if msg.type === 'video'}
          <video controls src={msg.url} class="w-full rounded-md">
            <track kind="captions" />
          </video>
        {:else if msg.type === 'action'}
          <p class="neon-label">Action: {msg.action}</p>
        {/if}
      </article>
    {/each}
  </div>
</section>
