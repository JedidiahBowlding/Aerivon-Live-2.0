# Aerivon Live V2 - Project Summary

## 1. Project Features and Functionality

Aerivon Live V2 is a multimodal AI agent system designed for the Gemini Live Agent Challenge. It combines real-time interaction, autonomous tool use, and an operator-style frontend to support practical agent workflows.

Core functionality includes:

- Real-time WebSocket interaction between client and backend for streaming events
- Multimodal handling across text, image, audio, video, and action events
- Autonomous agent turn execution with bounded tool-calling loops
- Tool firewall controls (allowlist, argument validation, relevance checks, call caps)
- Prompt injection and unsafe host protections (including SSRF-style blocking)
- Retry with exponential backoff for transient upstream model errors
- Session memory persistence with cloud-backed storage options
- Frontend timeline and step-tracking UI for agent visibility
- Browser-state and visual-frame streaming in the interface
- User interrupt support for live runs

The backend exposes health and agent endpoints and orchestrates Gemini model interaction plus tool execution. The frontend acts as a live cockpit showing runtime state, planner steps, and streamed outputs.

## 2. Technologies Used

### Backend

- Python
- FastAPI (API + WebSocket server)
- Uvicorn
- Google GenAI SDK (`google-genai`)
- Vertex AI integration for Gemini model access
- Playwright for browsing/screenshot-oriented tooling
- Google Cloud Storage and optional Firestore integration for memory

### Frontend

- SvelteKit + TypeScript
- Vite
- Tailwind CSS
- GSAP (UI animation)
- Three.js (visual/graphics capability)
- Store-based state management via Svelte stores

### Cloud / Platform

- Google Cloud Run for deployment
- Vertex AI for Gemini model access
- Google Cloud Storage (memory persistence)
- Optional Firestore memory path

## 3. Data Sources Used

Primary data sources in this project are operational and runtime-driven, rather than static datasets:

- User-provided inputs (prompt text and optional media)
- Model responses from Gemini Live / fallback Gemini Flash paths
- Web content retrieved through controlled browsing tools when agent tasks require it
- Session memory records persisted per user/session scope in cloud storage

No large external training dataset is bundled in this repository. The system works on live interaction data plus web/runtime retrieval.

## 4. Findings and Learnings

Key learnings from implementation and integration:

- Real-time agent systems need strong guardrails by default. Tool allowlists, bounded calls, and argument checks are essential for reliable autonomous behavior.
- Network and upstream model instability are normal in live systems; retry strategies and reconnection logic significantly improve user experience.
- Separating untrusted tool output from model instructions reduces prompt-injection risk in agent loops.
- Session-scoped memory improves continuity, but should be capped/trimmed to control token and cost growth.
- A visible execution timeline in the frontend makes debugging, demos, and judge evaluation much easier.
- Keeping generated artifacts and environment folders out of version control is important for security and repository maintainability.

## 5. Current V2 Outcome

Aerivon Live V2 now includes both backend and frontend in one repo, with project-level ignore rules to protect sensitive files and keep push size manageable. The result is a cleaner, challenge-ready codebase with improved portability, traceability, and deployment alignment.

## 6. Judge Quick Links

- Architecture diagram: `ARCHITECTURE_DIAGRAM.md`
- Backend architecture deep dive: `backend/ARCHITECTURE.md`
- Project summary (this file): `PROJECT_TEXT_DESCRIPTION.md`
- Deployment guide (Cloud Build/Run): `DEPLOY.md`
