<script lang="ts">
  import { onDestroy } from 'svelte';
  import { createEventDispatcher } from 'svelte';
  import { isListening, pushStep, streamMessages, type StreamMessage } from '$lib/agentStore';

  const dispatch = createEventDispatcher<{ submit: { text: string }; interrupt: null }>();

  type SpeechResult = {
    isFinal: boolean;
    0: { transcript: string };
  };

  type SpeechEventLike = Event & {
    resultIndex: number;
    results: ArrayLike<SpeechResult>;
  };

  type SpeechRecognitionLike = {
    lang: string;
    continuous: boolean;
    interimResults: boolean;
    onresult: ((event: SpeechEventLike) => void) | null;
    onerror: ((event: Event & { error?: string }) => void) | null;
    onend: (() => void) | null;
    start: () => void;
    stop: () => void;
  };

  type SpeechCtor = new () => SpeechRecognitionLike;

  let prompt = '';
  let pendingPrompt = '';
  let listening = false;
  let micError = '';

  let recognition: SpeechRecognitionLike | null = null;
  let micStream: MediaStream | null = null;
  let finalTranscript = '';
  let stoppingIntentional = false;
  let silenceTimer: ReturnType<typeof setTimeout> | null = null;

  let autoReadStory = true;
  let handsFreeMode = true;
  let assistantSpeaking = false;
  let currentAudio: HTMLAudioElement | null = null;
  let currentAudioCtx: AudioContext | null = null;
  let currentBufferSource: AudioBufferSourceNode | null = null;
  let lastPlayedAudioUrl = '';
  let lastPlayedAudioMime = '';

  function clearSilenceTimer(): void {
    if (!silenceTimer) {
      return;
    }
    clearTimeout(silenceTimer);
    silenceTimer = null;
  }

  function stopAssistantVoice(emitInterrupt = false): void {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      currentAudio = null;
    }
    if (currentBufferSource) {
      try {
        currentBufferSource.stop();
      } catch {
        // Ignore if already stopped.
      }
      currentBufferSource = null;
    }
    if (currentAudioCtx) {
      void currentAudioCtx.close();
      currentAudioCtx = null;
    }
    assistantSpeaking = false;
    if (emitInterrupt) {
      dispatch('interrupt', null);
    }
  }

  function latestAudioMessage(messages: StreamMessage[]): { url: string; mimeType?: string } | null {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const msg = messages[i];
      if (msg.type === 'audio' && typeof msg.url === 'string' && msg.url.trim()) {
        return { url: msg.url.trim(), mimeType: msg.mime_type };
      }
    }
    return null;
  }

  function extractRateFromMime(mimeType: string | undefined): number {
    if (!mimeType) {
      return 24000;
    }
    const m = mimeType.match(/rate=(\d+)/i);
    return m ? Number.parseInt(m[1], 10) : 24000;
  }

  function decodeBase64ToBytes(b64: string): Uint8Array {
    const binary = atob(b64);
    const out = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      out[i] = binary.charCodeAt(i);
    }
    return out;
  }

  async function playPcmL16DataUrl(url: string, mimeType: string | undefined): Promise<void> {
    const comma = url.indexOf(',');
    if (comma < 0) {
      throw new Error('Invalid PCM audio payload.');
    }

    const b64 = url.slice(comma + 1);
    const bytes = decodeBase64ToBytes(b64);
    if (bytes.length < 2) {
      throw new Error('PCM payload too short.');
    }

    const sampleRate = extractRateFromMime(mimeType);
    const sampleCount = Math.floor(bytes.length / 2);
    const floats = new Float32Array(sampleCount);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);

    // Gemini WS streams PCM s16le; keep big-endian as fallback for L16 payloads.
    const isLittleEndian = (mimeType || '').toLowerCase().includes('pcm');
    for (let i = 0; i < sampleCount; i += 1) {
      const sample = view.getInt16(i * 2, isLittleEndian);
      floats[i] = sample / 32768;
    }

    const AudioContextCtor = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextCtor) {
      throw new Error('Web Audio API unavailable.');
    }

    const ctx = new AudioContextCtor();
    currentAudioCtx = ctx;
    const buffer = ctx.createBuffer(1, floats.length, sampleRate);
    buffer.copyToChannel(floats, 0);

    const source = ctx.createBufferSource();
    currentBufferSource = source;
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.onended = () => {
      assistantSpeaking = false;
      currentBufferSource = null;
      if (currentAudioCtx) {
        void currentAudioCtx.close();
        currentAudioCtx = null;
      }
      if (handsFreeMode && !listening) {
        void startListening();
      }
    };

    assistantSpeaking = true;
    source.start(0);
  }

  function playGeminiAudio(url: string, mimeType?: string): void {
    if (typeof window === 'undefined') {
      return;
    }

    if (!url.trim()) {
      return;
    }

    if (currentAudio || currentBufferSource || currentAudioCtx) {
      stopAssistantVoice(false);
    }

    const normalizedMime = (mimeType || '').toLowerCase();
    if (normalizedMime.includes('audio/l16') || normalizedMime.includes('audio/pcm')) {
      void playPcmL16DataUrl(url, mimeType).catch(() => {
        micError = 'Gemini audio decode failed. Please try again.';
        assistantSpeaking = false;
      });
      return;
    }

    const player = new Audio(url);
    player.onplay = () => {
      assistantSpeaking = true;
    };
    player.onended = () => {
      assistantSpeaking = false;
      currentAudio = null;
      if (handsFreeMode && !listening) {
        void startListening();
      }
    };
    player.onerror = () => {
      micError = 'Audio playback failed for streamed model voice.';
      assistantSpeaking = false;
      currentAudio = null;
    };

    currentAudio = player;
    void player.play().catch(() => {
      micError = 'Auto-play blocked. Press Mic or interact with page, then retry.';
      assistantSpeaking = false;
      currentAudio = null;
    });
  }

  function speechCtor(): SpeechCtor | null {
    if (typeof window === 'undefined') {
      return null;
    }

    const w = window as unknown as {
      SpeechRecognition?: SpeechCtor;
      webkitSpeechRecognition?: SpeechCtor;
    };

    return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
  }

  function releaseMic(): void {
    if (!micStream) {
      return;
    }
    micStream.getTracks().forEach((track) => track.stop());
    micStream = null;
  }

  function setupRecognition(): boolean {
    if (recognition) {
      return true;
    }

    const Ctor = speechCtor();
    if (!Ctor) {
      micError = 'Speech recognition is not supported in this browser.';
      return false;
    }

    recognition = new Ctor();
    recognition.lang = 'en-US';
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event: SpeechEventLike) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const transcript = result?.[0]?.transcript ?? '';
        if (result?.isFinal) {
          finalTranscript += `${transcript} `;
        } else {
          interim += transcript;
        }
      }
      prompt = `${finalTranscript}${interim}`.trim();

      clearSilenceTimer();
      if (prompt) {
        // Natural turn-taking: send after a short pause instead of requiring manual stop.
        silenceTimer = setTimeout(() => {
          if (listening && recognition && prompt.trim()) {
            stoppingIntentional = true;
            recognition.stop();
          }
        }, 1800);
      }
    };

    recognition.onerror = (event: Event & { error?: string }) => {
      micError = event.error ? `Mic error: ${event.error}` : 'Microphone error occurred.';
      listening = false;
      isListening.set(false);
      releaseMic();
      clearSilenceTimer();
    };

    recognition.onend = () => {
      const shouldSubmit = stoppingIntentional;
      stoppingIntentional = false;
      listening = false;
      isListening.set(false);
      releaseMic();
      clearSilenceTimer();

      if (shouldSubmit && finalTranscript.trim()) {
        queuePromptForConfirmation(finalTranscript);
      } else if (shouldSubmit && prompt.trim()) {
        // Fallback when the recognizer delivered interim text but no final segment.
        queuePromptForConfirmation(prompt);
      }

      finalTranscript = '';
    };

    return true;
  }

  async function startListening(): Promise<void> {
    micError = '';
    finalTranscript = '';

    if (pendingPrompt.trim()) {
      micError = 'Review and confirm, edit, or cancel the pending prompt first.';
      return;
    }

    if (assistantSpeaking) {
      stopAssistantVoice(true);
    }

    if (!setupRecognition() || !recognition) {
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      micError = 'Microphone API is unavailable in this browser.';
      return;
    }

    try {
      // This is what triggers the browser mic permission prompt.
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stoppingIntentional = false;
      recognition.start();
      listening = true;
      isListening.set(true);
      pushStep('Listening');
    } catch {
      micError = 'Microphone access was blocked or unavailable.';
      releaseMic();
    }
  }

  function stopListening(): void {
    if (!recognition) {
      listening = false;
      isListening.set(false);
      releaseMic();
      return;
    }

    stoppingIntentional = true;
    clearSilenceTimer();
    recognition.stop();
  }

  async function toggleMic(): Promise<void> {
    if (listening) {
      stopListening();
      return;
    }
    await startListening();
  }

  function submitPrompt(): void {
    const text = prompt.trim();
    if (!text) {
      return;
    }
    queuePromptForConfirmation(text);
  }

  function manualInterrupt(): void {
    stopAssistantVoice(true);
    if (listening) {
      stopListening();
    }
  }

  function queuePromptForConfirmation(text: string): void {
    const normalized = text.trim();
    if (!normalized) {
      return;
    }
    pendingPrompt = normalized;
    prompt = normalized;
  }

  function confirmPrompt(): void {
    const text = pendingPrompt.trim();
    if (!text) {
      return;
    }
    dispatch('submit', { text });
    pushStep('Planning');
    pendingPrompt = '';
    prompt = '';
  }

  function editPrompt(): void {
    if (!pendingPrompt.trim()) {
      return;
    }
    prompt = pendingPrompt;
    pendingPrompt = '';
  }

  function cancelPrompt(): void {
    pendingPrompt = '';
  }

  $: if (autoReadStory) {
    const audio = latestAudioMessage($streamMessages);
    if (audio && (audio.url !== lastPlayedAudioUrl || (audio.mimeType || '') !== lastPlayedAudioMime)) {
      lastPlayedAudioUrl = audio.url;
      lastPlayedAudioMime = audio.mimeType || '';
      playGeminiAudio(audio.url, audio.mimeType);
    }
  }

  onDestroy(() => {
    clearSilenceTimer();
    stopAssistantVoice(false);
    releaseMic();
  });

  $: micClass = listening
    ? 'rounded-xl px-4 py-3 text-sm font-semibold transition bg-emerald-300/80 text-black'
    : 'rounded-xl px-4 py-3 text-sm font-semibold transition bg-cyan-300/20 text-cyan-100';
</script>

<div class="glass-panel p-3 md:p-4">
  <div class="mb-2 flex items-center justify-between">
    <p class="panel-title text-xs uppercase tracking-[0.18em] text-cyan-200/80">Voice Input</p>
    <p class="text-xs text-cyan-100/70">Natural mode: pause to draft, then confirm before send</p>
  </div>

  <div class="mb-3 flex flex-wrap items-center gap-3 text-xs text-cyan-100/80">
    <label class="inline-flex items-center gap-2">
      <input type="checkbox" bind:checked={autoReadStory} />
      Auto-play Gemini voice
    </label>
    <label class="inline-flex items-center gap-2">
      <input type="checkbox" bind:checked={handsFreeMode} />
      Hands-free turn-taking
    </label>
    <span class={assistantSpeaking ? 'text-emerald-300' : 'text-cyan-200/80'}>
      {assistantSpeaking ? 'Gemini Voice: speaking' : 'Gemini Voice: idle'}
    </span>
  </div>

  {#if micError}
    <p class="mb-2 text-xs text-rose-300">{micError}</p>
  {/if}

  <div class="flex gap-3">
    <input
      class="w-full rounded-xl border border-cyan-300/30 bg-slate-950/70 px-4 py-3 text-sm text-cyan-50 outline-none transition focus:border-cyan-300"
      placeholder="Say or type: Open nike.com and turn it into a cyberpunk story"
      bind:value={prompt}
      spellcheck="true"
      on:keydown={(e) => e.key === 'Enter' && submitPrompt()}
    />

    <button
      class="rounded-xl border border-cyan-300/45 px-4 py-3 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-300/20"
      on:click={submitPrompt}
      aria-label="Send"
    >
      Send
    </button>

    <button
      class={micClass}
      on:click={toggleMic}
      aria-label="Toggle microphone"
    >
      {listening ? 'Stop' : 'Mic'}
    </button>

    <button
      class="rounded-xl border border-rose-300/45 px-4 py-3 text-sm font-semibold text-rose-200 transition hover:bg-rose-300/15"
      on:click={manualInterrupt}
      aria-label="Interrupt"
    >
      Interrupt
    </button>
  </div>

  {#if pendingPrompt}
    <div class="mt-3 rounded-xl border border-amber-300/40 bg-amber-300/10 p-3">
      <p class="text-xs uppercase tracking-[0.15em] text-amber-200/90">Agent Confirmation</p>
      <p class="mt-1 text-xs text-amber-100/90">I heard this prompt. Do you want me to send it exactly as written?</p>
      <p class="mt-2 text-sm text-amber-100">{pendingPrompt}</p>
      <div class="mt-3 flex flex-wrap gap-2">
        <button
          class="rounded-lg border border-emerald-300/45 px-3 py-2 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-300/15"
          on:click={confirmPrompt}
        >
          Yes, Send It
        </button>
        <button
          class="rounded-lg border border-cyan-300/45 px-3 py-2 text-xs font-semibold text-cyan-100 transition hover:bg-cyan-300/20"
          on:click={editPrompt}
        >
          No, Let Me Edit
        </button>
        <button
          class="rounded-lg border border-rose-300/45 px-3 py-2 text-xs font-semibold text-rose-200 transition hover:bg-rose-300/15"
          on:click={cancelPrompt}
        >
          Cancel
        </button>
      </div>
    </div>
  {/if}
</div>
