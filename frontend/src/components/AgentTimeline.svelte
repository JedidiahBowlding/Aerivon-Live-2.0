<script lang="ts">
  import { onDestroy } from 'svelte';
  import type { PlannerStep } from '$lib/agentStore';

  export let steps: string[] = [];
  export let plannedSteps: PlannerStep[] = [];
  export let intents: string[] = [];
  export let currentExecutingStepId: number | null = null;
  export let completedStepIds: number[] = [];
  export let runCompletedAt: number | null = null;

  let previousCompletedIds: number[] = [];
  let pulseStepIds: number[] = [];
  const clearTimers = new Map<number, ReturnType<typeof setTimeout>>();

  function statusFor(step: PlannerStep): 'completed' | 'current' | 'pending' {
    if (currentExecutingStepId === step.id) {
      return 'current';
    }
    if (completedStepIds.includes(step.id)) {
      return 'completed';
    }
    return 'pending';
  }

  function triggerPulse(stepId: number): void {
    if (pulseStepIds.includes(stepId)) {
      return;
    }

    pulseStepIds = [...pulseStepIds, stepId];
    const timer = setTimeout(() => {
      pulseStepIds = pulseStepIds.filter((id) => id !== stepId);
      clearTimers.delete(stepId);
    }, 700);
    clearTimers.set(stepId, timer);
  }

  $: {
    const newlyCompleted = completedStepIds.filter((id) => !previousCompletedIds.includes(id));
    newlyCompleted.forEach(triggerPulse);
    previousCompletedIds = [...completedStepIds];
  }

  onDestroy(() => {
    clearTimers.forEach((timer) => clearTimeout(timer));
    clearTimers.clear();
  });
</script>

<section class="glass-panel p-4 md:p-5">
  <div class="mb-4 flex items-center justify-between">
    <h2 class="panel-title text-sm uppercase tracking-[0.18em] text-cyan-200">Agent Timeline</h2>
    <span class="text-xs text-cyan-100/70">Live Reasoning</span>
  </div>

  <ol class="space-y-3">
    {#each steps as step, i}
      <li class="relative flex items-center gap-3 rounded-lg border border-cyan-300/15 bg-slate-950/45 px-3 py-2">
        <span class="inline-flex h-6 w-6 items-center justify-center rounded-full border border-cyan-300/30 text-xs text-cyan-200">
          {i + 1}
        </span>
        <span class="neon-label text-sm">{step}</span>
      </li>
    {/each}
  </ol>

  <div class="mt-5 border-t border-cyan-300/15 pt-4">
    <div class="mb-3 flex items-center justify-between">
      <h3 class="panel-title text-xs uppercase tracking-[0.18em] text-cyan-200/90">Execution Plan</h3>
      <span class="text-[11px] text-cyan-100/60">From planner event</span>
    </div>

    {#if intents.length > 0}
      <p class="mb-3 text-xs text-cyan-100/70">Intent: {intents.join(', ')}</p>
    {/if}

    {#if plannedSteps.length === 0}
      <p class="text-xs text-cyan-100/60">Waiting for planner output...</p>
    {:else}
      {#if runCompletedAt}
        <div class="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-300/65 bg-emerald-300/10 px-3 py-1 text-[11px] uppercase tracking-[0.12em] text-emerald-100">
          <span class="inline-block h-1.5 w-1.5 rounded-full bg-emerald-200"></span>
          Run Completed
        </div>
      {/if}
      <ol class="space-y-2">
        {#each plannedSteps as step}
          {@const status = statusFor(step)}
          {@const shouldPulse = pulseStepIds.includes(step.id)}
          <li
            class={`rounded-lg px-3 py-2 text-xs transition ${
              status === 'current'
                ? 'border border-emerald-300/70 bg-emerald-300/10 text-emerald-100 shadow-[0_0_22px_rgba(47,242,201,0.25)]'
                : status === 'completed'
                  ? 'border border-cyan-300/35 bg-cyan-300/10 text-cyan-100/90'
                  : 'border border-cyan-300/15 bg-slate-950/40 text-cyan-100/85'
            } ${shouldPulse ? 'progress-pulse' : ''}`}
          >
            <div class="flex items-center justify-between gap-3">
              <span>{step.id}. {step.capability} -> {step.action}</span>
              {#if status === 'current'}
                <span class="rounded-full border border-emerald-300/70 px-2 py-0.5 text-[10px] uppercase tracking-[0.16em] text-emerald-100">
                  Executing
                </span>
              {:else if status === 'completed'}
                <span class="rounded-full border border-cyan-300/55 px-2 py-0.5 text-[10px] uppercase tracking-[0.16em] text-cyan-100">
                  Completed
                </span>
              {:else}
                <span class="rounded-full border border-cyan-300/25 px-2 py-0.5 text-[10px] uppercase tracking-[0.16em] text-cyan-100/70">
                  Pending
                </span>
              {/if}
            </div>
          </li>
        {/each}
      </ol>
    {/if}
  </div>
</section>

<style>
  .progress-pulse {
    animation: progress-pulse 680ms ease-out;
  }

  @keyframes progress-pulse {
    0% {
      transform: translateY(0) scale(1);
      box-shadow: 0 0 0 rgba(94, 196, 255, 0);
    }
    35% {
      transform: translateY(-1px) scale(1.01);
      box-shadow: 0 0 26px rgba(94, 196, 255, 0.35);
    }
    100% {
      transform: translateY(0) scale(1);
      box-shadow: 0 0 0 rgba(94, 196, 255, 0);
    }
  }
</style>
