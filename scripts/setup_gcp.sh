#!/bin/bash
set -e

PROJECT_ID="tabi-487416"
REGION="asia-northeast1"
TF_STATE_BUCKET="${PROJECT_ID}-tf-state"
SA_NAME="github-deployer"

echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

echo "Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com \
  storage.googleapis.com

echo "Creating Terraform State Bucket: gs://$TF_STATE_BUCKET ..."
if ! gcloud storage buckets describe gs://$TF_STATE_BUCKET > /dev/null 2>&1; then
  gcloud storage buckets create gs://$TF_STATE_BUCKET --location=$REGION
else
  echo "Bucket already exists."
fi

echo "Creating Service Account..."
if ! gcloud iam service-accounts describe $SA_NAME@$PROJECT_ID.iam.gserviceaccount.com > /dev/null 2>&1; then
  gcloud iam service-accounts create $SA_NAME --display-name="GitHub Actions Deployer"
else
  echo "Service Account already exists."
fi

echo "Granting IAM roles..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/editor" > /dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin" > /dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.admin" > /dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin" > /dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/resourcemanager.projectIamAdmin" > /dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountCreator" > /dev/null

echo "Generating Key File..."
if [ ! -f gcp-key.json ]; then
  gcloud iam service-accounts keys create gcp-key.json \
    --iam-account=$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com
  echo "Key saved to gcp-key.json"
else
  echo "gcp-key.json already exists. Skipping creation."
fi

echo "========================================================"
echo "Setup Complete!"
echo "1. TF_STATE_BUCKET: $TF_STATE_BUCKET"
echo "2. Please copy the content of 'gcp-key.json' to GitHub Secret 'GCP_SA_KEY'."
echo "3. Add '$PROJECT_ID' to GitHub Secret 'GCP_PROJECT_ID' (if not already done)."
echo "4. Add '$TF_STATE_BUCKET' to GitHub Secret 'TF_STATE_BUCKET'."
echo "========================================================"
