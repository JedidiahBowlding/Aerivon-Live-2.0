# Aerivon Live V2

Aerivon Live V2 is a multimodal agent system for the Gemini Live Agent Challenge. It combines:

- Live voice interaction
- Voice interruption with explicit interrupt acknowledgment
- UI navigation and visual analysis
- Story and illustration generation
- Veo-powered video generation with fast preview + job status streaming

This README is written for judges to run and deploy quickly.

## What Judges Can Verify

- Voice prompt ingestion and interruption handling
- Visible interrupt acknowledgment in UI logs and timeline reset to listening
- Agent planning/action timeline
- Website exploration + visual reasoning
- Auto-triggered Veo video generation from voice/text prompts (including fast preview)
- End-to-end backend/frontend deployment on Google Cloud Run

## Repo Structure

- `backend/` - FastAPI backend, WebSocket endpoints, Veo job APIs
- `frontend/` - SvelteKit UI (timeline, stream, Veo panel)
- `cloudbuild.yaml` - Cloud Build pipeline for backend + frontend deploy
- `scripts/deploy_cloud_build.sh` - one-command deployment wrapper
- `ARCHITECTURE_DIAGRAM.md` - system architecture diagram
- `PROJECT_TEXT_DESCRIPTION.md` - project summary for submission
- `DEMONSTRATION_VIDEO.md` - Veo demo video generation notes

## Prerequisites

- Google Cloud project with billing enabled
- `gcloud` CLI authenticated
- Access to Vertex AI models used by the app
- Cloud APIs enabled: Cloud Build, Cloud Run, Artifact Registry, Vertex AI
- Deploy service account with Cloud Run deploy permissions

## Local Run (Quick)

### Backend

```bash
cd backend
pip install -r requirements.txt

export GOOGLE_GENAI_USE_VERTEXAI=True
export GOOGLE_CLOUD_PROJECT="<your-project-id>"
export GOOGLE_CLOUD_LOCATION="us-central1"
export AERIVON_MEMORY_BUCKET="<your-memory-bucket>"
export AERIVON_VIDEO_MODEL="veo-3.1-generate-001"

uvicorn server:app --host 0.0.0.0 --port 8081
```

### Frontend

```bash
cd frontend
npm install

# Optional, but recommended for local explicit config
export VITE_AERIVON_API_URL="http://localhost:8081"
export VITE_AERIVON_WS_URL="ws://localhost:8081/ws/live"

npm run dev -- --host 0.0.0.0 --port 5173
```

Open the frontend in your browser and test voice + Veo generation.

## Deploy to Google Cloud Run (Recommended)

The repository includes a working Cloud Build pipeline.

### 1) Configure environment values

Required:

- `PROJECT_ID`
- `SERVICE_ACCOUNT`
- `MEMORY_BUCKET`

Optional:

- `REGION` (default `us-central1`)
- `BACKEND_SERVICE` (default `aerivon-live-agent`)
- `FRONTEND_SERVICE` (default `aerivon-live-frontend`)
- `VIDEO_MODEL` (default `veo-3.1-generate-001`)
- `AERIVON_VEO_PARALLELISM` (default 3, bounded in backend)

### 2) Run deployment

```bash
cd /path/to/Aerivon-Live-2.0

PROJECT_ID="<your-project-id>" \
SERVICE_ACCOUNT="<deploy-sa>@<project>.iam.gserviceaccount.com" \
MEMORY_BUCKET="<your-memory-bucket>" \
REGION="us-central1" \
./scripts/deploy_cloud_build.sh
```

### 3) Verify services

```bash
gcloud run services describe aerivon-live-agent \
  --project "<your-project-id>" \
  --region us-central1 \
  --format='value(status.url,status.latestReadyRevisionName)'

gcloud run services describe aerivon-live-frontend \
  --project "<your-project-id>" \
  --region us-central1 \
  --format='value(status.url,status.latestReadyRevisionName)'
```

## Deployed Endpoints (Current)

- Frontend: `https://aerivon-live-frontend-oauob6cvnq-uc.a.run.app`
- Backend: `https://aerivon-live-agent-oauob6cvnq-uc.a.run.app`

## Key Backend Endpoints

- `GET /health`
- `WS /ws/live` (main frontend stream)
- `POST /veo/jobs` (start Veo generation)
- `GET /veo/jobs/{job_id}` (status)
- `WS /ws/veo/{job_id}` (live job status updates)
- `GET /veo/jobs/{job_id}/preview` (early preview when `fast_preview=true`)
- `GET /veo/jobs/{job_id}/video` (generated video file)

## Interrupt Behavior

- User can interrupt via the `Interrupt` button or by hands-free barge-in while the agent is speaking.
- Backend sends `{"type":"interrupted","source":"client"}` when an interrupt is received.
- Frontend surfaces this as `interrupt_ack:<source>` in action logs and immediately returns timeline state to `Listening`.

## Fast Veo Preview

- Submit Veo jobs with `fast_preview=true` for earlier visual feedback.
- While status is `running`, `preview_video_url` may become available before final completion.
- Final output remains available at `/veo/jobs/{job_id}/video` when status reaches `completed`.

## Example Judge Prompts

- "Open nike.com, analyze what you see, and create an illustration cinematic video concept."
- "Browse apple.com and generate a short cinematic video summary."
- "Visit tesla.com, extract themes, and render a marketing video concept."

## Troubleshooting

- `socket_not_ready_veo_fallback`:
  - Main story socket was not ready, but Veo generation fallback was triggered.
- Build permission errors:
  - Ensure active `gcloud` account has Cloud Build + Cloud Run deploy permissions.
- Veo model access errors:
  - Confirm project has access to selected Veo model (`AERIVON_VIDEO_MODEL`).

## Submission Docs

- `ARCHITECTURE_DIAGRAM.md`
- `PROJECT_TEXT_DESCRIPTION.md`
- `DEMONSTRATION_VIDEO.md`
- `DEPLOY.md`
