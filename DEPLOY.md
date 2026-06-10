# Stodi — Deploy & Cloud Wiring

The code is cloud-ready and **gated by config** — it runs fully offline today
(JSON file store, local corpus grounding) and switches to cloud services when
the matching env vars are set. This file lists the `gcloud` commands for the
infra pieces (they need your GCP project + credentials).

## TL;DR — one-shot deploy

```bash
# once, interactive:
gcloud auth login
gcloud auth application-default login

# then everything (APIs, Firestore, Cloud Run via the Dockerfile, Scheduler):
./deploy.sh
```

> Status (2026-06-11): **LIVE** — https://stodi-api-3cg5degnzq-uc.a.run.app
> Cloud Run (service `stodi-api`) + Firestore (native, us-central1) +
> Cloud Scheduler (`stodi-daily-drip`, 08:00 Africa/Lagos, dry-run gated).
> Note for fresh projects: the default compute SA needs
> `roles/cloudbuild.builds.builder` (build), `roles/aiplatform.user` and
> `roles/datastore.user` (runtime) — deploy.sh's first run surfaces this.

## Environment variables

| Var | Default | What it does |
|-----|---------|--------------|
| `GOOGLE_CLOUD_PROJECT` | `stodi-498317` | GCP project |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | Region |
| `GOOGLE_GENAI_USE_VERTEXAI` | `true` | Use Vertex (vs API key) |
| `GOOGLE_API_KEY` | — | Gemini API key (if not using Vertex) |
| `STODI_MODEL` | `gemini-2.5-flash` | Model id. For **Gemini 3.5 Flash** set `STODI_MODEL=gemini-3.5-flash` AND `GOOGLE_CLOUD_LOCATION=global` (3.x is served via the global endpoint only; us-central1 404s) |
| `STODI_STORE` | `json` | `json` \| `firestore` \| `memory` |
| `STODI_DATA_DIR` | `stodi/data` | Where the JSON store lives |
| `STODI_FIRESTORE_COLLECTION` | `stodi_students` | Firestore collection |
| `VERTEX_SEARCH_DATASTORE` | — | Set to **activate** Vertex AI Search RAG |
| `STODI_DRIP_DRY_RUN` | `true` | `false` to actually send drips |
| `STODI_DRIP_INTERVAL_MINUTES` | `60` | Local poller cadence |
| `TELEGRAM_BOT_TOKEN` | — | Telegram channel |
| `STODI_API_KEY` | — | When set, `/chat` `/switch` `/progress` `/drip` require the `X-API-Key` header (Scheduler sends it automatically via deploy.sh). Protects the public URL from credit-burning. |

## 1. Persistent profiles → Firestore (makes "we remember you" durable at scale)

```bash
gcloud services enable firestore.googleapis.com --project "$GOOGLE_CLOUD_PROJECT"
gcloud firestore databases create --location="$GOOGLE_CLOUD_LOCATION" --project "$GOOGLE_CLOUD_PROJECT"
# Then run with:
export STODI_STORE=firestore
```
No code change — `get_store()` picks Firestore and falls back to JSON if it can't connect.

## 2. Vertex AI Search grounding (the mandatory RAG layer)

```bash
gcloud services enable discoveryengine.googleapis.com --project "$GOOGLE_CLOUD_PROJECT"
# Create a data store in the Agent Builder / Vertex AI Search console,
# import exam_packs/**/past_questions content, then export its resource name:
export VERTEX_SEARCH_DATASTORE="projects/<p>/locations/<l>/collections/default_collection/dataStores/<id>"
```
Once set, `ground_search()` enriches every curriculum search with a grounded
answer. Until set, it uses the local corpus (no over-claiming).

## 3. Deploy the API → Cloud Run

```bash
gcloud run deploy stodi-api \
  --source . \
  --project "$GOOGLE_CLOUD_PROJECT" --region "$GOOGLE_CLOUD_LOCATION" \
  --allow-unauthenticated \
  --set-env-vars "STODI_STORE=firestore,GOOGLE_GENAI_USE_VERTEXAI=true,STODI_DRIP_DRY_RUN=false"
# Entry point: uvicorn stodi.core.api:app --host 0.0.0.0 --port $PORT
```
The Quasar/Vue client points at this URL: `POST /chat`, `GET /progress/{id}`, `POST /switch`.

## 4. Autonomous drips → Cloud Scheduler

```bash
gcloud services enable cloudscheduler.googleapis.com --project "$GOOGLE_CLOUD_PROJECT"
gcloud scheduler jobs create http stodi-daily-drip \
  --project "$GOOGLE_CLOUD_PROJECT" --location "$GOOGLE_CLOUD_LOCATION" \
  --schedule "0 8 * * *" --time-zone "Africa/Lagos" \
  --uri "https://<your-cloud-run-url>/drip" --http-method POST
```

## Local dev

```bash
# Telegram bot (channel):
PYTHONPATH=.. python -m stodi.telegram_bot
# API (for the Quasar app):
PYTHONPATH=.. uvicorn stodi.core.api:app --reload --port 8080
# Tests:
PYTHONPATH=.. STODI_STORE=memory pytest stodi/tests/ -q
```
