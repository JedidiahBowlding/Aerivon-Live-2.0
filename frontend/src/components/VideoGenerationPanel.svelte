<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { browser } from '$app/environment';

  type VideoReadyEvent = {
    url: string;
  };

  type VeoStatusPayload = {
    type: 'veo_status';
    job_id: string;
    status: string;
    progress?: number;
    video_url?: string | null;
    preview_video_url?: string | null;
    fast_preview?: boolean;
    error?: string | null;
  };

  const dispatch = createEventDispatcher<{ videoReady: VideoReadyEvent }>();
  const SUPPORTED_DURATIONS = [30, 45, 60] as const;

  let prompt = 'Create a cinematic 45-second product demo of Aerivon Live V2 showing voice interaction, planning, navigation, storytelling, and value outcome.';
  let model = 'veo-3.1-generate-001';
  let durationSeconds = 45;
  let aspectRatio = '16:9';

  let isRunning = false;
  let jobId: string | null = null;
  let status = 'idle';
  let progress = 0;
  let errorMessage = '';
  let finalVideoUrl: string | null = null;
  let previewVideoUrl: string | null = null;
  let statusLog: string[] = [];

  let ws: WebSocket | null = null;

  function apiBase(): string {
    const envUrl = (import.meta.env.VITE_AERIVON_API_URL as string | undefined)?.trim();
    if (envUrl) {
      return envUrl.replace(/\/$/, '');
    }
    if (!browser) {
      return 'http://localhost:8081';
    }
    return `${location.protocol}//${location.hostname}:8081`;
  }

  function wsBaseFromApi(base: string): string {
    const wsBase = base.startsWith('https://') ? base.replace('https://', 'wss://') : base.replace('http://', 'ws://');
    if (browser && location.protocol === 'https:' && wsBase.startsWith('ws://')) {
      return `wss://${wsBase.slice(5)}`;
    }
    return wsBase;
  }

  function normalizeWsUrl(url: string): string {
    const trimmed = (url || '').trim();
    if (browser && location.protocol === 'https:' && trimmed.startsWith('ws://')) {
      return `wss://${trimmed.slice(5)}`;
    }
    return trimmed;
  }

  function absolutizeVideoUrl(pathOrUrl: string): string {
    if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')) {
      return pathOrUrl;
    }
    return `${apiBase()}${pathOrUrl.startsWith('/') ? '' : '/'}${pathOrUrl}`;
  }

  function addStatusLog(message: string): void {
    const stamp = new Date().toLocaleTimeString();
    statusLog = [`${stamp} - ${message}`, ...statusLog].slice(0, 12);
  }

  function closeStatusSocket(): void {
    if (ws) {
      ws.close();
      ws = null;
    }
  }

  function handleStatusEvent(payload: VeoStatusPayload): void {
    status = payload.status || status;
    progress = typeof payload.progress === 'number' ? payload.progress : progress;

    if (payload.error) {
      errorMessage = payload.error;
      addStatusLog(`Failed: ${payload.error}`);
      isRunning = false;
      return;
    }

    addStatusLog(`Status: ${status} (${progress}%)`);

    if (payload.preview_video_url) {
      const nextPreviewUrl = absolutizeVideoUrl(payload.preview_video_url);
      if (nextPreviewUrl !== previewVideoUrl) {
        previewVideoUrl = nextPreviewUrl;
        addStatusLog('Preview video ready.');
      }
    }

    if (payload.video_url && payload.status === 'completed') {
      finalVideoUrl = absolutizeVideoUrl(payload.video_url);
      dispatch('videoReady', { url: finalVideoUrl });
      isRunning = false;
      addStatusLog('Video ready for playback.');
    }
  }

  async function startVideoGeneration(): Promise<void> {
    if (isRunning) {
      return;
    }

    errorMessage = '';
    finalVideoUrl = null;
    previewVideoUrl = null;
    statusLog = [];
    status = 'submitting';
    progress = 0;
    isRunning = true;

    closeStatusSocket();

    const normalizedDuration = SUPPORTED_DURATIONS.includes(durationSeconds as 30 | 45 | 60)
      ? durationSeconds
      : 45;

    try {
      const response = await fetch(`${apiBase()}/veo/jobs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          prompt,
          model,
          duration_seconds: normalizedDuration,
          aspect_ratio: aspectRatio,
          fast_preview: true
        })
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`Job create failed (${response.status}): ${detail}`);
      }

      const job = (await response.json()) as VeoStatusPayload & { ws_url?: string };
      jobId = job.job_id;
      handleStatusEvent(job);

      const wsUrl = normalizeWsUrl(job.ws_url || `${wsBaseFromApi(apiBase())}/ws/veo/${job.job_id}`);
      ws = new WebSocket(wsUrl);

      ws.onopen = () => addStatusLog('Connected to Veo status stream.');
      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as VeoStatusPayload;
          if (payload.type === 'veo_status') {
            handleStatusEvent(payload);
          }
        } catch {
          // Ignore malformed status frames.
        }
      };
      ws.onerror = () => {
        addStatusLog('Status websocket error.');
      };
      ws.onclose = () => {
        ws = null;
        if (status !== 'completed' && status !== 'failed') {
          addStatusLog('Status websocket closed.');
        }
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown Veo job error.';
      errorMessage = message;
      isRunning = false;
      status = 'failed';
      addStatusLog(`Failed: ${message}`);
    }
  }

  export async function startFromVoiceRequest(voiceText: string): Promise<void> {
    const trimmed = (voiceText || '').trim();
    if (!trimmed) {
      return;
    }
    prompt = trimmed;
    await startVideoGeneration();
  }
</script>

<section class="glass-panel p-4 md:p-5">
  <div class="mb-4 flex items-center justify-between">
    <h2 class="panel-title text-sm uppercase tracking-[0.18em] text-cyan-200">Veo Video Generator</h2>
    <span class="text-xs text-cyan-100/70">Backend Job + WS Status</span>
  </div>

  <div class="space-y-3">
    <label class="block text-xs text-cyan-100/75">Prompt</label>
    <textarea
      bind:value={prompt}
      rows="3"
      class="w-full rounded-lg border border-cyan-300/25 bg-slate-950/55 px-3 py-2 text-sm text-cyan-50 outline-none focus:border-cyan-300/60"
      placeholder="Describe the demo scene sequence"
    ></textarea>

    <div class="grid gap-3 md:grid-cols-3">
      <label class="text-xs text-cyan-100/75">
        Model
        <input
          bind:value={model}
          class="mt-1 w-full rounded-md border border-cyan-300/25 bg-slate-950/55 px-2 py-1.5 text-sm text-cyan-50 outline-none focus:border-cyan-300/60"
        />
      </label>
      <label class="text-xs text-cyan-100/75">
        Clip Seconds
        <select
          bind:value={durationSeconds}
          class="mt-1 w-full rounded-md border border-cyan-300/25 bg-slate-950/55 px-2 py-1.5 text-sm text-cyan-50 outline-none focus:border-cyan-300/60"
        >
          {#each SUPPORTED_DURATIONS as seconds}
            <option value={seconds}>{seconds}</option>
          {/each}
        </select>
      </label>
      <label class="text-xs text-cyan-100/75">
        Aspect
        <input
          bind:value={aspectRatio}
          class="mt-1 w-full rounded-md border border-cyan-300/25 bg-slate-950/55 px-2 py-1.5 text-sm text-cyan-50 outline-none focus:border-cyan-300/60"
        />
      </label>
    </div>

    <div class="flex items-center gap-3">
      <button
        on:click={startVideoGeneration}
        disabled={isRunning}
        class="rounded-lg border border-cyan-300/35 bg-cyan-400/15 px-4 py-2 text-sm text-cyan-100 transition hover:bg-cyan-400/25 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isRunning ? 'Generating...' : 'Generate Video'}
      </button>
      <div class="text-xs text-cyan-100/75">Job: {jobId || 'none'} | Status: {status} | Progress: {progress}%</div>
    </div>

    {#if errorMessage}
      <div class="rounded-md border border-rose-300/35 bg-rose-400/10 px-3 py-2 text-xs text-rose-200">{errorMessage}</div>
    {/if}

    {#if finalVideoUrl}
      <div class="rounded-xl border border-emerald-300/35 bg-emerald-400/10 p-3">
        <div class="mb-2 text-xs uppercase tracking-wide text-emerald-200">Final Veo Video</div>
        <video controls class="w-full rounded-md" src={finalVideoUrl}>
          <track kind="captions" />
        </video>
        <a class="mt-2 inline-block text-xs text-emerald-200 underline" href={finalVideoUrl} target="_blank" rel="noopener noreferrer">Open video in new tab</a>
      </div>
    {/if}

    {#if previewVideoUrl && !finalVideoUrl}
      <div class="rounded-xl border border-amber-300/35 bg-amber-400/10 p-3">
        <div class="mb-2 text-xs uppercase tracking-wide text-amber-200">Preview Video (Fast)</div>
        <video controls class="w-full rounded-md" src={previewVideoUrl}>
          <track kind="captions" />
        </video>
      </div>
    {/if}

    <div class="rounded-md border border-cyan-300/20 bg-slate-950/45 p-3">
      <div class="mb-2 text-[11px] uppercase tracking-[0.14em] text-cyan-200/80">Status Log</div>
      <div class="max-h-28 space-y-1 overflow-y-auto text-xs text-cyan-100/70">
        {#if statusLog.length === 0}
          <div>Waiting for job events.</div>
        {:else}
          {#each statusLog as line}
            <div>{line}</div>
          {/each}
        {/if}
      </div>
    </div>
  </div>
</section>
