# Deploying MTGC as a Production Web Service

This guide covers deploying the MTG Card Collection Builder as a persistent web service on an Ubuntu machine, with automated deployment via GitHub Actions.

## Architecture

```
GitHub repo
    │
    │  push to main triggers deploy workflow
    ▼
Self-hosted runner
    │
    │  deploy.sh
    ▼
┌─────────────────────────────────────────┐
│  Ubuntu server                          │
│                                         │
│  nginx (:8082) ──► mtgc service (:8081) │
│                                         │
│  Code: ~/workspace/efj-mtgc             │
│  Data: /var/lib/mtgc                    │
└─────────────────────────────────────────┘
```

## Quick Start

If you just want to get it running and the defaults work for you:

```bash
# 1. Install prerequisites
sudo apt install nginx curl
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and run setup
git clone https://github.com/thaen/efj-mtgc.git ~/workspace/efj-mtgc
cd ~/workspace/efj-mtgc
bash deploy/setup.sh
```

`setup.sh` handles everything: installs dependencies, downloads card data (~700MB), installs the systemd service, and configures nginx. It checks prerequisites and verifies the deployment at the end.

## Prerequisites

- Ubuntu server (tested on 22.04/24.04)
- nginx (`sudo apt install nginx`)
- uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Python 3.12+

## Step-by-Step Setup

If you prefer to run each step manually, or need to customize the defaults.

### 1. Clone the repository

```bash
mkdir -p ~/workspace
git clone https://github.com/thaen/efj-mtgc.git ~/workspace/efj-mtgc
cd ~/workspace/efj-mtgc
uv sync
```

### 2. Create the data directory

The app stores its SQLite database, Scryfall cache, MTGJSON data, and price data here (~700MB after setup).

```bash
sudo mkdir -p /var/lib/mtgc
sudo chown $USER:$USER /var/lib/mtgc
```

### 3. Run initial data setup

Downloads Scryfall bulk data (~500MB) and MTGJSON price data (~200MB). Takes a few minutes.

```bash
MTGC_HOME=/var/lib/mtgc uv run mtg setup
MTGC_HOME=/var/lib/mtgc uv run mtg data fetch-prices
```

To load demo data (~50 cards) for testing:

```bash
MTGC_HOME=/var/lib/mtgc uv run mtg setup --demo
```

### 4. Install the systemd service

Edit `deploy/mtgc.service` first if your username, repo path, or uv path differ from the defaults:

| Field | Default | How to find yours |
|---|---|---|
| `User` / `Group` | `ryangantt` | `whoami` |
| `WorkingDirectory` | `/home/ryangantt/workspace/efj-mtgc` | Where you cloned the repo |
| `ExecStart` uv path | `/home/ryangantt/.local/bin/uv` | `which uv` |

Then install and start:

```bash
sudo cp deploy/mtgc.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mtgc
```

Verify it's running:

```bash
sudo systemctl status mtgc
curl http://localhost:8081/
```

### 5. Install the nginx config

The default config listens on port 8082. Edit `deploy/mtgc-nginx.conf` to change the port.

```bash
sudo cp deploy/mtgc-nginx.conf /etc/nginx/sites-available/mtgc
sudo ln -sf /etc/nginx/sites-available/mtgc /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Verify:

```bash
curl http://localhost:8082/
curl http://localhost:8082/api/cached-sets
```

At this point the app is running and accessible. The remaining steps set up automated deployment.

### 6. Set up automated deployment (optional)

To auto-deploy on every push to main, register a GitHub Actions self-hosted runner on your repo (or fork).

Go to GitHub: **Settings > Actions > Runners > New self-hosted runner**. Follow the instructions, then install as a systemd service:

```bash
cd ~/actions-runner
sudo ./svc.sh install
sudo ./svc.sh start
```

The deploy workflow (`.github/workflows/deploy.yml`) triggers on push to main, checks out the code, and runs `deploy/deploy.sh`. The deploy script needs sudo access to restart services — configure sudoers for your runner user to allow:

```
your-runner-user ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart mtgc
your-runner-user ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
your-runner-user ALL=(ALL) NOPASSWD: /usr/bin/systemctl daemon-reload
your-runner-user ALL=(ALL) NOPASSWD: /usr/bin/cp <repo-path>/deploy/mtgc.service /etc/systemd/system/mtgc.service
your-runner-user ALL=(ALL) NOPASSWD: /usr/bin/cp <repo-path>/deploy/mtgc-nginx.conf /etc/nginx/sites-available/mtgc
your-runner-user ALL=(ALL) NOPASSWD: /usr/bin/ln -sf /etc/nginx/sites-available/mtgc /etc/nginx/sites-enabled/
your-runner-user ALL=(ALL) NOPASSWD: /usr/sbin/nginx -t
your-runner-user ALL=(ALL) NOPASSWD: /usr/bin/mkdir -p /var/lib/mtgc
your-runner-user ALL=(ALL) NOPASSWD: /usr/bin/chown *\:* /var/lib/mtgc
```

## How It Works

1. Push to main triggers the deploy workflow
2. The self-hosted runner checks out the latest code
3. `deploy/deploy.sh` syncs dependencies, copies changed configs, restarts the service, and runs a health check

## What's in `deploy/`

| File | Purpose |
|---|---|
| `setup.sh` | One-time machine provisioning (run manually) |
| `deploy.sh` | Called by CI on every push (handles incremental updates) |
| `mtgc.service` | systemd unit file for the Python server |
| `mtgc-nginx.conf` | nginx reverse proxy config |

## Port Summary

| Port | Used by | Purpose |
|---|---|---|
| 8081 | mtgc (Python) | Application server (internal) |
| 8082 | nginx | Public-facing reverse proxy |

Both ports are configurable. Change 8081 in `mtgc.service` and `mtgc-nginx.conf`. Change 8082 in `mtgc-nginx.conf`.

## Troubleshooting

**Service won't start:**

```bash
sudo journalctl -u mtgc -n 50 --no-pager
```

**Service crashes with "AllPricesToday.json not found":**

The price data wasn't downloaded. Fix with:

```bash
MTGC_HOME=/var/lib/mtgc uv run mtg data fetch-prices
sudo systemctl restart mtgc
```

**Deploy workflow fails:**

Check the Actions tab on your repo. Common issues:
- Runner offline — verify with `sudo systemctl status actions.runner.*`
- Sudoers not installed — deploy.sh can't restart services
- Missing data directory — deploy.sh handles this on first run, but check `/var/lib/mtgc` exists and is owned by the right user

**nginx returns 502:**

The Python service isn't running or hasn't finished starting. Check `systemctl status mtgc` and wait a few seconds for startup.

**SSE streaming (ingest pages) not working through nginx:**

Verify `proxy_buffering off` is in the nginx config. Some environments also need `proxy_cache off` — add it to the `location /` block if SSE events are being batched.
