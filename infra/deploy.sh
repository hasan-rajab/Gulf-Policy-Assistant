#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
VERTEX_LOCATION="${VERTEX_LOCATION:-global}"
BQ_LOCATION="${BQ_LOCATION:-US}"
BACKEND_SERVICE="${BACKEND_SERVICE:-gcc-policy-rag-api}"
WEB_SERVICE="${WEB_SERVICE:-gcc-policy-rag-web}"
WEB_SA="${WEB_SA:-gcc-rag-web}"
BACKEND_SA="${BACKEND_SA:-gcc-rag-backend}"
IAP_MEMBER="${IAP_MEMBER:-}"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/gcc-rag/backend:latest"
WEB_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/gcc-rag/web:latest"

echo "Enabling APIs..."
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com bigquery.googleapis.com iamcredentials.googleapis.com iap.googleapis.com --project "$PROJECT_ID"

# Ensure the IAP service agent exists before binding Cloud Run Invoker.
gcloud beta services identity create --service=iap.googleapis.com --project="$PROJECT_ID" >/dev/null

gcloud artifacts repositories describe gcc-rag --location "$REGION" --project "$PROJECT_ID" >/dev/null 2>&1 || \
  gcloud artifacts repositories create gcc-rag --repository-format=docker --location "$REGION" --project "$PROJECT_ID"

for SA in "$WEB_SA" "$BACKEND_SA"; do
  gcloud iam service-accounts describe "${SA}@${PROJECT_ID}.iam.gserviceaccount.com" --project "$PROJECT_ID" >/dev/null 2>&1 || \
    gcloud iam service-accounts create "$SA" --project "$PROJECT_ID"
done

# Prototype permissions. In production, narrow data access to the required dataset/resources.
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user" >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser" >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor" >/dev/null

# Bootstrap BigQuery with bq for portability.
bq --location="$BQ_LOCATION" --project_id="$PROJECT_ID" show "${PROJECT_ID}:enterprise_rag" >/dev/null 2>&1 || \
  bq --location="$BQ_LOCATION" --project_id="$PROJECT_ID" mk --dataset "${PROJECT_ID}:enterprise_rag"
bq --location="$BQ_LOCATION" --project_id="$PROJECT_ID" query --use_legacy_sql=false \
"CREATE TABLE IF NOT EXISTS \`${PROJECT_ID}.enterprise_rag.policy_chunks\` (
 id STRING NOT NULL, document_id STRING NOT NULL, title STRING NOT NULL, text STRING NOT NULL,
 embedding ARRAY<FLOAT64> NOT NULL, chunk_index INT64 NOT NULL, page INT64, language STRING,
 source_uri STRING, metadata STRING);"

echo "Building backend..."
gcloud builds submit backend --tag "$BACKEND_IMAGE" --project "$PROJECT_ID"

echo "Deploying private backend..."
gcloud run deploy "$BACKEND_SERVICE" \
  --image "$BACKEND_IMAGE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --service-account "${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --no-allow-unauthenticated \
  --set-env-vars "DEMO_MODE=false,AUTH_MODE=iap,VECTOR_BACKEND=bigquery,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${VERTEX_LOCATION},BQ_DATASET=enterprise_rag,BQ_TABLE=policy_chunks,BQ_LOCATION=${BQ_LOCATION},GEMINI_MODEL=gemini-3-flash-preview,EMBEDDING_MODEL=gemini-embedding-001,EMBEDDING_DIMENSIONS=768" \
  --memory 1Gi --cpu 1 --min 0 --max 10

BACKEND_URL="$(gcloud run services describe "$BACKEND_SERVICE" --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')"

gcloud run services add-iam-policy-binding "$BACKEND_SERVICE" \
  --region "$REGION" --project "$PROJECT_ID" \
  --member="serviceAccount:${WEB_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker" >/dev/null

echo "Building web..."
gcloud builds submit frontend --tag "$WEB_IMAGE" --project "$PROJECT_ID"

echo "Deploying web tier..."
gcloud run deploy "$WEB_SERVICE" \
  --image "$WEB_IMAGE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --service-account "${WEB_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --no-allow-unauthenticated \
  --iap \
  --set-env-vars "BACKEND_URL=${BACKEND_URL},GOOGLE_CLOUD_PROJECT=${PROJECT_ID},NEXT_PUBLIC_DEMO_MODE=false,NEXT_PUBLIC_APP_NAME=Gulf Horizon Policy Assistant" \
  --memory 512Mi --cpu 1 --min 0 --max 10

# Direct IAP on Cloud Run requires the IAP service agent to invoke the service.
gcloud run services add-iam-policy-binding "$WEB_SERVICE" \
  --region "$REGION" --project "$PROJECT_ID" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com" \
  --role="roles/run.invoker" >/dev/null

# Optional: grant an employee/group access during deployment, e.g.
# IAP_MEMBER="group:ai-demo@yourcompany.com" bash infra/deploy.sh
if [[ -n "$IAP_MEMBER" ]]; then
  gcloud iap web add-iam-policy-binding \
    --resource-type=cloud-run \
    --service="$WEB_SERVICE" \
    --region="$REGION" \
    --member="$IAP_MEMBER" \
    --role="roles/iap.httpsResourceAccessor" \
    --project="$PROJECT_ID" >/dev/null
fi

WEB_URL="$(gcloud run services describe "$WEB_SERVICE" --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')"
cat <<EOF

Deployment complete.
Web:     ${WEB_URL}
Backend: ${BACKEND_URL} (private)

NEXT:
1. Grant employees/groups IAP access (or set IAP_MEMBER before running this script).
2. Ingest approved documents from an authenticated admin environment.
3. Create the vector index in infra/bigquery.sql when corpus size justifies ANN.
4. Move secrets/config to Secret Manager and add retention/monitoring policies.
EOF
