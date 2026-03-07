import { browser } from '$app/environment';
import { get } from 'svelte/store';
import {
  appendLiveVisualFrame,
  browserUrl,
  browserScreenshot,
  markRunCompleted,
  markEventReceived,
  markPromptSent,
  plannerSteps,
  pushMessage,
  setCompletedSteps,
  setCurrentExecutingStep,
  setLatestStoryText,
  setPlanner,
  resetRunVisuals,
  socketState,
  pushStep,
  type PlannerStep,
  type StreamMessage,
  type TimelineState
} from '$lib/agentStore';

const ACTION_TO_TIMELINE: Record<string, TimelineState> = {
  listening: 'Listening',
  planning: 'Planning',
  navigating: 'Navigating',
  analyzing: 'Analyzing',
  creating: 'Creating',
  rendering: 'Rendering'
};

export type AerivonSocketMessage =
  | { type: 'text'; text: string }
  | { type: 'transcript'; text: string; finished?: boolean }
  | { type: 'image'; url?: string; data_b64?: string; mime_type?: string }
  | { type: 'audio'; url?: string; data_b64?: string; mime_type?: string }
  | { type: 'video'; url?: string; data_b64?: string; mime_type?: string }
  | { type: 'action'; action: string }
  | { type: 'browser'; screenshot: string | null; url?: string }
  | {
      type: 'plan';
      plan: PlannerStep[];
      intent: { intents?: string[]; confidence?: number };
    };

let ws: WebSocket | null = null;
let planCursor = -1;

function forceSecureWs(url: string): string {
  if (browser && location.protocol === 'https:' && url.startsWith('ws://')) {
    return `wss://${url.slice(5)}`;
  }
  return url;
}

function toStatusCardDataUrl(action: string): string {
  const safe = action.replace(/&/g, 'and').replace(/</g, '').replace(/>/g, '');
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='1280' height='720' viewBox='0 0 1280 720'>
  <defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0%' stop-color='#0E1E35'/><stop offset='100%' stop-color='#1A1038'/></linearGradient></defs>
  <rect width='1280' height='720' fill='url(#g)'/>
  <rect x='50' y='50' width='1180' height='620' rx='16' fill='none' stroke='#5EC4FF' stroke-opacity='0.35'/>
  <text x='90' y='170' fill='#5EC4FF' font-size='42' font-family='monospace'>Aerivon Step</text>
  <text x='90' y='280' fill='#E6F1FF' font-size='56' font-family='monospace'>${safe}</text>
  </svg>`;
  const b64 = btoa(unescape(encodeURIComponent(svg)));
  return `data:image/svg+xml;base64,${b64}`;
}

function matchesAction(step: PlannerStep, action: string): boolean {
  const normalized = action.toLowerCase();
  if (normalized === 'navigating' || normalized === 'analyzing') {
    return step.capability === 'navigator';
  }
  if (normalized === 'creating') {
    return step.capability === 'storyteller' && step.action === 'generate_story';
  }
  if (normalized === 'rendering') {
    return (
      step.capability === 'storyteller' &&
      (step.action === 'generate_illustration' || step.action === 'generate_video')
    );
  }
  return false;
}

function advanceExecutingStep(action: string): void {
  const normalized = action.toLowerCase();
  const plan = get(plannerSteps);

  if (normalized === 'listening' || normalized === 'planning' || normalized === 'interrupted') {
    setCurrentExecutingStep(null);

    if (normalized === 'listening' && plan.length > 0 && planCursor >= 0) {
      setCompletedSteps(plan.map((s) => s.id));
      markRunCompleted(Date.now());
      planCursor = plan.length - 1;
      return;
    }

    if (normalized === 'listening') {
      planCursor = -1;
    }
    if (normalized === 'planning') {
      setCompletedSteps([]);
    }
    return;
  }

  if (plan.length === 0) {
    setCurrentExecutingStep(null);
    setCompletedSteps([]);
    return;
  }

  // First, try advancing to the next matching step so repeated phases like
  // `rendering` can progress from illustration -> video.
  const start = Math.max(0, planCursor + 1);
  for (let i = start; i < plan.length; i += 1) {
    if (matchesAction(plan[i], normalized)) {
      planCursor = i;
      setCurrentExecutingStep(plan[i].id);
      if (i <= 0) {
        setCompletedSteps([]);
      } else {
        setCompletedSteps(plan.slice(0, i).map((s) => s.id));
      }
      return;
    }
  }

  // If no forward step exists, keep the current step active when still compatible.
  if (planCursor >= 0 && planCursor < plan.length && matchesAction(plan[planCursor], normalized)) {
    setCurrentExecutingStep(plan[planCursor].id);
    return;
  }

  // Last fallback: recover by finding the first matching step anywhere.
  for (let i = 0; i < plan.length; i += 1) {
    if (matchesAction(plan[i], normalized)) {
      planCursor = i;
      setCurrentExecutingStep(plan[i].id);
      setCompletedSteps(i <= 0 ? [] : plan.slice(0, i).map((s) => s.id));
      return;
    }
  }
}

function wsUrl(): string {
  const ensureLivePath = (url: string): string => {
    if (url.includes('/ws/live')) {
      return url;
    }
    if (url.includes('/ws/story')) {
      return url.replace('/ws/story', '/ws/live');
    }
    return `${url.replace(/\/$/, '')}/ws/live`;
  };

  const envUrl = (import.meta.env.VITE_AERIVON_WS_URL as string | undefined)?.trim();
  if (envUrl) {
    return forceSecureWs(ensureLivePath(envUrl));
  }

  const apiUrl = (import.meta.env.VITE_AERIVON_API_URL as string | undefined)?.trim();
  if (apiUrl) {
    const wsBase = apiUrl.startsWith('https://')
      ? apiUrl.replace('https://', 'wss://')
      : apiUrl.replace('http://', 'ws://');
    return forceSecureWs(`${wsBase.replace(/\/$/, '')}/ws/live`);
  }

  if (!browser) {
    return forceSecureWs('ws://localhost:8081/ws/live');
  }

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return forceSecureWs(`${protocol}//${location.hostname}:8081/ws/live`);
}

function mediaDataUrl(dataB64: string | undefined, mimeType: string): string | null {
  if (typeof dataB64 !== 'string' || !dataB64.trim()) {
    return null;
  }
  return `data:${mimeType};base64,${dataB64.trim()}`;
}

export function connectAerivonSocket(): WebSocket | null {
  if (!browser) {
    return null;
  }

  if (ws && ws.readyState <= 1) {
    return ws;
  }

  socketState.set('connecting');
  ws = new WebSocket(wsUrl());

  ws.onopen = () => {
    socketState.set('connected');
    setCurrentExecutingStep(null);
    pushStep('Listening');
  };

  ws.onmessage = (event: MessageEvent<string>) => {
    let data: AerivonSocketMessage | null = null;
    try {
      data = JSON.parse(event.data) as AerivonSocketMessage;
    } catch {
      return;
    }

    if (!data) {
      return;
    }

    const ts = Date.now();
    markEventReceived(ts);
    if (data.type === 'browser') {
      browserScreenshot.set(data.screenshot);
      if (typeof data.url === 'string' && data.url.trim()) {
        browserUrl.set(data.url.trim());
      }
      if (typeof data.screenshot === 'string' && data.screenshot.trim()) {
        appendLiveVisualFrame({
          type: 'screenshot',
          url: data.screenshot,
          ts,
          label: typeof data.url === 'string' ? data.url : 'navigator'
        });
      }
      return;
    }

    if (data.type === 'action') {
      const mapped = ACTION_TO_TIMELINE[data.action.toLowerCase()];
      if (mapped) {
        pushStep(mapped);
      }
      advanceExecutingStep(data.action);

      if (!data.action.startsWith('user:') && !data.action.startsWith('plan_received:')) {
        appendLiveVisualFrame({
          type: 'status',
          url: toStatusCardDataUrl(data.action),
          ts,
          label: data.action
        });
      }

      pushMessage({ type: 'action', action: data.action, ts });
      return;
    }

    if (data.type === 'plan') {
      const intents = Array.isArray(data.intent?.intents)
        ? data.intent.intents.filter((x): x is string => typeof x === 'string')
        : [];
      const plan = Array.isArray(data.plan) ? data.plan : [];
      planCursor = -1;
      setCurrentExecutingStep(null);
      setCompletedSteps([]);
      setPlanner(plan, intents);
      pushMessage({
        type: 'action',
        action: `plan_received:${plan.length}_steps`,
        ts
      });
      return;
    }

    if (data.type === 'image') {
      const resolvedUrl =
        (typeof data.url === 'string' && data.url.trim())
          ? data.url.trim()
          : mediaDataUrl(data.data_b64, data.mime_type || 'image/png');

      if (!resolvedUrl) {
        return;
      }

      appendLiveVisualFrame({
        type: 'illustration',
        url: resolvedUrl,
        ts,
        label: 'story illustration'
      });
      pushMessage({ type: 'image', url: resolvedUrl, ts });
      return;
    }

    if (data.type === 'audio') {
      const mime = (typeof data.mime_type === 'string' && data.mime_type.trim()) ? data.mime_type.trim() : 'audio/pcm';
      const resolvedUrl =
        (typeof data.url === 'string' && data.url.trim())
          ? data.url.trim()
          : mediaDataUrl(data.data_b64, mime);

      if (!resolvedUrl) {
        return;
      }

      pushMessage({ type: 'audio', url: resolvedUrl, mime_type: mime, ts });
      return;
    }

    if (data.type === 'video') {
      const resolvedUrl =
        (typeof data.url === 'string' && data.url.trim())
          ? data.url.trim()
          : mediaDataUrl(data.data_b64, data.mime_type || 'video/mp4');

      if (!resolvedUrl) {
        return;
      }

      pushMessage({ type: 'video', url: resolvedUrl, ts });
      return;
    }

    if (data.type === 'text' && typeof data.text === 'string') {
      const text = data.text.trim();
      if (text && !text.toLowerCase().startsWith('navigator:') && !text.toLowerCase().startsWith('interrupt ack:')) {
        setLatestStoryText(text);
      }
    }

    if (data.type === 'transcript' && typeof data.text === 'string') {
      const text = data.text.trim();
      if (text) {
        setLatestStoryText(text);
        pushMessage({ type: 'text', text, ts });
      }
      return;
    }

    pushMessage({ ...(data as StreamMessage), ts });
  };

  ws.onerror = () => {
    socketState.set('error');
    pushMessage({ type: 'action', action: 'socket_error', ts: Date.now() });
  };

  ws.onclose = () => {
    socketState.set('disconnected');
  };

  return ws;
}

export function sendSocketMessage(payload: object): boolean {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    return false;
  }
  resetRunVisuals();
  markPromptSent();
  // Backward compatibility: callers may still send {type:'prompt', text:'...'}.
  if (
    typeof payload === 'object' &&
    payload !== null &&
    'type' in payload &&
    'text' in payload &&
    (payload as { type?: string }).type === 'prompt'
  ) {
    const legacy = payload as { text?: string };
    ws.send(JSON.stringify({ type: 'text', text: legacy.text ?? '' }));
    return true;
  }

  ws.send(JSON.stringify(payload));
  return true;
}

export function sendInterrupt(): boolean {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    return false;
  }
  ws.send(JSON.stringify({ type: 'interrupt' }));
  return true;
}

export function closeSocket(): void {
  if (!ws) {
    return;
  }
  ws.close(1000, 'manual-close');
  ws = null;
  socketState.set('disconnected');
  planCursor = -1;
  setCurrentExecutingStep(null);
  setCompletedSteps([]);
}
