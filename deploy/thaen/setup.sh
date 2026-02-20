#!/usr/bin/env bash
#
# Set up an MTGC container instance on macOS (rootless Podman).
# No systemd, no Quadlet — just podman run.
#
# Usage:
#   bash deploy/thaen/setup.sh <instance> [port]
#
# Examples:
#   bash deploy/thaen/setup.sh prod 8081        # explicit port
#   bash deploy/thaen/setup.sh feature-xyz      # auto-assigns next free port
#
# Env file:
#   Copies from ~/.config/mtgc/default.env if it exists (set this up once
#   with your API key). Falls back to .env.example (needs manual editing).
#
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: bash deploy/thaen/setup.sh <instance> [port]"
    echo "Example: bash deploy/thaen/setup.sh prod 8081"
    exit 1
fi

INSTANCE="$1"
CONTAINER_NAME="mtgc-${INSTANCE}"
MTGC_CONFIG="$HOME/.config/mtgc"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# --- Port assignment ---

if [ $# -ge 2 ]; then
    PORT="$2"
else
    # Auto-assign: find highest host port among mtgc-* containers, add 1 (start at 8081)
    MAX_PORT=8080
    for P in $(podman ps -a --filter "name=^mtgc-" --format '{{.Ports}}' 2>/dev/null | sed 's/.*:\([0-9]*\)->.*/\1/' | sort -n); do
        if [ "$P" -gt "$MAX_PORT" ] 2>/dev/null; then
            MAX_PORT="$P"
        fi
    done
    PORT=$((MAX_PORT + 1))
fi

echo "==> MTGC deployment setup"
echo "    Instance: $INSTANCE"
echo "    Port:     $PORT"
echo "    Repo:     $REPO_DIR"

# --- Prerequisites ---

if ! command -v podman &>/dev/null; then
    echo "ERROR: podman not found. Install it first:"
    echo "  brew install podman"
    exit 1
fi

echo "    podman: $(podman --version)"

# --- Env file ---

ENV_FILE="${MTGC_CONFIG}/${INSTANCE}.env"
if [ ! -f "$ENV_FILE" ]; then
    mkdir -p "$MTGC_CONFIG"
    if [ -f "${MTGC_CONFIG}/default.env" ]; then
        echo "==> Creating $ENV_FILE from default.env..."
        cp "${MTGC_CONFIG}/default.env" "$ENV_FILE"
    else
        echo "==> Creating $ENV_FILE from .env.example..."
        echo "    NOTE: Set ANTHROPIC_API_KEY in $ENV_FILE before starting."
        echo "    (Create ~/.config/mtgc/default.env to skip this for future instances.)"
        cp "$REPO_DIR/.env.example" "$ENV_FILE"
    fi
    chmod 600 "$ENV_FILE"
else
    echo "    $ENV_FILE already exists, skipping"
fi

# --- Build container image ---

echo "==> Building container image (mtgc:$INSTANCE)..."
podman build -t "mtgc:${INSTANCE}" -f "$REPO_DIR/Containerfile" "$REPO_DIR"

# --- Run container ---

echo "==> Creating data volume (mtgc-${INSTANCE}-data)..."
podman volume create "mtgc-${INSTANCE}-data" 2>/dev/null || true

echo "==> Starting container ($CONTAINER_NAME)..."
podman run -d \
    --name "$CONTAINER_NAME" \
    --restart=on-failure \
    -p "${PORT}:8081" \
    -v "mtgc-${INSTANCE}-data:/data" \
    --env-file "$ENV_FILE" \
    -e MTGC_HOME=/data \
    "localhost/mtgc:${INSTANCE}"

echo ""
echo "==> Setup complete!"
echo ""
echo "  Port:       podman port $CONTAINER_NAME"
echo "  Init data:  podman exec -it $CONTAINER_NAME mtg setup"
echo "  Logs:       podman logs -f $CONTAINER_NAME"
echo "  Stop:       podman stop $CONTAINER_NAME"
echo "  Start:      podman start $CONTAINER_NAME"
echo "  Teardown:   bash deploy/thaen/teardown.sh $INSTANCE"
