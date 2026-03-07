#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   PROJECT_ID=... \
#   SERVICE_ACCOUNT=... \
#   MEMORY_BUCKET=... \
#   ./scripts/deploy_cloud_build.sh

PROJECT_ID="${PROJECT_ID:-}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-}"
MEMORY_BUCKET="${MEMORY_BUCKET:-}"
REGION="${REGION:-us-central1}"
BACKEND_SERVICE="${BACKEND_SERVICE:-aerivon-live-agent}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-aerivon-live-frontend}"
VIDEO_MODEL="${VIDEO_MODEL:-veo-3.1-generate-001}"

if [[ -z "${PROJECT_ID}" || -z "${SERVICE_ACCOUNT}" || -z "${MEMORY_BUCKET}" ]]; then
  echo "Missing required env vars."
  echo "Required: PROJECT_ID, SERVICE_ACCOUNT, MEMORY_BUCKET"
  echo "Optional: REGION, BACKEND_SERVICE, FRONTEND_SERVICE, VIDEO_MODEL"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "Submitting Cloud Build for Aerivon-Live-2.0..."

gcloud builds submit \
  --project "${PROJECT_ID}" \
  --config cloudbuild.yaml \
  --substitutions "_PROJECT_ID=${PROJECT_ID},_SERVICE_ACCOUNT=${SERVICE_ACCOUNT},_MEMORY_BUCKET=${MEMORY_BUCKET},_REGION=${REGION},_BACKEND_SERVICE=${BACKEND_SERVICE},_FRONTEND_SERVICE=${FRONTEND_SERVICE},_VIDEO_MODEL=${VIDEO_MODEL}" \
  .

echo "Build submitted successfully."
