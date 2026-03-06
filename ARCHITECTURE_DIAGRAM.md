# Aerivon Live V2 - Architecture Diagram

This diagram shows how the frontend, backend, Gemini models, tools, and memory services interact.

## System Diagram

```mermaid
flowchart LR
  U[User]
  F[Frontend\nSvelteKit + Vite\nWebSocket UI]
  B[Backend API\nFastAPI + WebSocket\nAgent Orchestrator]
  A[Agent Runtime\nTool Firewall + Guardrails]
  G[Gemini via Vertex AI\nLive API primary\nFlash fallback]
  T[Tool Runtime\nPlaywright + extraction/generation tools]
  M[(Session Memory\nGCS or Firestore)]
  C[(Cloud Run Deployment)]

  U --> F
  F -->|prompt/audio/events| B
  B --> A
  A -->|model requests| G
  G -->|streamed responses/tool calls| A
  A -->|validated tool calls| T
  T -->|tool results| A
  A -->|append/load memory| M
  A --> B
  B -->|text/image/audio/video/action stream| F
  B -. deployed on .-> C
```

## Data Flow Summary

1. User interacts with the Svelte frontend.
2. Frontend streams requests to FastAPI over WebSocket.
3. Backend invokes Aerivon agent runtime.
4. Agent uses Gemini Live on Vertex AI (with fallback to Gemini Flash).
5. If tools are needed, the tool firewall validates and executes allowed tools.
6. Session memory is loaded/saved through GCS or Firestore.
7. Backend streams multimodal results back to the frontend for live display.

## Judge Quick Access

- Primary diagram file: `ARCHITECTURE_DIAGRAM.md`
- Project summary file: `PROJECT_TEXT_DESCRIPTION.md`
- Backend architecture details: `backend/ARCHITECTURE.md`
