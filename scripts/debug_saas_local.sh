#!/bin/bash
IMAGE="asia-northeast1-docker.pkg.dev/tabi-487416/tabi-repo/tabi-saas:manual-fix-v3"

docker pull $IMAGE

docker run --rm -it \
  -p 8080:8080 \
  -e PORT=8080 \
  -e APP_MODE=saas \
  -e GOOGLE_CLOUD_PROJECT=tabi-487416 \
  -e GOOGLE_CLOUD_LOCATION=asia-northeast1 \
  -e DATABASE_URL="postgresql://dummy:dummy@localhost:5432/dummy" \
  $IMAGE
