#!/usr/bin/env bash
#
# Rebuild and restart a single MTGC instance on macOS.
# No systemd — uses podman directly.
#
# Usage:
#   bash deploy/thaen/deploy.sh <instance>
#
# Example:
#   bash deploy/thaen/deploy.sh prod
#
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: bash deploy/thaen/deploy.sh <instance>"
    echo "Example: bash deploy/thaen/deploy.sh prod"
    exit 1
fi

INSTANCE="$1"
CONTAINER_NAME="mtgc-${INSTANCE}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_DIR"

# If container doesn't exist, delegate to setup.sh for initial install
if ! podman container exists "$CONTAINER_NAME" 2>/dev/null; then
    echo "==> No container found for $INSTANCE, running initial setup..."
    bash "$SCRIPT_DIR/setup.sh" "$INSTANCE"
else
    # Capture current port mapping before teardown
    PORT_LINE=$(podman port "$CONTAINER_NAME" 8081/tcp 2>/dev/null || true)
    CURRENT_PORT=$(echo "$PORT_LINE" | sed 's/.*://' | head -1)

    echo "==> Building container image (mtgc:$INSTANCE)..."
    podman build -t "mtgc:${INSTANCE}" -f Containerfile .

    echo "==> Replacing container ($CONTAINER_NAME)..."
    podman stop "$CONTAINER_NAME" 2>/dev/null || true
    podman rm "$CONTAINER_NAME" 2>/dev/null || true

    ENV_FILE="$HOME/.config/mtgc/${INSTANCE}.env"

    podman run -d \
        --name "$CONTAINER_NAME" \
        --restart=on-failure \
        -p "${CURRENT_PORT}:8081" \
        -v "mtgc-${INSTANCE}-data:/data" \
        --env-file "$ENV_FILE" \
        -e MTGC_HOME=/data \
        "localhost/mtgc:${INSTANCE}"
fi

# Discover port and health check
sleep 2
PORT_LINE=$(podman port "$CONTAINER_NAME" 8081/tcp 2>/dev/null || true)
PORT=$(echo "$PORT_LINE" | sed 's/.*://' | head -1)
if [ -z "$PORT" ]; then
    echo "==> Could not determine port. Check: podman port $CONTAINER_NAME"
    exit 1
fi

echo "==> Listening on port $PORT"
MAX_ATTEMPTS=15
echo "==> Health check: $CONTAINER_NAME (port $PORT)..."
for i in $(seq 1 $MAX_ATTEMPTS); do
    if curl -skf --connect-timeout 3 "https://localhost:${PORT}/" > /dev/null 2>&1; then
        echo "==> Health check passed (attempt $i/$MAX_ATTEMPTS)"
        exit 0
    fi
    echo "    Attempt $i/$MAX_ATTEMPTS failed, waiting 2s..."
    sleep 2
done

echo "==> Health check FAILED after $MAX_ATTEMPTS attempts"
exit 1
