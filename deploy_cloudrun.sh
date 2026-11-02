#!/usr/bin/env bash
# Deploy ONLY the UI + voice backend to Google Cloud Run.
#
# Prerequisite: you have already run the local setup (indices + data + agent
# exist in Elastic). See README -> "Deploy to Google Cloud Run".
#
# Usage:
#   ./deploy_cloudrun.sh <GCP_PROJECT_ID> [REGION] [SERVICE_NAME]
#   e.g. ./deploy_cloudrun.sh my-gcp-project asia-south1 pratham-mitr
#
# Only the runtime secrets (KIBANA_API_KEY, SARVAM_API_KEY) go to Secret Manager.
# ELASTIC_API_KEY / ELASTICSEARCH_URL are NOT needed by the running app.
set -euo pipefail
cd "$(dirname "$0")"

PROJECT="${1:-${GCP_PROJECT:-}}"
REGION="${2:-${GCP_REGION:-asia-south1}}"
SERVICE="${3:-pratham-mitr}"

[ -n "$PROJECT" ] || { echo "Usage: $0 <GCP_PROJECT_ID> [REGION] [SERVICE_NAME]"; exit 1; }
[ -f .env ]       || { echo "❌ No .env found. Complete the local setup first."; exit 1; }
command -v gcloud >/dev/null || { echo "❌ gcloud CLI not installed: https://cloud.google.com/sdk/docs/install"; exit 1; }

# Read a single KEY from .env (no sourcing, so values with special chars are safe)
envval() { { grep -E "^$1=" .env || true; } | tail -1 | cut -d= -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//'; }

for k in KIBANA_URL KIBANA_API_KEY SARVAM_API_KEY; do
  [ -n "$(envval $k)" ] || { echo "❌ $k is missing in .env"; exit 1; }
done

# Deterministic Cloud Run URL -> used as the OAuth redirect base
PROJECT_NUM="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
PUBLIC_URL="https://${SERVICE}-${PROJECT_NUM}.${REGION}.run.app"
GOOGLE_ON=0
if [ -n "$(envval GOOGLE_CLIENT_ID)" ] && [ -n "$(envval GOOGLE_CLIENT_SECRET)" ]; then GOOGLE_ON=1; fi

echo "☁️  Project=$PROJECT  Region=$REGION  Service=$SERVICE"
gcloud config set project "$PROJECT" >/dev/null

echo "🔌 Enabling APIs (first time takes a minute)..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com

# Create or update a secret from a .env value
put_secret() {
  local name="$1" val; val="$(envval "$2")"
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    printf %s "$val" | gcloud secrets versions add "$name" --data-file=- >/dev/null
  else
    printf %s "$val" | gcloud secrets create "$name" --data-file=- --replication-policy=automatic >/dev/null
  fi
}
echo "🔐 Storing secrets in Secret Manager..."
put_secret mitr-kibana-api-key KIBANA_API_KEY
put_secret mitr-sarvam-api-key SARVAM_API_KEY
SECRETS="KIBANA_API_KEY=mitr-kibana-api-key:latest,SARVAM_API_KEY=mitr-sarvam-api-key:latest"
SECRET_NAMES="mitr-kibana-api-key mitr-sarvam-api-key"
if [ "$GOOGLE_ON" = 1 ]; then
  put_secret mitr-google-client-secret GOOGLE_CLIENT_SECRET
  # Session-signing key: generate once, keep stable across redeploys
  if ! gcloud secrets describe mitr-session-secret >/dev/null 2>&1; then
    python3 -c 'import secrets;print(secrets.token_urlsafe(32),end="")' | \
      gcloud secrets create mitr-session-secret --data-file=- --replication-policy=automatic >/dev/null
  fi
  SECRETS="$SECRETS,GOOGLE_CLIENT_SECRET=mitr-google-client-secret:latest,SESSION_SECRET=mitr-session-secret:latest"
  SECRET_NAMES="$SECRET_NAMES mitr-google-client-secret mitr-session-secret"
else
  echo "⚠️  GOOGLE_CLIENT_ID/SECRET not in .env -> deploying WITHOUT login (anyone can use it)"
fi

# Let the Cloud Run runtime service account read them
RUNTIME_SA="${PROJECT_NUM}-compute@developer.gserviceaccount.com"
for s in $SECRET_NAMES; do
  gcloud secrets add-iam-policy-binding "$s" \
    --member="serviceAccount:$RUNTIME_SA" --role=roles/secretmanager.secretAccessor >/dev/null
done

# Non-secret config (written to a temp YAML so values with commas are safe)
ENVFILE="$(mktemp)"; trap 'rm -f "$ENVFILE"' EXIT
for k in KIBANA_URL KIBANA_SPACE_ID AGENT_ID AGENT_INFERENCE_ID \
         SARVAM_STT_MODEL SARVAM_TRANSLATE_MODEL SARVAM_TTS_MODEL \
         SARVAM_TTS_SPEAKER SARVAM_SPEAKER_GENDER ALLOWED_EMAIL_DOMAIN; do
  v="$(envval $k)"; [ -n "$v" ] && printf '%s: "%s"\n' "$k" "$v" >> "$ENVFILE"
done

if [ "$GOOGLE_ON" = 1 ]; then
  printf 'GOOGLE_CLIENT_ID: "%s"\nPUBLIC_URL: "%s"\n' "$(envval GOOGLE_CLIENT_ID)" "$PUBLIC_URL" >> "$ENVFILE"
  echo "🔑 OAuth redirect URI that must be allowed in Google: $PUBLIC_URL/auth/callback"
fi

# Build the image ourselves (Cloud Build -> Artifact Registry) and deploy it with --image.
# `gcloud run deploy --source` auto-creates a "run-sources-*" bucket per region, which
# locked-down orgs reject; this path reuses the project's existing Cloud Build bucket.
REPO="cloud-run-source-deploy"
gcloud artifacts repositories describe "$REPO" --location "$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "$REPO" --repository-format=docker --location "$REGION" >/dev/null
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${SERVICE}:$(date +%Y%m%d-%H%M%S)"
echo "🏗️  Building image $IMAGE ..."
gcloud builds submit . --tag "$IMAGE" --quiet

echo "🚀 Deploying to Cloud Run..."
# max-instances=1 + session affinity: caller->conversation_id map is in memory.
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --allow-unauthenticated \
  --max-instances 1 \
  --session-affinity \
  --memory 512Mi \
  --timeout 120 \
  --env-vars-file "$ENVFILE" \
  --set-secrets "$SECRETS"

echo ""
echo "✅ Deployed: $(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo "   (Cloud Run is HTTPS, so the browser mic works.)"
