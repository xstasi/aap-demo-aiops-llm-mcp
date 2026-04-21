#!/usr/bin/env bash
# Build the AIOps Triage custom Execution Environment.
#
# This script copies the triage Python scripts into the build context,
# runs ansible-builder, tags and pushes the image, then cleans up.
#
# Usage:
#   cd context/
#   ./build.sh [registry/image:tag]
#
# Prerequisites:
#   - ansible-builder >= 3.0
#   - podman (or docker)
#   - Access to registry.redhat.io (for the base EE image)

set -euo pipefail

IMAGE="${1:-aiops-triage-ee:latest}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Building Execution Environment: ${IMAGE}..."
ansible-builder build \
  --file "${SCRIPT_DIR}/execution-environment.yml" \
  --tag "${IMAGE}" \
  --container-runtime podman \
  --verbosity 3

echo "==> Cleaning up copied scripts..."
rm -rf "${SCRIPT_DIR}/files/"

echo ""
echo "Build complete: ${IMAGE}"
echo ""
echo "To push to a registry:"
echo "  podman tag ${IMAGE} registry.example.com/${IMAGE}"
echo "  podman push registry.example.com/${IMAGE}"
