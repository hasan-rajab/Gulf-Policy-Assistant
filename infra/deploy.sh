#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
VERTEX_LOCATION="${VERTEX_LOCATION:-global}"
BQ_LOCATION="${BQ_LOCATION:-US}"
BACKEND_SERVICE="${BACKEND_SERVICE:-nexus-enterprise-ai-api}"
WEB_SERVICE="${WEB_SERVICE:-nexus-enterprise-ai-web}"
WEB_SA="${WEB_SA:-nexus-web}"
BACKEND_SA="${BACKEND_SA:-nexus-backend}"
IAP_MEMBER="${IAP_MEMBER:-}"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/nexus/backend:latest"
WEB_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/nexus/web:latest"

echo "Enabling APIs..."
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com bigquery.googleapis.com iamcredentials.googleapis.com iap.googleapis.com --project "$PROJECT_ID"

gcloud beta services identity create --service=iap.googleapis.com --project="$PROJECT_ID" >/dev/null

gcloud artifacts repositories describe nexus --location "$REGION" --project "$PROJECT_ID" >/dev/null 2>&1 || \
  gcloud artifacts repositories create nexus --repository-format=docker --location "$REGION" --project "$PROJECT_ID"

for SA in "$WEB_SA" "$BACKEND_SA"; do
  gcloud iam service-accounts describe "${SA}@${PROJECT_ID}.iam.gserviceaccount.com" --project "$PROJECT_ID" >/dev/null 2>&1 || \
    gcloud iam service-accounts create "$SA" --project "$PROJECT_ID"
done

# Reference deployment roles. For a real customer environment, scope data
# permissions to the NEXUS dataset/resources rather than the whole project.
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user" >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser" >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor" >/dev/null

# Bootstrap/migrate the governed corpus schema. The separate vector-index DDL in
# infra/bigquery.sql can be applied once corpus size justifies ANN search.
bq --location="$BQ_LOCATION" --project_id="$PROJECT_ID" show "${PROJECT_ID}:enterprise_rag" >/dev/null 2>&1 || \
  bq --location="$BQ_LOCATION" --project_id="$PROJECT_ID" mk --dataset "${PROJECT_ID}:enterprise_rag"

bq --location="$BQ_LOCATION" --project_id="$PROJECT_ID" query --use_legacy_sql=false \
"CREATE TABLE IF NOT EXISTS \`${PROJECT_ID}.enterprise_rag.policy_chunks\` (
 id STRING NOT NULL, document_id STRING NOT NULL, title STRING NOT NULL, text STRING NOT NULL,
 embedding ARRAY<FLOAT64> NOT NULL, chunk_index INT64 NOT NULL, page INT64, language STRING,
 source_uri STRING, metadata STRING, visibility STRING, allowed_roles ARRAY<STRING>,
 allowed_departments ARRAY<STRING>);"

bq --location="$BQ_LOCATION" --project_id="$PROJECT_ID" query --use_legacy_sql=false \
"ALTER TABLE \`${PROJECT_ID}.enterprise_rag.policy_chunks\` ADD COLUMN IF NOT EXISTS visibility STRING;
 ALTER TABLE \`${PROJECT_ID}.enterprise_rag.policy_chunks\` ADD COLUMN IF NOT EXISTS allowed_roles ARRAY<STRING>;
 ALTER TABLE \`${PROJECT_ID}.enterprise_rag.policy_chunks\` ADD COLUMN IF NOT EXISTS allowed_departments ARRAY<STRING>;
 UPDATE \`${PROJECT_ID}.enterprise_rag.policy_chunks\` SET visibility='public' WHERE visibility IS NULL;
 CREATE TABLE IF NOT EXISTS \`${PROJECT_ID}.enterprise_rag.audit_events\` (
   event_id STRING NOT NULL, timestamp TIMESTAMP NOT NULL, actor STRING NOT NULL,
   action STRING NOT NULL, resource STRING, outcome STRING NOT NULL, request_id STRING,
   details STRING, previous_hash STRING, event_hash STRING NOT NULL
 ) PARTITION BY DATE(timestamp) CLUSTER BY actor, action, outcome;"

echo "Building backend..."
gcloud builds submit backend --tag "$BACKEND_IMAGE" --project "$PROJECT_ID"

echo "Deploying private backend..."
gcloud run deploy "$BACKEND_SERVICE" \
  --image "$BACKEND_IMAGE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --service-account "${BACKEND_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --no-allow-unauthenticated \
  --set-env-vars "DEMO_MODE=false,AUTH_MODE=iap,VECTOR_BACKEND=bigquery,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${VERTEX_LOCATION},BQ_DATASET=enterprise_rag,BQ_TABLE=policy_chunks,BQ_AUDIT_TABLE=audit_events,BQ_LOCATION=${BQ_LOCATION},GEMINI_MODEL=gemini-3-flash-preview,EMBEDDING_MODEL=gemini-embedding-001,EMBEDDING_DIMENSIONS=768,ACCESS_PROFILES_JSON={}" \
  --memory 1Gi --cpu 1 --min 0 --max 10

BACKEND_URL="$(gcloud run services describe "$BACKEND_SERVICE" --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')"

gcloud run services add-iam-policy-binding "$BACKEND_SERVICE" \
  --region "$REGION" --project "$PROJECT_ID" \
  --member="serviceAccount:${WEB_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker" >/dev/null

echo "Building web..."
gcloud builds submit frontend --tag "$WEB_IMAGE" --project "$PROJECT_ID"

echo "Deploying IAP-protected web tier..."
gcloud run deploy "$WEB_SERVICE" \
  --image "$WEB_IMAGE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --service-account "${WEB_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --no-allow-unauthenticated \
  --iap \
  --set-env-vars "BACKEND_URL=${BACKEND_URL},GOOGLE_CLOUD_PROJECT=${PROJECT_ID},NEXT_PUBLIC_DEMO_MODE=false,NEXT_PUBLIC_APP_NAME=NEXUS Enterprise AI" \
  --memory 512Mi --cpu 1 --min 0 --max 10

gcloud run services add-iam-policy-binding "$WEB_SERVICE" \
  --region "$REGION" --project "$PROJECT_ID" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com" \
  --role="roles/run.invoker" >/dev/null

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

NEXUS deployment complete.
Web:     ${WEB_URL}
Backend: ${BACKEND_URL} (private)

NEXT:
1. Grant employee/group IAP access (or set IAP_MEMBER before deployment).
2. Populate ACCESS_PROFILES_JSON from a trusted directory for role/department entitlements and knowledge-admin users. The deployment default is public-corpus-only.
3. Apply the vector index in infra/bigquery.sql when corpus size justifies ANN; ACL columns are stored in the index for pre-filtering.
4. Ingest approved documents through a knowledge-admin identity and assign visibility/ACLs.
5. Narrow BigQuery IAM to dataset/resource scope and add customer-specific retention, monitoring, and residency controls.
EOF
