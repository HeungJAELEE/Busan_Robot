#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REGISTRY="${REGISTRY:-ghcr.io/heungjaelee}"
TAG="${TAG:-latest}"
PLATFORM="${PLATFORM:-linux/amd64}"

IMAGES=(
  "robot-controller:backend/docker/robot_controller.Dockerfile"
  "db-worker:backend/docker/db_worker.Dockerfile"
  "digital-twin:backend/docker/digital_twin.Dockerfile"
  "plc-bridge:backend/docker/plc_bridge.Dockerfile"
  "vision-yolo:backend/docker/vision_yolo.Dockerfile"
)

if ! command -v docker >/dev/null 2>&1; then
  echo "docker command not found. Install Docker Desktop or use the GitHub Actions publisher."
  exit 127
fi

docker buildx inspect >/dev/null 2>&1 || docker buildx create --use >/dev/null

for item in "${IMAGES[@]}"; do
  image="${item%%:*}"
  dockerfile="${item#*:}"
  full_image="${REGISTRY}/indy7-hmi-${image}:${TAG}"
  echo "==> Building and pushing ${full_image}"
  docker buildx build \
    --platform "${PLATFORM}" \
    --file "${ROOT_DIR}/${dockerfile}" \
    --tag "${full_image}" \
    --push \
    "${ROOT_DIR}"
done
