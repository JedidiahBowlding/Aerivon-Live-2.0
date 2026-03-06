# Demonstration Video (Veo) - Judge Ready

This project includes a Veo-based script to produce a real demonstration video under 4 minutes.

## What This Demo Covers

- Real-time live agent behavior (including interruption)
- Agent planning and capability routing
- UI navigation + visual analysis
- Story + illustration + video generation flow
- Security/reliability posture
- Final value pitch

## 1) Prerequisites

Set one of these auth paths:

- Vertex AI path (recommended)
  - `GOOGLE_GENAI_USE_VERTEXAI=true`
  - `GOOGLE_CLOUD_PROJECT=<your-project-id>`
  - `GOOGLE_CLOUD_LOCATION=us-central1`
  - Application Default Credentials configured
- API key path
  - `GEMINI_API_KEY=<your-key>`

Set model:

- `AERIVON_VIDEO_MODEL=veo-3.0-generate-001`

## 2) Generate The Demo

From `Aerivon-Live-2.0`:

```bash
python3 scripts/generate_demo_video_with_veo.py \
  --model "${AERIVON_VIDEO_MODEL:-veo-3.0-generate-001}" \
  --duration-seconds 12 \
  --max-scenes 8 \
  --output-dir demo_video_output
```

This produces:

- `demo_video_output/demo_manifest.json`
- `demo_video_output/clips/scene_*.mp4`
- `demo_video_output/Aerivon_Live_V2_Demo.mp4` (if `ffmpeg` is available)

## 3) Keep Submission Under 4 Minutes

Default output is ~96 seconds (8 scenes x 12s), which is safely below 4 minutes.

## 4) Judge Submission Tip

Upload this final file to the challenge media section or image/video carousel:

- `demo_video_output/Aerivon_Live_V2_Demo.mp4`

If final concat is not available, upload the best single clip from `demo_video_output/clips/`.
