import { writable } from 'svelte/store';

export type TimelineState =
  | 'Listening'
  | 'Planning'
  | 'Navigating'
  | 'Analyzing'
  | 'Creating'
  | 'Rendering';

export type StreamMessage =
  | { type: 'text'; text: string; ts: number }
  | { type: 'image'; url: string; ts: number }
  | { type: 'audio'; url: string; ts: number; mime_type?: string }
  | { type: 'video'; url: string; ts: number }
  | { type: 'action'; action: string; ts: number };

export type PlannerStep = {
  id: number;
  capability: string;
  action: string;
};

export type LiveVisualFrame = {
  type: 'screenshot' | 'illustration' | 'status';
  url: string;
  ts: number;
  label?: string;
};

export const timelineSteps = writable<TimelineState[]>(['Listening']);
export const streamMessages = writable<StreamMessage[]>([]);
export const browserScreenshot = writable<string | null>(null);
export const browserUrl = writable<string | null>(null);
export const liveVisualFrames = writable<LiveVisualFrame[]>([]);
export const isListening = writable(false);
export const plannerSteps = writable<PlannerStep[]>([]);
export const plannerIntents = writable<string[]>([]);
export const currentExecutingStepId = writable<number | null>(null);
export const completedStepIds = writable<number[]>([]);
export const socketState = writable<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
export const promptsSent = writable(0);
export const eventsReceived = writable(0);
export const lastEventAt = writable<number | null>(null);
export const runCompletedAt = writable<number | null>(null);
export const latestStoryText = writable<string>('');

export function pushStep(step: TimelineState): void {
  timelineSteps.update((steps) => {
    if (steps[steps.length - 1] === step) {
      return steps;
    }
    return [...steps.slice(-6), step];
  });
}

export function pushMessage(msg: StreamMessage): void {
  streamMessages.update((messages) => [...messages.slice(-60), msg]);
}

export function resetStream(): void {
  timelineSteps.set(['Listening']);
  streamMessages.set([]);
  browserScreenshot.set(null);
  browserUrl.set(null);
  liveVisualFrames.set([]);
  plannerSteps.set([]);
  plannerIntents.set([]);
  currentExecutingStepId.set(null);
  completedStepIds.set([]);
  eventsReceived.set(0);
  lastEventAt.set(null);
  runCompletedAt.set(null);
  latestStoryText.set('');
}

export function setPlanner(plan: PlannerStep[], intents: string[]): void {
  plannerSteps.set(plan);
  plannerIntents.set(intents);
  completedStepIds.set([]);
}

export function setCurrentExecutingStep(stepId: number | null): void {
  currentExecutingStepId.set(stepId);
}

export function setCompletedSteps(stepIds: number[]): void {
  completedStepIds.set(stepIds);
}

export function markPromptSent(): void {
  promptsSent.update((v) => v + 1);
  runCompletedAt.set(null);
  latestStoryText.set('');
}

export function markEventReceived(ts: number): void {
  eventsReceived.update((v) => v + 1);
  lastEventAt.set(ts);
}

export function markRunCompleted(ts: number): void {
  runCompletedAt.set(ts);
}

export function appendLiveVisualFrame(frame: LiveVisualFrame): void {
  liveVisualFrames.update((frames) => [...frames.slice(-18), frame]);
}

export function resetRunVisuals(): void {
  browserScreenshot.set(null);
  browserUrl.set(null);
  liveVisualFrames.set([]);
  runCompletedAt.set(null);
}

export function setLatestStoryText(text: string): void {
  latestStoryText.set(text);
}
