#!/usr/bin/env bash
# =============================================================================
# deploy-gcp.sh — Automated GCP Deployment for Booker App
# =============================================================================
# Usage:
#   1. Copy .env.gcp.example to .env.gcp and fill in your values
#   2. Authenticate: gcloud auth login && gcloud auth application-default login
#   3. Run: bash deploy-gcp.sh
#
# Prerequisites:
#   - gcloud CLI installed (https://cloud.google.com/sdk/docs/install)
#   - Docker installed and running
#   - A GCP project with billing enabled
# =============================================================================
set -euo pipefail

# ─── Load Configuration ──────────────────────────────────────────────────────
# Source environment variables from .env.gcp (create from .env.gcp.example)
if [[ -f .env.gcp ]]; then
    set -a
    source .env.gcp
    set +a
else
    echo "❌ .env.gcp not found. Copy .env.gcp.example to .env.gcp and fill in values."
    exit 1
fi

# ─── Required Variables (with defaults) ──────────────────────────────────────
GCP_PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID in .env.gcp}"
GCP_REGION="${GCP_REGION:-us-central1}"
GCP_ZONE="${GCP_ZONE:-us-central1-a}"

# Artifact Registry
AR_REPO_NAME="${AR_REPO_NAME:-booker-app}"

# Cloud SQL
DB_INSTANCE_NAME="${DB_INSTANCE_NAME:-booker-db}"
DB_NAME="${DB_NAME:-booker}"
DB_USER="${DB_USER:-booker_admin}"
DB_PASSWORD="${DB_PASSWORD:?Set DB_PASSWORD in .env.gcp}"

# Cloud Run
SERVICE_NAME="${SERVICE_NAME:-booker-api}"
IMAGE_NAME="${SERVICE_NAME}"
CONTAINER_PORT="${CONTAINER_PORT:-8080}"

# Django
DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:?Set DJANGO_SECRET_KEY in .env.gcp}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          Booker App — GCP Deployment Script                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Project:      ${GCP_PROJECT_ID}"
echo "  Region:       ${GCP_REGION}"
echo "  AR Repo:      ${AR_REPO_NAME}"
echo "  SQL Instance: ${DB_INSTANCE_NAME}"
echo "  Service:      ${SERVICE_NAME}"
echo ""

# ─── Step 0: Set GCP Project ─────────────────────────────────────────────────
echo "▸ Setting GCP project..."
gcloud config set project "${GCP_PROJECT_ID}"

# ─── Step 1: Enable Required APIs ────────────────────────────────────────────
echo ""
echo "▸ Enabling GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    iam.googleapis.com

echo "  ✅ APIs enabled"

# ─── Step 2: Create Artifact Registry Repository ─────────────────────────────
echo ""
echo "▸ Creating Artifact Registry repository..."
if gcloud artifacts repositories describe "${AR_REPO_NAME}" \
    --location="${GCP_REGION}" --format="value(name)" 2>/dev/null; then
    echo "  ℹ️  Repository already exists, skipping creation"
else
    gcloud artifacts repositories create "${AR_REPO_NAME}" \
        --repository-format=docker \
        --location="${GCP_REGION}" \
        --description="Booker Docker images"
    echo "  ✅ Repository created"
fi

# Configure Docker for Artifact Registry
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet

# ─── Step 3: Create Cloud SQL PostgreSQL Instance ─────────────────────────────
echo ""
echo "▸ Provisioning Cloud SQL PostgreSQL instance..."
if gcloud sql instances describe "${DB_INSTANCE_NAME}" \
    --format="value(name)" 2>/dev/null; then
    echo "  ℹ️  Instance already exists, skipping creation"
else
    gcloud sql instances create "${DB_INSTANCE_NAME}" \
        --database-version=POSTGRES_16 \
        --tier=db-f1-micro \
        --region="${GCP_REGION}" \
        --availability-type=regional \
        --storage-type=SSD \
        --storage-size=10GB \
        --storage-auto-increase \
        --backup-start-time=03:00 \
        --enable-bin-log \
        --maintenance-window-day=SUN \
        --maintenance-window-hour=04 \
        --no-assign-ip \
        --network=default \
        --require-ssl

    echo "  ✅ Cloud SQL instance created (this may take 5-10 minutes)"
fi

# ─── Step 4: Create Database and User ────────────────────────────────────────
echo ""
echo "▸ Configuring database and user..."
# Create database (ignore error if exists)
gcloud sql databases create "${DB_NAME}" \
    --instance="${DB_INSTANCE_NAME}" 2>/dev/null || echo "  ℹ️  Database '${DB_NAME}' already exists"

# Create user (ignore error if exists)
gcloud sql users create "${DB_USER}" \
    --instance="${DB_INSTANCE_NAME}" \
    --password="${DB_PASSWORD}" 2>/dev/null || echo "  ℹ️  User '${DB_USER}' already exists"

echo "  ✅ Database configured"

# ─── Step 5: Store Secrets in Secret Manager ─────────────────────────────────
echo ""
echo "▸ Storing secrets in Secret Manager..."

create_or_update_secret() {
    local SECRET_NAME=$1
    local SECRET_VALUE=$2

    if gcloud secrets describe "${SECRET_NAME}" --format="value(name)" 2>/dev/null; then
        echo -n "${SECRET_VALUE}" | gcloud secrets versions add "${SECRET_NAME}" --data-file=-
    else
        echo -n "${SECRET_VALUE}" | gcloud secrets create "${SECRET_NAME}" --data-file=-
    fi
}

create_or_update_secret "django-secret-key" "${DJANGO_SECRET_KEY}"
create_or_update_secret "db-password" "${DB_PASSWORD}"
create_or_update_secret "stripe-secret-key" "${STRIPE_SECRET_KEY:-changeme}"
create_or_update_secret "stripe-webhook-secret" "${STRIPE_WEBHOOK_SECRET:-changeme}"
create_or_update_secret "cloudinary-cloud-name" "${CLOUDINARY_CLOUD_NAME:-changeme}"
create_or_update_secret "cloudinary-api-key" "${CLOUDINARY_API_KEY:-changeme}"
create_or_update_secret "cloudinary-api-secret" "${CLOUDINARY_API_SECRET:-changeme}"

echo "  ✅ Secrets stored"

# ─── Step 6: Build and Push Docker Image ─────────────────────────────────────
IMAGE_TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
FULL_IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${AR_REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"

echo ""
echo "▸ Building Docker image..."
docker build -t "${FULL_IMAGE}" .

echo ""
echo "▸ Pushing image to Artifact Registry..."
docker push "${FULL_IMAGE}"

echo "  ✅ Image pushed: ${FULL_IMAGE}"

# ─── Step 7: Deploy to Cloud Run ─────────────────────────────────────────────
echo ""
echo "▸ Deploying to Cloud Run..."

# Get the Cloud SQL connection name
INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe "${DB_INSTANCE_NAME}" \
    --format="value(connectionName)")

# Build environment variable flags
ENV_VARS=(
    "DJANGO_SETTINGS_MODULE=core.settings"
    "DEBUG=false"
    "ALLOWED_HOSTS=${SERVICE_NAME}-${GCP_PROJECT_ID}.${GCP_REGION}.run.app"
    "CSRF_TRUSTED_ORIGINS=https://${SERVICE_NAME}-${GCP_PROJECT_ID}.${GCP_REGION}.run.app"
    "DB_ENGINE=django.db.backends.postgresql"
    "DB_NAME=${DB_NAME}"
    "DB_USER=${DB_USER}"
    "DB_HOST=/cloudsql/${INSTANCE_CONNECTION_NAME}"
    "DB_PORT=5432"
    "DB_SSLMODE=disable"
    "REDIS_URL=${REDIS_URL:-redis://127.0.0.1:6379/1}"
    "STRIPE_CURRENCY=usd"
    "EMAIL_HOST=${EMAIL_HOST:-smtp.gmail.com}"
    "EMAIL_PORT=${EMAIL_PORT:-587}"
    "EMAIL_USE_TLS=${EMAIL_USE_TLS:-true}"
    "DEFAULT_FROM_EMAIL=${DEFAULT_FROM_EMAIL:-noreply@booker.app}"
)

# Join env vars for gcloud
ENV_VARS_STR=$(IFS=,; echo "${ENV_VARS[*]}")

# Allow unauthenticated requests (public API)
# Remove --no-allow-unauthenticated if you want Cloud Run to handle auth
gcloud run deploy "${SERVICE_NAME}" \
    --image="${FULL_IMAGE}" \
    --region="${GCP_REGION}" \
    --platform=managed \
    --port="${CONTAINER_PORT}" \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=10 \
    --timeout=120 \
    --concurrency=80 \
    --set-env-vars="${ENV_VARS_STR}" \
    --set-secrets="DJANGO_SECRET_KEY=django-secret-key:latest,DB_PASSWORD=db-password:latest,STRIPE_SECRET_KEY=stripe-secret-key:latest,STRIPE_WEBHOOK_SECRET=stripe-webhook-secret:latest,CLOUDINARY_CLOUD_NAME=cloudinary-cloud-name:latest,CLOUDINARY_API_KEY=cloudinary-api-key:latest,CLOUDINARY_API_SECRET=cloudinary-api-secret:latest" \
    --add-cloudsql-instances="${INSTANCE_CONNECTION_NAME}" \
    --service-account="${SERVICE_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
    --allow-unauthenticated

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${GCP_REGION}" \
    --format="value(status.url)")

echo "  ✅ Deployed to: ${SERVICE_URL}"

# ─── Step 8: Run Database Migrations ─────────────────────────────────────────
echo ""
echo "▸ Running database migrations..."
gcloud run services execute "${SERVICE_NAME}" \
    --region="${GCP_REGION}" \
    --command="python" \
    --args="manage.py,migrate,--no-input" \
    --async

echo "  ✅ Migrations triggered (async)"

# ─── Step 9: Create Cache Table ──────────────────────────────────────────────
echo ""
echo "▸ Creating cache table for DatabaseCache..."
gcloud run services execute "${SERVICE_NAME}" \
    --region="${GCP_REGION}" \
    --command="python" \
    --args="manage.py,createcachetable" \
    --async

echo "  ✅ Cache table creation triggered (async)"

# ─── Step 10: Collect Static Files ───────────────────────────────────────────
echo ""
echo "▸ Collecting static files..."
gcloud run services execute "${SERVICE_NAME}" \
    --region="${GCP_REGION}" \
    --command="python" \
    --args="manage.py,collectstatic,--no-input" \
    --async

echo "  ✅ Static files collection triggered (async)"

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Deployment Complete!                     ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║"
echo "║  Service URL:  ${SERVICE_URL}"
echo "║  Image:        ${FULL_IMAGE}"
echo "║  SQL Instance: ${GCP_PROJECT_ID}:${GCP_REGION}:${DB_INSTANCE_NAME}"
echo "║"
echo "║  Next steps:"
echo "║  1. Verify: gcloud run services describe ${SERVICE_NAME} --region ${GCP_REGION}"
echo "║  2. Logs:   gcloud run services logs read ${SERVICE_NAME} --region ${GCP_REGION}"
echo "║  3. Create superuser:"
echo "║     gcloud run services execute ${SERVICE_NAME} --region ${GCP_REGION} \\"
echo "║       --command=python --args=manage.py,createsuperuser"
echo "║"
echo "╚══════════════════════════════════════════════════════════════╝"
