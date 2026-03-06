<script lang="ts">
  import type { LiveVisualFrame } from '$lib/agentStore';

  export let screenshot: string | null = null;
  export let url: string | null = null;
  export let frames: LiveVisualFrame[] = [];

  $: latest = frames.length > 0 ? frames[frames.length - 1] : null;
  let selectedFrameTs: number | null = null;
  let userSelected = false;
  $: if (frames.length === 0) selectedFrameTs = null;
  $: if (frames.length === 0) userSelected = false;
  $: preferred = [...frames].reverse().find((f) => f.type !== 'status') ?? latest;
  $: if (frames.length > 0 && (!userSelected || selectedFrameTs === null || !frames.some((f) => f.ts === selectedFrameTs))) {
    selectedFrameTs = preferred ? preferred.ts : frames[frames.length - 1].ts;
  }
  $: selected = frames.find((f) => f.ts === selectedFrameTs) ?? latest;
  let showEmbed = false;
</script>

<section class="glass-panel p-4 md:p-5">
  <div class="mb-4 flex items-center justify-between">
    <h2 class="panel-title text-sm uppercase tracking-[0.18em] text-cyan-200">Live Browser View</h2>
    <span class="text-xs text-cyan-100/70">Navigator Feed</span>
  </div>

  {#if url}
    <div class="mb-3 rounded-lg border border-cyan-300/20 bg-slate-950/50 px-3 py-2 text-xs text-cyan-100/85">
      <div class="mb-1 text-cyan-100/65">Current Site</div>
      <a class="break-all text-cyan-300 underline" href={url} target="_blank" rel="noopener noreferrer">{url}</a>
    </div>
  {/if}

  {#if url}
    <div class="mb-3 rounded-xl border border-cyan-300/20 bg-slate-950/55 p-3 text-xs text-cyan-100/80">
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
        <span>Live site embedding can be blocked by `X-Frame-Options` or CSP headers.</span>
        <div class="flex items-center gap-2">
          <a
            class="rounded-md border border-cyan-300/35 px-2 py-1 text-[11px] text-cyan-100 hover:bg-cyan-300/15"
            href={url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open Site
          </a>
          <button
            class="rounded-md border border-cyan-300/35 px-2 py-1 text-[11px] text-cyan-100 hover:bg-cyan-300/15"
            on:click={() => (showEmbed = !showEmbed)}
          >
            {showEmbed ? 'Hide Embed' : 'Try Embed'}
          </button>
        </div>
      </div>
      <p class="text-cyan-100/60">If blocked, rely on the screenshot feed below. It is captured by Playwright and reflects where the agent actually went.</p>
    </div>

    {#if showEmbed}
      <div class="mb-3 overflow-hidden rounded-xl border border-cyan-300/20 bg-slate-950/70">
        <iframe
          src={url}
          class="h-[300px] w-full md:h-[360px]"
          title="Live site preview"
          loading="lazy"
          referrerpolicy="no-referrer"
        ></iframe>
      </div>
    {/if}
  {/if}

  <div class="overflow-hidden rounded-xl border border-cyan-300/20 bg-slate-950/65">
    {#if selected}
      <img
        class="h-[320px] w-full object-cover md:h-[520px]"
        src={selected.url}
        alt={selected.type === 'illustration' ? 'Story illustration' : selected.type === 'status' ? 'Execution step card' : 'Browser screenshot'}
      />
      <div class="border-t border-cyan-300/20 px-3 py-2 text-xs text-cyan-100/75">
        Live frame: {selected.type === 'illustration' ? 'illustration' : selected.type === 'status' ? 'step' : 'screenshot'}
        {#if selected.label}
          <span class="text-cyan-200"> | {selected.label}</span>
        {/if}
      </div>
    {:else if screenshot}
      <img class="h-[320px] w-full object-cover md:h-[520px]" src={screenshot} alt="Latest browser screenshot" />
    {:else}
      <div class="flex h-[320px] items-center justify-center p-5 text-center text-sm text-cyan-100/70 md:h-[520px]">
        Live visuals appear here from both browser navigation screenshots and generated illustrations.
      </div>
    {/if}
  </div>

  {#if frames.length > 1}
    <div class="mt-3 grid max-h-36 grid-cols-4 gap-2 overflow-y-auto pr-1 md:grid-cols-6">
      {#each [...frames].reverse() as frame}
        <button
          class={`overflow-hidden rounded-md border bg-slate-950/50 text-left ${selectedFrameTs === frame.ts ? 'border-cyan-300/70 ring-1 ring-cyan-300/65' : 'border-cyan-300/20'}`}
          on:click={() => {
            userSelected = true;
            selectedFrameTs = frame.ts;
          }}
          aria-label={`Show ${frame.type} frame`}
        >
          <img class="h-14 w-full object-cover" src={frame.url} alt={frame.type} />
          <div class="px-1 py-0.5 text-[10px] text-cyan-100/70">
            {frame.type === 'illustration' ? 'art' : frame.type === 'status' ? 'step' : 'nav'}
          </div>
        </button>
      {/each}
    </div>
  {/if}
</section>
