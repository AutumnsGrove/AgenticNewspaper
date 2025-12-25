# Deployment Guide

## Overview

The Daily Clearing uses a dual deployment architecture:

- **TypeScript Worker** → Cloudflare Workers (edge computing, global distribution)
- **Python Core** → Hetzner VPS (dedicated server, local installations)

Both deployments are automated via GitHub Actions.

---

## GitHub Secrets Required

### Cloudflare Secrets

Add these in your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Description | How to Get It |
|-------------|-------------|---------------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token with Workers & D1 permissions | Cloudflare Dashboard → My Profile → API Tokens → Create Token → "Edit Cloudflare Workers" template |
| `CLOUDFLARE_ACCOUNT_ID` | Your Cloudflare account ID | Cloudflare Dashboard → Workers & Pages → Right sidebar |

### Hetzner Secrets

| Secret Name | Description | How to Get It |
|-------------|-------------|---------------|
| `HETZNER_HOST` | Your Hetzner VPS IP address or hostname | Hetzner Cloud Console → Your server → IPv4 address (e.g., `95.217.123.45`) |
| `HETZNER_USERNAME` | SSH username (usually `root` or `deploy`) | Created when you set up the server |
| `HETZNER_SSH_KEY` | Private SSH key for authentication | Local: `cat ~/.ssh/id_rsa` or `cat ~/.ssh/id_ed25519` |
| `HETZNER_PORT` | SSH port (optional, defaults to 22) | Usually `22` unless you changed it |

---

## Cloudflare Setup

### 1. Create Cloudflare Account & Project

1. Sign up at [Cloudflare](https://dash.cloudflare.com/)
2. Go to **Workers & Pages**
3. Create a new Worker (optional - GitHub Actions will handle deployment)

### 2. Create D1 Database

```bash
# From packages/worker directory
wrangler d1 create clearing-db
```

Copy the database ID from the output and update `wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "clearing-db"
database_id = "your-database-id-here"
```

### 3. Add Environment Variables

In Cloudflare Dashboard → Your Worker → Settings → Variables:

- `OPENROUTER_API_KEY` - Your OpenRouter API key
- `TAVILY_API_KEY` - Your Tavily API key
- `ANTHROPIC_API_KEY` - (Optional) Anthropic fallback key
- `JWT_SECRET` - Random secure string for JWT signing
- `ENVIRONMENT` - Set to `production`

---

## Hetzner Setup

### 1. Provision Server

1. Go to [Hetzner Cloud Console](https://console.hetzner.cloud/)
2. Create new project: "The Daily Clearing"
3. Add server:
   - Location: Choose closest to your users
   - Image: Ubuntu 22.04
   - Type: CPX11 (2 vCPU, 2GB RAM) - $5/month
   - SSH Key: Add your public key

### 2. Initial Server Setup

SSH into your server:

```bash
ssh root@YOUR_SERVER_IP
```

Run setup script:

```bash
# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3.11 python3.11-venv git curl

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Create deployment user
useradd -m -s /bin/bash deploy
mkdir -p /opt/clearing
chown deploy:deploy /opt/clearing

# Setup git
su - deploy
cd /opt/clearing
git clone https://github.com/YOUR_USERNAME/AgenticNewspaper.git .

# Install Python package
cd packages/core
uv sync
```

### 3. Create systemd service

Create `/etc/systemd/system/clearing.service`:

```ini
[Unit]
Description=The Daily Clearing - News Digest Service
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/clearing/packages/core
ExecStart=/home/deploy/.cargo/bin/uv run python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

Environment="OPENROUTER_API_KEY=your-key-here"
Environment="TAVILY_API_KEY=your-key-here"
Environment="ANTHROPIC_API_KEY=your-key-here"
Environment="ENVIRONMENT=production"

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable clearing.service
systemctl start clearing.service
systemctl status clearing.service
```

### 4. Setup Firewall

```bash
# Allow SSH, HTTP, HTTPS
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### 5. Add secrets.json

Create `/opt/clearing/packages/core/secrets.json`:

```json
{
  "openrouter_api_key": "sk-or-v1-...",
  "tavily_api_key": "tvly-...",
  "anthropic_api_key": "sk-ant-api03-..."
}
```

Secure it:

```bash
chown deploy:deploy /opt/clearing/packages/core/secrets.json
chmod 600 /opt/clearing/packages/core/secrets.json
```

---

## Triggering Deployments

### Automatic Deployments

Deployments trigger automatically when you push to `main`:

- Changes to `packages/worker/**` → Deploys to Cloudflare
- Changes to `packages/core/**` → Deploys to Hetzner

### Manual Deployments

GitHub Actions → Choose workflow → Run workflow → Select branch

---

## Monitoring

### Cloudflare

- **Logs**: Cloudflare Dashboard → Your Worker → Logs → Real-time Logs
- **Analytics**: Workers & Pages → Your Worker → Analytics
- **Errors**: Sentry integration (optional)

### Hetzner

```bash
# SSH into server
ssh deploy@YOUR_SERVER_IP

# View logs
journalctl -u clearing.service -f

# Check status
systemctl status clearing.service

# Restart service
systemctl restart clearing.service
```

---

## Cost Estimates

### Cloudflare Workers

- **Free Tier**: 100,000 requests/day
- **Paid Plan**: $5/month for 10M requests
- **D1 Database**: First 5GB free

**Estimated Cost**: $0-5/month

### Hetzner VPS

- **CPX11**: $5/month (2 vCPU, 2GB RAM, 40GB SSD)
- **CPX21**: $10/month (3 vCPU, 4GB RAM, 80GB SSD) - if you need more power

**Estimated Cost**: $5-10/month

### API Costs

- **DeepSeek V3.2**: ~$0.0007/digest
- **Tavily Search**: $0.01/search (5 searches/digest = $0.05)
- **Daily budget**: 100 users × 1 digest = $5/day = $150/month

**Estimated Cost**: $50-150/month (depends on usage)

---

## Troubleshooting

### Cloudflare Deployment Fails

1. Check GitHub Actions logs
2. Verify `CLOUDFLARE_API_TOKEN` has correct permissions
3. Ensure `wrangler.toml` is correct
4. Check D1 database exists: `wrangler d1 list`

### Hetzner Deployment Fails

1. Verify SSH key is correct (no passphrase)
2. Check server is accessible: `ssh deploy@YOUR_SERVER_IP`
3. Verify service exists: `systemctl status clearing.service`
4. Check logs: `journalctl -u clearing.service`

### Service Won't Start

1. Check secrets.json exists and has correct permissions
2. Verify UV is installed: `which uv`
3. Check Python version: `python3.11 --version`
4. Test manually: `cd /opt/clearing/packages/core && uv run python -m src.orchestrator.main_orchestrator`

---

## Next Steps

After deployment:

1. Test Cloudflare Worker: `curl https://your-worker.workers.dev/health`
2. Test Hetzner API: `curl http://YOUR_SERVER_IP:8000/health`
3. Set up cron jobs for digest generation
4. Add monitoring/alerting (e.g., UptimeRobot, Sentry)
5. Configure custom domain (optional)
6. Set up nginx reverse proxy with SSL (recommended)

---

**Last Updated**: 2025-12-25
**Deployment Strategy**: Dual architecture (Cloudflare + Hetzner)
