# Hetzner On-Demand Architecture

**Status**: Design Phase
**Cost Savings**: 90% compared to persistent server ($7/year vs $60/year)
**Inspired by**: [Grove Minecraft Server](https://github.com/AutumnsGrove) ephemeral architecture

---

## 🎯 Core Concept

Instead of running a 24/7 Hetzner VPS, we provision servers **on-demand** for 1-2 hours when digest generation is needed, then destroy them. This reduces monthly costs from $5 to ~$0.60.

```
IDLE (no server) ──► PROVISION (1-2 min) ──► RUN (20-30 min) ──► DESTROY ──► IDLE
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      CLOUDFLARE (Always On)                       │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ R2: digests  │  │ R2: core-pkg │  │  D1: state   │           │
│  │ (output .md) │  │ (Python src) │  │ (jobs, logs) │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                  │                   │
│         └─────────────────┼──────────────────┘                   │
│                           │                                      │
│              ┌────────────▼────────────┐                         │
│              │ Worker: hetzner-control │                         │
│              │  - Provision VPS        │                         │
│              │  - Monitor jobs         │                         │
│              │  - Destroy VPS          │                         │
│              │  - Store results        │                         │
│              └────────────┬────────────┘                         │
│                           │                                      │
│      ┌────────────────────┼────────────────────┐                 │
│      │                    │                    │                 │
│  ┌───▼────┐         ┌─────▼──────┐      ┌─────▼──────┐          │
│  │  Cron  │         │ API: /gen  │      │   Pages    │          │
│  │ 6am/6pm│         │  (manual)  │      │  /digests  │          │
│  └────────┘         └────────────┘      └────────────┘          │
└───────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │  Hetzner VPS (Ephemeral)     │
                │  CPX11: 2 vCPU, 2GB, $0.01/h │
                │                              │
                │  ┌────────────────────────┐  │
                │  │  cloud-init startup    │  │
                │  │  1. Install UV+Python  │  │
                │  │  2. Clone from GitHub  │  │
                │  │  3. Install deps       │  │
                │  │  4. Run orchestrator   │  │
                │  │  5. Upload to R2       │  │
                │  │  6. POST completion    │  │
                │  │  7. Self-destruct      │  │
                │  └────────────────────────┘  │
                │                              │
                │  Lifecycle: ~30-60 minutes   │
                │  Cost: $0.01-0.02 per run    │
                └──────────────────────────────┘
```

---

## 📊 State Machine

### States

1. **IDLE**: No server exists, waiting for trigger
2. **PROVISIONING**: Creating Hetzner VPS (1-2 min)
3. **INSTALLING**: Installing dependencies (1-2 min)
4. **RUNNING**: Generating digest (20-30 min)
5. **UPLOADING**: Saving results to R2 (30 sec)
6. **DESTROYING**: Deleting server (instant)

### Transitions

```
IDLE
  │
  ├─[Cron trigger 6am/6pm]──► PROVISIONING
  ├─[Manual API call]────────► PROVISIONING
  │
PROVISIONING
  │
  ├─[Server ready]───────────► INSTALLING
  ├─[Provisioning failed]────► IDLE (log error)
  │
INSTALLING
  │
  ├─[Setup complete]─────────► RUNNING
  ├─[Setup failed]───────────► DESTROYING (cleanup)
  │
RUNNING
  │
  ├─[Digest complete]────────► UPLOADING
  ├─[Job timeout]────────────► DESTROYING (partial results)
  ├─[Job error]──────────────► DESTROYING (log error)
  │
UPLOADING
  │
  ├─[Upload success]─────────► DESTROYING
  ├─[Upload failed]──────────► DESTROYING (retry failed)
  │
DESTROYING
  │
  └─[Server deleted]─────────► IDLE
```

---

## 🗄️ D1 Database Schema

### `jobs` table

Tracks digest generation jobs and server lifecycle:

```sql
CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  status TEXT NOT NULL, -- provisioning, installing, running, uploading, destroying, completed, failed
  server_id TEXT,       -- Hetzner server ID
  server_ip TEXT,       -- Server IP address
  started_at TEXT NOT NULL,
  completed_at TEXT,
  error TEXT,

  -- Job metadata
  topics_count INTEGER,
  articles_found INTEGER,
  articles_included INTEGER,
  tokens_used INTEGER,
  cost_usd REAL,

  -- Output
  digest_r2_key TEXT,   -- R2 path to generated digest

  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_user ON jobs(user_id);
CREATE INDEX idx_jobs_started ON jobs(started_at);
```

### `server_logs` table

Detailed server lifecycle logs:

```sql
CREATE TABLE server_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  level TEXT NOT NULL,  -- info, warn, error
  message TEXT NOT NULL,
  metadata TEXT,        -- JSON blob

  FOREIGN KEY (job_id) REFERENCES jobs(id)
);

CREATE INDEX idx_logs_job ON server_logs(job_id);
```

---

## 🚀 Hetzner API Integration

### Provisioning Flow

```typescript
// In Cloudflare Worker
async function provisionServer(jobId: string, userId: string) {
  // 1. Create server via Hetzner API
  const response = await fetch('https://api.hetzner.cloud/v1/servers', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.HETZNER_API_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name: `clearing-${jobId}`,
      server_type: 'cpx11',      // 2 vCPU, 2GB RAM, $0.01/h
      location: 'ash',            // Ashburn, VA (or 'fsn1' for EU)
      image: 'ubuntu-22.04',
      user_data: await generateCloudInit(jobId, userId),
      labels: {
        project: 'daily-clearing',
        job_id: jobId,
        ephemeral: 'true',
      },
    }),
  });

  const { server } = await response.json();

  // 2. Store server info in D1
  await env.DB.prepare(`
    UPDATE jobs
    SET server_id = ?, server_ip = ?, status = 'provisioning'
    WHERE id = ?
  `).bind(server.id, server.public_net.ipv4.ip, jobId).run();

  return server;
}
```

### cloud-init Script

This runs when the server boots:

```bash
#!/bin/bash
set -e

JOB_ID="{{JOB_ID}}"
USER_ID="{{USER_ID}}"
WEBHOOK_URL="{{CLOUDFLARE_WORKER_URL}}/api/webhooks/job-status"

# 1. Update system and install dependencies
apt-get update
apt-get install -y python3.11 python3.11-venv git curl

# 2. Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

# 3. Clone repository
cd /opt
git clone https://github.com/AutumnsGrove/AgenticNewspaper.git
cd AgenticNewspaper/packages/core

# 4. Create secrets.json from environment
cat > secrets.json <<EOF
{
  "openrouter_api_key": "$OPENROUTER_API_KEY",
  "tavily_api_key": "$TAVILY_API_KEY",
  "anthropic_api_key": "$ANTHROPIC_API_KEY"
}
EOF
chmod 600 secrets.json

# 5. Install dependencies
uv sync

# 6. Run digest generation
uv run python -c "
import asyncio
import httpx
from src.orchestrator.main_orchestrator import generate_digest_for_user

async def main():
    try:
        # Generate digest
        digest = await generate_digest_for_user('$USER_ID')

        # Upload to R2 via Cloudflare Worker
        async with httpx.AsyncClient() as client:
            await client.post(
                '$WEBHOOK_URL',
                json={
                    'job_id': '$JOB_ID',
                    'status': 'completed',
                    'digest': digest,
                }
            )
    except Exception as e:
        # Report error
        async with httpx.AsyncClient() as client:
            await client.post(
                '$WEBHOOK_URL',
                json={
                    'job_id': '$JOB_ID',
                    'status': 'failed',
                    'error': str(e),
                }
            )
    finally:
        # Self-destruct (trigger server deletion)
        async with httpx.AsyncClient() as client:
            await client.post(
                '$WEBHOOK_URL',
                json={
                    'job_id': '$JOB_ID',
                    'action': 'destroy',
                }
            )

asyncio.run(main())
"

# Script completes, server waits for deletion signal
```

---

## 🎛️ Cloudflare Worker Endpoints

### Trigger Digest Generation

```typescript
// POST /api/generate
app.post('/api/generate', async (c) => {
  const { userId, preferences } = await c.req.json();

  // Create job record
  const jobId = crypto.randomUUID();
  await c.env.DB.prepare(`
    INSERT INTO jobs (id, user_id, status, started_at)
    VALUES (?, ?, 'pending', ?)
  `).bind(jobId, userId, new Date().toISOString()).run();

  // Provision server (async)
  await provisionServer(jobId, userId);

  return c.json({ jobId, status: 'provisioning' });
});
```

### Webhook for Status Updates

```typescript
// POST /api/webhooks/job-status
app.post('/api/webhooks/job-status', async (c) => {
  const { job_id, status, digest, error, action } = await c.req.json();

  if (action === 'destroy') {
    // Get server ID
    const job = await c.env.DB.prepare('SELECT server_id FROM jobs WHERE id = ?')
      .bind(job_id).first();

    // Delete Hetzner server
    await fetch(`https://api.hetzner.cloud/v1/servers/${job.server_id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${c.env.HETZNER_API_TOKEN}` },
    });

    // Update job status
    await c.env.DB.prepare(`
      UPDATE jobs SET status = 'destroyed', completed_at = ? WHERE id = ?
    `).bind(new Date().toISOString(), job_id).run();

    return c.json({ success: true });
  }

  if (status === 'completed' && digest) {
    // Upload digest to R2
    const key = `digests/${job_id}.md`;
    await c.env.DIGESTS.put(key, digest);

    // Update job
    await c.env.DB.prepare(`
      UPDATE jobs
      SET status = ?, digest_r2_key = ?, completed_at = ?
      WHERE id = ?
    `).bind('uploading', key, new Date().toISOString(), job_id).run();
  }

  if (status === 'failed') {
    await c.env.DB.prepare(`
      UPDATE jobs SET status = 'failed', error = ?, completed_at = ? WHERE id = ?
    `).bind(error, new Date().toISOString(), job_id).run();
  }

  return c.json({ success: true });
});
```

---

## 💰 Cost Breakdown

### Per Digest

| Item | Cost |
|------|------|
| Hetzner CPX11 (30 min) | $0.005 |
| DeepSeek V3.2 tokens | $0.001 |
| Tavily searches (5) | $0.050 |
| Cloudflare R2 storage | $0.000 (free tier) |
| Cloudflare D1 queries | $0.000 (free tier) |
| **Total** | **$0.056** |

### Monthly (60 digests/month for 1 user)

| Item | Cost |
|------|------|
| Compute (60 × $0.005) | $0.30 |
| API costs (60 × $0.051) | $3.06 |
| **Total** | **$3.36/month** |

### Annual Cost Comparison

| Approach | Cost |
|----------|------|
| **On-demand Hetzner** | **$40/year** |
| Persistent Hetzner | $60/year + $37/year API = $97/year |
| Cloudflare only | Would hit limits quickly |

**Savings**: 59% cheaper than persistent server!

---

## 🔐 Required GitHub Secrets

Add these to your GitHub repo for the deployment workflow:

| Secret | Description | How to Get |
|--------|-------------|------------|
| `HETZNER_API_TOKEN` | Hetzner Cloud API token | Hetzner Console → Security → API Tokens → Generate |
| `CLOUDFLARE_WORKER_URL` | Your worker URL | After first deploy: `https://daily-clearing.xxx.workers.dev` |

---

## 🚦 Implementation Phases

### Phase 1: Manual Trigger (Current)
- [x] Cloudflare Worker deployed
- [ ] Add Hetzner API integration
- [ ] Create cloud-init template
- [ ] Test manual server provisioning

### Phase 2: Automated Lifecycle
- [ ] Add D1 job tracking
- [ ] Implement status webhooks
- [ ] Add automatic server destruction
- [ ] Monitor and log all stages

### Phase 3: Scheduled Digests
- [ ] Connect cron triggers
- [ ] Add user preferences
- [ ] Batch multiple users per server
- [ ] Optimize for cost

### Phase 4: Production Ready
- [ ] Error recovery
- [ ] Retry logic
- [ ] Cost alerts
- [ ] Performance monitoring

---

## 🎯 Next Steps

1. **Add Hetzner API token to GitHub secrets**
2. **Create Hetzner provisioning function in Worker**
3. **Test full lifecycle with manual trigger**
4. **Connect to scheduled cron jobs**
5. **Monitor costs and optimize**

---

**Last Updated**: 2025-12-25
**Architecture**: Ephemeral on-demand compute
**Estimated Savings**: 90% vs persistent server
