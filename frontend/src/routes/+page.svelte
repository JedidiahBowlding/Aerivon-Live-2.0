<script lang="ts">
	import { onMount } from 'svelte';
	import { gsap } from 'gsap';

	import AIBackground from '../components/AIBackground.svelte';
	import AgentTimeline from '../components/AgentTimeline.svelte';
	import BrowserView from '../components/BrowserView.svelte';
	import StoryStream from '../components/StoryStream.svelte';
	import VideoGenerationPanel from '../components/VideoGenerationPanel.svelte';
	import VoiceInput from '../components/VoiceInput.svelte';
	import {
		browserUrl,
		browserScreenshot,
		liveVisualFrames,
		completedStepIds,
		currentExecutingStepId,
		eventsReceived,
		lastEventAt,
		latestStoryText,
		plannerIntents,
		plannerSteps,
		promptsSent,
		pushMessage,
		resetStream,
		runCompletedAt,
		socketState,
		streamMessages,
		timelineSteps,
		type PlannerStep,
		type LiveVisualFrame,
		type StreamMessage
	} from '$lib/agentStore';
	import { closeSocket, connectAerivonSocket, sendInterrupt, sendSocketMessage } from '$lib/websocket';

	let steps: string[] = [];
	let plan: PlannerStep[] = [];
	let intents: string[] = [];
	let activePlanStepId: number | null = null;
	let donePlanStepIds: number[] = [];
	let messages: StreamMessage[] = [];
	let screenshot: string | null = null;
	let siteUrl: string | null = null;
	let frames: LiveVisualFrame[] = [];
	let liveSocketState: 'connecting' | 'connected' | 'disconnected' | 'error' = 'disconnected';
	let sentCount = 0;
	let recvCount = 0;
	let lastEventText = 'none';
	let completedAt: number | null = null;
	let storyText = '';
	let videoPanel: { startFromVoiceRequest: (voiceText: string) => Promise<void> } | null = null;

	$: steps = $timelineSteps;
	$: plan = $plannerSteps;
	$: intents = $plannerIntents;
	$: activePlanStepId = $currentExecutingStepId;
	$: donePlanStepIds = $completedStepIds;
	$: messages = $streamMessages;
	$: screenshot = $browserScreenshot;
	$: siteUrl = $browserUrl;
	$: frames = $liveVisualFrames;
	$: liveSocketState = $socketState;
	$: sentCount = $promptsSent;
	$: recvCount = $eventsReceived;
	$: lastEventText = $lastEventAt ? new Date($lastEventAt).toLocaleTimeString() : 'none';
	$: completedAt = $runCompletedAt;
	$: storyText = $latestStoryText;

	function shouldTriggerVeoFromVoice(text: string): boolean {
		const value = (text || '').toLowerCase();
		if (!value) {
			return false;
		}
		const hasVideoCue = /\b(video|veo|cinematic|scene|trailer|clip|short|animation|film)\b/.test(value);
		const hasImageCue = /\b(illustration|illustrate|image|artwork|art|draw|poster)\b/.test(value);
		const hasCreationCue = /\b(make|create|generate|render|produce|build|craft|design|show)\b/.test(value);
		const hasRequestCue = /\b(want|need|please|can you|could you|let's|lets)\b/.test(value);

		if (!(hasVideoCue || hasImageCue)) {
			return false;
		}

		// Trigger if the user clearly asks for media creation, even when wording is conversational.
		return hasCreationCue || hasRequestCue;
	}

	function submitPrompt(event: CustomEvent<{ text: string }>): void {
		const text = event.detail.text;
		const autoVeo = shouldTriggerVeoFromVoice(text) && !!videoPanel;
		pushMessage({ type: 'action', action: `user:${text}`, ts: Date.now() });

		const sent = sendSocketMessage({ type: 'prompt', text });
		if (!sent) {
			pushMessage({
				type: 'action',
				action: autoVeo ? 'socket_not_ready_veo_fallback' : 'socket_not_ready',
				ts: Date.now()
			});
		}

		if (autoVeo && videoPanel) {
			pushMessage({
				type: 'action',
				action: 'veo_auto_triggered_from_voice',
				ts: Date.now()
			});
			void videoPanel.startFromVoiceRequest(text);
		} else if (!autoVeo) {
			pushMessage({
				type: 'action',
				action: 'veo_auto_not_triggered',
				ts: Date.now()
			});
		}
	}

	function interruptRun(): void {
		const sent = sendInterrupt();
		pushMessage({
			type: 'action',
			action: sent ? 'user_interrupt' : 'interrupt_not_sent',
			ts: Date.now()
		});
	}

	function handleVideoReady(event: CustomEvent<{ url: string }>): void {
		const url = event.detail.url;
		pushMessage({
			type: 'action',
			action: 'veo_video_ready',
			ts: Date.now()
		});
		pushMessage({
			type: 'video',
			url,
			ts: Date.now()
		});
	}

	onMount(() => {
		const ws = connectAerivonSocket();

		gsap.from('.hero-title', {
			y: 18,
			opacity: 0,
			duration: 0.8,
			ease: 'power3.out'
		});

		gsap.from('.panel-stack > *', {
			y: 20,
			opacity: 0,
			duration: 0.6,
			stagger: 0.1,
			ease: 'power2.out',
			delay: 0.12
		});

		if (!ws) {
			pushMessage({
				type: 'action',
				action: 'socket_unavailable',
				ts: Date.now()
			});
		}

		return () => {
			closeSocket();
			resetStream();
		};
	});
</script>

<svelte:head>
	<title>Aerivon OS</title>
	<meta
		name="description"
		content="Aerivon futuristic multimodal cockpit for voice, navigation, and creative storytelling"
	/>
</svelte:head>

<AIBackground />

<main class="relative z-10 mx-auto min-h-screen w-full max-w-[1450px] px-4 pb-6 pt-6 md:px-8 md:pt-8">
	<section class="mb-5 grid gap-4 md:grid-cols-[1.1fr_auto] md:items-end">
		<div>
			<div class="mb-3 inline-flex items-center gap-3 rounded-xl border border-cyan-300/25 bg-slate-950/50 px-3 py-2">
				<img src="/branding/logo.png" alt="Aerivon logo" class="h-8 w-8 object-contain" />
				<span class="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-100/85">Aerivon</span>
			</div>
			<p class="neon-label mb-2 text-xs uppercase tracking-[0.22em]">Aerivon Multimodal Runtime</p>
			<h1 class="hero-title text-3xl font-bold leading-tight text-cyan-50 md:text-5xl">
				Voice-driven creative operating system
			</h1>
		</div>
		<div class="glass-panel rounded-2xl px-4 py-3 text-xs text-cyan-100/80">
			<div>
				Stream: <span class="text-cyan-300">Text • Image • Audio • Video • Action</span>
			</div>
			<div class="mt-1 text-cyan-100/70">
				Socket: <span class={liveSocketState === 'connected' ? 'text-emerald-300' : liveSocketState === 'error' ? 'text-rose-300' : 'text-amber-300'}>{liveSocketState}</span>
				 | Prompts: <span class="text-cyan-200">{sentCount}</span>
				 | Events: <span class="text-cyan-200">{recvCount}</span>
				 | Last Event: <span class="text-cyan-200">{lastEventText}</span>
			</div>
		</div>
	</section>

	<section class="panel-stack mb-4">
		<VoiceInput on:submit={submitPrompt} on:interrupt={interruptRun} />
	</section>

	<section class="panel-stack mb-4">
		<VideoGenerationPanel bind:this={videoPanel} on:videoReady={handleVideoReady} />
	</section>

	<section class="panel-stack grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
		<div class="space-y-4">
			<AgentTimeline
				steps={steps}
				plannedSteps={plan}
				intents={intents}
				currentExecutingStepId={activePlanStepId}
				completedStepIds={donePlanStepIds}
				runCompletedAt={completedAt}
			/>
			<StoryStream messages={messages} latestStoryText={storyText} />
		</div>
		<BrowserView screenshot={screenshot} url={siteUrl} frames={frames} />
	</section>
</main>
