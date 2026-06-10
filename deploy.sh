#!/usr/bin/env bash
# Stodi — one-shot Google Cloud deploy.
#
# Prereqs (interactive, run once):
#   gcloud auth login
#   gcloud auth application-default login
#
# Then:  ./deploy.sh
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:=stodi-498317}"
: "${GOOGLE_CLOUD_LOCATION:=us-central1}"
SERVICE=stodi-api

if ! gcloud auth print-access-token >/dev/null 2>&1; then
  echo "✗ Not authenticated. Run:"
  echo "    gcloud auth login && gcloud auth application-default login"
  exit 1
fi

echo "→ Project: $GOOGLE_CLOUD_PROJECT ($GOOGLE_CLOUD_LOCATION)"
gcloud config set project "$GOOGLE_CLOUD_PROJECT" --quiet

echo "→ Enabling APIs (idempotent)"
gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  firestore.googleapis.com cloudscheduler.googleapis.com \
  aiplatform.googleapis.com discoveryengine.googleapis.com --quiet

echo "→ Firestore database (no-op if it exists)"
gcloud firestore databases create --location="$GOOGLE_CLOUD_LOCATION" --quiet 2>/dev/null \
  || echo "  (already exists)"

echo "→ Deploying $SERVICE to Cloud Run"
ENV_VARS="STODI_STORE=firestore,GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION,STODI_DRIP_DRY_RUN=true"
# API-key gate for credit-spending routes (set STODI_API_KEY before running)
if [ -n "${STODI_API_KEY:-}" ]; then
  ENV_VARS="$ENV_VARS,STODI_API_KEY=$STODI_API_KEY"
fi

gcloud run deploy "$SERVICE" \
  --source . \
  --region "$GOOGLE_CLOUD_LOCATION" \
  --allow-unauthenticated \
  --memory 1Gi \
  --set-env-vars "$ENV_VARS" \
  --quiet

URL=$(gcloud run services describe "$SERVICE" --region "$GOOGLE_CLOUD_LOCATION" --format='value(status.url)')

echo "→ Cloud Scheduler drip job (08:00 Africa/Lagos)"
HDR=()
if [ -n "${STODI_API_KEY:-}" ]; then HDR=(--headers "X-API-Key=$STODI_API_KEY"); fi
gcloud scheduler jobs create http stodi-daily-drip \
  --location "$GOOGLE_CLOUD_LOCATION" \
  --schedule "0 8 * * *" --time-zone "Africa/Lagos" \
  --uri "$URL/drip" --http-method POST "${HDR[@]}" --quiet 2>/dev/null \
  || gcloud scheduler jobs update http stodi-daily-drip \
       --location "$GOOGLE_CLOUD_LOCATION" --uri "$URL/drip" \
       ${STODI_API_KEY:+--update-headers "X-API-Key=$STODI_API_KEY"} --quiet

echo "→ Smoke test"
curl -fsS "$URL/health" && echo

echo
echo "✓ Deployed: $URL"
echo "  Next (optional):"
echo "  - Vertex AI Search: create a data store in Agent Builder, import the"
echo "    exam-pack corpus, then redeploy with VERTEX_SEARCH_DATASTORE=<resource-name>"
echo "  - Flip drips live: redeploy with STODI_DRIP_DRY_RUN=false"
echo "  - Telegram bot: run separately with TELEGRAM_BOT_TOKEN set (long-polling):"
echo "      PYTHONPATH=.. python -m stodi.telegram_bot"
