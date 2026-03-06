# Deploy Guide (Cloud Build + Cloud Run)

This guide shows how to deploy `Aerivon-Live-2.0` with `cloudbuild.yaml`, including a GitHub trigger for auto-deploys on `main`.

## Prerequisites

- `gcloud` CLI authenticated
- Cloud Build, Cloud Run, Artifact Registry, and IAM APIs enabled
- A deploy service account with permissions for Cloud Run and builds
- Repo connected to Cloud Build GitHub integration

Required values:

- `PROJECT_ID`
- `SERVICE_ACCOUNT`
- `MEMORY_BUCKET`
- Optional: `REGION` (default `us-central1`)

## 1) Manual Deploy (single command)

```bash
cd /Users/blockdev/Downloads/aerivon-2.0/Aerivon-Live-2.0

PROJECT_ID="your-project-id" \
SERVICE_ACCOUNT="your-service-account@your-project.iam.gserviceaccount.com" \
MEMORY_BUCKET="your-memory-bucket" \
./scripts/deploy_cloud_build.sh
```

## 2) Create Main-Branch Auto-Deploy Trigger (GitHub)

Replace placeholders as needed, then run:

```bash
gcloud builds triggers create github \
  --project "your-project-id" \
  --name "aerivon-live-2-main-deploy" \
  --repo-owner "your-github-owner" \
  --repo-name "your-github-repo" \
  --branch-pattern "^main$" \
  --build-config "cloudbuild.yaml" \
  --substitutions "_PROJECT_ID=your-project-id,_SERVICE_ACCOUNT=your-service-account@your-project.iam.gserviceaccount.com,_MEMORY_BUCKET=your-memory-bucket,_REGION=us-central1,_BACKEND_SERVICE=aerivon-live-agent,_FRONTEND_SERVICE=aerivon-live-frontend,_VIDEO_MODEL=veo-3.0-generate-001"
```

Repo-specific example (based on this repo remote):

```bash
gcloud builds triggers create github \
  --project "your-project-id" \
  --name "aerivon-live-2-main-deploy" \
  --repo-owner "JedidiahBowlding" \
  --repo-name "Aerivon-Live-2.0" \
  --branch-pattern "^main$" \
  --build-config "cloudbuild.yaml" \
  --substitutions "_PROJECT_ID=your-project-id,_SERVICE_ACCOUNT=your-service-account@your-project.iam.gserviceaccount.com,_MEMORY_BUCKET=your-memory-bucket,_REGION=us-central1,_BACKEND_SERVICE=aerivon-live-agent,_FRONTEND_SERVICE=aerivon-live-frontend,_VIDEO_MODEL=veo-3.0-generate-001"
```

## 3) Trigger a Manual Run From Existing Trigger

```bash
gcloud builds triggers run "aerivon-live-2-main-deploy" \
  --project "your-project-id" \
  --branch "main"
```

## 4) Verify Deployments

```bash
gcloud run services list --project "your-project-id" --region "us-central1"

gcloud run services describe aerivon-live-agent \
  --project "your-project-id" \
  --region "us-central1" \
  --format='value(status.url)'

gcloud run services describe aerivon-live-frontend \
  --project "your-project-id" \
  --region "us-central1" \
  --format='value(status.url)'
```

## Notes

- `cloudbuild.yaml` deploys backend first, then injects backend URL into frontend via `VITE_AERIVON_API_URL`.
- Veo model defaults to `veo-3.0-generate-001` via `_VIDEO_MODEL` substitution.
