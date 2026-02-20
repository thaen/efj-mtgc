#!/usr/bin/env bash
#
# Tear down an MTGC container instance on macOS.
# Stops the container, removes it and its image.
# Data volume and env file are preserved unless --purge is passed.
#
# Usage:
#   bash deploy/thaen/teardown.sh <instance>          # keep data
#   bash deploy/thaen/teardown.sh <instance> --purge   # remove everything
#
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: bash deploy/thaen/teardown.sh <instance> [--purge]"
    exit 1
fi

INSTANCE="$1"
PURGE="${2:-}"
CONTAINER_NAME="mtgc-${INSTANCE}"

if ! podman container exists "$CONTAINER_NAME" 2>/dev/null; then
    echo "ERROR: No container found for instance '$INSTANCE'"
    exit 1
fi

echo "==> Tearing down $CONTAINER_NAME..."

podman stop "$CONTAINER_NAME" 2>/dev/null || true
podman rm "$CONTAINER_NAME" 2>/dev/null || true

# Remove image
podman rmi "mtgc:${INSTANCE}" 2>/dev/null || true

echo "    Container stopped and removed."

if [ "$PURGE" = "--purge" ]; then
    podman volume rm "mtgc-${INSTANCE}-data" 2>/dev/null || true
    echo "    Data volume removed."

    rm -f "$HOME/.config/mtgc/${INSTANCE}.env"
    echo "    Env file removed."

    echo "==> Purge complete — all traces of $INSTANCE removed."
else
    echo "    Data volume and env file preserved."
    echo "    Run with --purge to remove everything."
fi
