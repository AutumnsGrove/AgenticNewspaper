# GroveBloom Reference Patterns

> Source: https://github.com/AutumnsGrove/GroveBloom
> Purpose: Serverless remote coding agent infrastructure with transient VPS

---

## What to Clone For

When you need to reference GroveBloom patterns:

```bash
git clone https://github.com/AutumnsGrove/GroveBloom /tmp/grovebloom-ref
```

---

## Key Patterns for Newspaper Project

### 1. Transient Compute Pattern (CRITICAL)

**The Big Idea**: Spin up VPS, do batch work, sync results, destroy.

```
5:00 AM: Hetzner VPS provisions (~30-45 seconds)
5:01 AM: Run all users' newspaper generation
5:30 AM: Sync results to R2
5:31 AM: VPS terminates
Cost: ~$0.01 for 30 minutes
```

**Location**:
- `packages/worker/src/services/hetzner.ts` - VPS lifecycle
- `packages/vps-scripts/cloud-init.yaml` - Provisioning
- `packages/vps-scripts/sync-to-r2.sh` - State sync

**Useful for**: Batch newspaper generation for all users (daily/weekly runs)

### 2. State Machine Pattern

**Location**: `packages/worker/src/types/`

```
OFFLINE → PROVISIONING → RUNNING → IDLE → SYNCING → TERMINATING → OFFLINE
```

**Newspaper equivalent**:
```
IDLE → COLLECTING → ANALYZING → SYNTHESIZING → DELIVERING → IDLE
```

### 3. Webhook-Driven Architecture

**Location**: `packages/worker/src/index.ts`

```typescript
// VPS → Worker webhooks
POST /webhook/ready     // VPS up, update DNS
POST /webhook/heartbeat // Track activity
POST /webhook/task-complete // Trigger cleanup
POST /webhook/idle-timeout  // Graceful shutdown
```

**Useful for**: Coordinating between Workers and external compute

### 4. R2 Sync for State Preservation

**Location**: `packages/vps-scripts/sync-to-r2.sh`

Pattern: No data loss despite VPS destruction
- Workspace snapshots to `bloom-state` bucket
- Repos to `bloom-repos` bucket

**Useful for**: Caching fetched articles, storing generated digests

### 5. Dual-Model AI Configuration

**Pattern**: Different models for different tasks

```
DeepSeek V3.2 → Code/reasoning (cheap: $0.28/$0.42 per 1M)
GLM 4.6V → Vision tasks (when needed)
```

**Newspaper equivalent**:
```
Haiku/DeepSeek → Search queries, parsing (cheap, fast)
Sonnet → Synthesis, bias detection (expensive, smart)
```

### 6. Cost Tracking Tables

**Location**: `schemas/d1-schema.sql`

```sql
monthly_summary
├── month (YYYY-MM)
├── total_hours
├── total_cost
└── session_count
```

**Useful for**: Per-user cost tracking, billing

### 7. Monorepo Structure

```
packages/
├── dashboard/     # SvelteKit UI
├── worker/        # Cloudflare Workers
└── vps-scripts/   # Provisioning scripts
```

**Useful for**: Organizing newspaper project similarly

---

## Hetzner Region Pricing

| Region | Cost/hr | Latency to US |
|--------|---------|---------------|
| EU (Falkenstein) | €0.0085 (~$0.009) | 90-100ms |
| US (Ashburn) | €0.022 (~$0.024) | 20-30ms |

For batch processing (not latency-sensitive), EU is 2.5x cheaper.

---

## Files to Read First

1. `docs/grove-bloom-spec.md` - Complete specification
2. `packages/worker/src/services/hetzner.ts` - VPS provisioning
3. `packages/vps-scripts/cloud-init.yaml` - Server setup
4. `schemas/d1-schema.sql` - Database schema
5. `packages/dashboard/src/lib/stores/session.svelte.ts` - Svelte 5 state

---

## Svelte 5 State Pattern

**Location**: `packages/dashboard/src/lib/stores/session.svelte.ts`

```typescript
let state = $state<SessionState>({
  status: null,
  loading: false,
  error: null,
});

const isRunning = $derived(
  state.status?.state === 'RUNNING'
);

async function start(region: Region) {
  state.loading = true;
  // ...
}
```

---

## Cleanup After Reference

```bash
rm -rf /tmp/grovebloom-ref
```
