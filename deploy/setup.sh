#!/usr/bin/env bash
#
# One-time machine setup for MTGC deployment.
# Run this as the application user (e.g. ryangantt) who has sudo access.
# After this script completes, deploy.sh handles all subsequent deploys.
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="/var/lib/mtgc"

echo "==> MTGC deployment setup"
echo "    Repo: $REPO_DIR"
echo "    Data: $DATA_DIR"
echo ""

# --- Prerequisites ---

echo "==> Checking prerequisites..."

if ! command -v uv &>/dev/null; then
    echo "ERROR: uv not found. Install it first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

if ! command -v nginx &>/dev/null; then
    echo "ERROR: nginx not found. Install it first:"
    echo "  sudo apt install nginx"
    exit 1
fi

if ! command -v curl &>/dev/null; then
    echo "ERROR: curl not found. Install it first:"
    echo "  sudo apt install curl"
    exit 1
fi

echo "    uv: $(which uv)"
echo "    nginx: $(which nginx)"

# --- Dependencies ---

echo "==> Installing Python dependencies..."
cd "$REPO_DIR"
uv sync

# --- Data directory ---

if [ ! -d "$DATA_DIR" ]; then
    echo "==> Creating data directory..."
    sudo mkdir -p "$DATA_DIR"
    sudo chown "$(whoami):$(id -gn)" "$DATA_DIR"
fi

echo "==> Running mtg setup (DB + Scryfall cache, ~500MB download)..."
MTGC_HOME="$DATA_DIR" uv run mtg setup

echo "==> Fetching price data (~200MB download)..."
MTGC_HOME="$DATA_DIR" uv run mtg data fetch-prices

# --- systemd service ---

echo "==> Installing systemd service..."
sudo cp "$REPO_DIR/deploy/mtgc.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mtgc

# --- nginx ---

echo "==> Installing nginx config..."
sudo cp "$REPO_DIR/deploy/mtgc-nginx.conf" /etc/nginx/sites-available/mtgc
sudo ln -sf /etc/nginx/sites-available/mtgc /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# --- Verify ---

echo ""
echo "==> Verifying..."
sleep 2

if curl -sf http://localhost:8081/ > /dev/null 2>&1; then
    echo "    mtgc service (port 8081): OK"
else
    echo "    mtgc service (port 8081): FAILED"
    echo "    Check: sudo journalctl -u mtgc -n 20 --no-pager"
fi

if curl -sf http://localhost:8082/ > /dev/null 2>&1; then
    echo "    nginx proxy (port 8082): OK"
else
    echo "    nginx proxy (port 8082): FAILED"
    echo "    Check: sudo nginx -t"
fi

echo ""
echo "==> Setup complete!"
echo ""
echo "Remaining manual step: register a GitHub Actions self-hosted runner"
echo "on your fork. Go to your fork on GitHub:"
echo "  Settings > Actions > Runners > New self-hosted runner"
echo ""
echo "Then install it as a service:"
echo "  cd ~/actions-runner"
echo "  sudo ./svc.sh install"
echo "  sudo ./svc.sh start"
