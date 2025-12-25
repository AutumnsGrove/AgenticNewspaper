# Forage Reference Patterns

> Source: https://github.com/AutumnsGrove/Forage
> Purpose: AI-powered domain name discovery with multi-agent orchestration

---

## What to Clone For

When you need to reference Forage patterns:

```bash
git clone https://github.com/AutumnsGrove/Forage /tmp/forage-ref
```

---

## Key Patterns for Newspaper Project

### 1. Two-Tier Agent System (CRITICAL)

**Location**: `worker/src/agents/`

This is the PRIMARY pattern to follow for newspaper agents:

```
Driver Agent (Generation)     →    Swarm Agent (Evaluation)
├── Single call per batch          ├── Parallel chunked processing
├── Generates 50 candidates        ├── Evaluates in chunks of 10
├── Uses tool calling              ├── Up to 12 concurrent chunks
└── Returns structured output      └── Graceful fallback to heuristics
```

**Newspaper equivalent**:
- Driver Agent → Search Agent (generate article candidates)
- Swarm Agent → Eval Agents (score articles for quality/bias/relevance)

### 2. Durable Objects with Alarm-Based Batching

**Location**: `worker/src/durable-object.ts` (~1150 lines)

Pattern for long-running operations:
```typescript
// Start immediately
scheduleAlarm(0);

// In alarm() method
async alarm(): Promise<void> {
  const result = await this.processBatch(job);

  if (complete) {
    updateJobStatus("complete");
    await sendCompletionEmail(job);
  } else if (batch_num < maxBatches) {
    scheduleAlarm(10000); // Next batch in 10 seconds
  }
}
```

**Useful for**: Digest generation pipeline that processes many articles

### 3. Dual Persistence (DO + D1)

**Pattern**:
- **DO SQLite**: Source of truth for job details, results, artifacts
- **D1**: Index/discovery layer for listing and querying

```sql
-- DO tables
search_job (single row per job)
domain_results (accumulated results)
search_artifacts (reports, follow-ups)

-- D1 table
job_index (denormalized for fast queries)
```

**Useful for**: User digests in DO, digest history/discovery in D1

### 4. Provider Abstraction

**Location**: `worker/src/providers/`

```typescript
interface AIProvider {
  generate(prompt, options): Promise<ProviderResponse>
  generateWithTools(prompt, tools, options): Promise<ProviderResponse>
}

// Factory pattern
getProvider("deepseek", env) → DeepSeekProvider
getProvider("openrouter", env) → OpenRouterProvider
```

**Useful for**: Swapping between DeepSeek, Claude, GPT-oss, etc.

### 5. Chunked Concurrency Pattern

**Location**: `worker/src/agents/swarm.ts`

```typescript
const chunkSize = 10;
const maxConcurrent = 12;

for (let i = 0; i < chunks.length; i += maxConcurrent) {
  const batch = chunks.slice(i, i + maxConcurrent);
  await Promise.all(batch.map(chunk => evaluateChunk(...)));
}
```

**Useful for**: Parallel article evaluation without overwhelming APIs

### 6. Tool Calling with JSON Fallback

```typescript
try {
  // Try structured tool calling first
  const response = await provider.generateWithTools({ tools: [TOOL] });
  result = parseToolCall(response.toolCalls);
} catch (error) {
  // Fall back to JSON parsing from text
  result = await generateWithFallback(provider, prompt);
}
```

**Useful for**: Reliable structured output from any model

---

## Files to Read First

1. `worker/src/durable-object.ts` - DO lifecycle and batch processing
2. `worker/src/agents/driver.ts` - Generation agent pattern
3. `worker/src/agents/swarm.ts` - Parallel evaluation pattern
4. `worker/src/providers/index.ts` - Provider factory
5. `worker/src/job-index.ts` - D1 query patterns

---

## Configuration Reference

**wrangler.toml**:
```toml
[vars]
DRIVER_PROVIDER = "openrouter"
SWARM_PROVIDER = "openrouter"
MAX_BATCHES = "6"
TARGET_RESULTS = "25"
```

---

## Token/Cost Tracking

```typescript
// Accumulated in DO
total_input_tokens += response.usage.inputTokens;
total_output_tokens += response.usage.outputTokens;

// Cost estimation
const cost = (totalInput * COSTS.input + totalOutput * COSTS.output) / 1_000_000;
```

---

## Cleanup After Reference

```bash
rm -rf /tmp/forage-ref
```
