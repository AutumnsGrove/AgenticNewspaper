# Amber Reference Patterns

> Source: https://github.com/AutumnsGrove/Amber
> Purpose: Unified storage management for Grove ecosystem

---

## What to Clone For

When you need to reference Amber patterns:

```bash
git clone https://github.com/AutumnsGrove/Amber /tmp/amber-ref
```

---

## Key Patterns for Newspaper Project

### 1. ExportJob Durable Object (CRITICAL)

**Location**: `worker/src/services/ExportJob.ts`

Production-grade DO for long-running operations:

```typescript
// SQLite-backed state (not KV!)
state.storage.sql

// Chunked processing
const CHUNK_SIZE = 100; // files per iteration
const MAX_CHUNK_BYTES = 50 * 1024 * 1024; // 50MB

// Alarm-driven continuation
async alarm() {
  await processNextChunk();
  if (!complete) {
    ctx.storage.setAlarm(Date.now() + 2000); // 2 second delay
  }
}
```

**Useful for**: Digest generation DO that processes articles in chunks

### 2. Parallel Validation Pattern

**Location**: `worker/src/services/ExportJob.ts`

```typescript
// Validate in parallel batches of 10
const VALIDATION_BATCH_SIZE = 10;
for (let i = 0; i < files.length; i += VALIDATION_BATCH_SIZE) {
  const batch = files.slice(i, i + VALIDATION_BATCH_SIZE);
  await Promise.all(batch.map(file => validateFile(file)));
}
```

**Useful for**: Parallel article fetching/validation

### 3. Resilient Partial Success

**Pattern**: Missing items are logged; don't fail the whole operation

```typescript
try {
  const content = await fetchArticle(url);
  results.push({ url, content, success: true });
} catch (error) {
  results.push({ url, error: error.message, success: false });
  // Continue processing other articles
}
```

**Useful for**: Graceful handling when some article sources fail

### 4. Repository Pattern

**Location**: `src/lib/server/storage.ts`

```typescript
class StorageRepository {
  async getFiles(userId: string, options: QueryOptions): Promise<File[]>
  async uploadFile(userId: string, file: FileData): Promise<File>
  async deleteFile(userId: string, fileId: string): Promise<void>
}
```

**Useful for**: Encapsulating all article/digest database operations

### 5. API Layer with Mock Toggle

**Location**: `src/lib/api.ts`

```typescript
const USE_MOCK_DATA = false; // Toggle for development

async function request<T>(method, path, body?) {
  if (USE_MOCK_DATA) {
    return getMockResponse<T>(path);
  }
  // Real API call
}
```

**Useful for**: Development without hitting real Tavily/news APIs

### 6. Tiered Warning System

**Location**: `src/lib/components/StorageMeter.svelte`

```typescript
const WARNING_THRESHOLD = 0.80;  // 80% - show warning
const CRITICAL_THRESHOLD = 0.95; // 95% - show critical
const FULL_THRESHOLD = 1.00;     // 100% - block actions

const status = $derived(
  usage >= FULL_THRESHOLD ? 'full' :
  usage >= CRITICAL_THRESHOLD ? 'critical' :
  usage >= WARNING_THRESHOLD ? 'warning' : 'normal'
);
```

**Useful for**: Quality score thresholds, article relevance filtering

### 7. Soft-Delete + Cron Cleanup

**Pattern**:
```sql
-- Soft delete
UPDATE articles SET deleted_at = NOW() WHERE id = ?

-- Cron cleanup (daily at 3 AM)
DELETE FROM articles WHERE deleted_at < NOW() - INTERVAL 30 DAY
```

**Useful for**: Article retention, digest archival

### 8. Streaming ZIP/Export

**Location**: `worker/src/services/zipStream.ts`

Uses `fflate` for streaming compression without loading into memory.

**Useful for**: Exporting user's digest history, batch downloads

---

## Testing Strategy

**Location**: `vitest.config.ts`

```javascript
coverage: {
  provider: 'v8',
  lines: 80,
  functions: 80,
  branches: 80,
  statements: 80
}
```

**Pattern**: 80% minimum coverage mandate

---

## Component Architecture

```
src/
├── routes/
│   ├── (app)/          # Main routes
│   └── api/            # API endpoints
├── lib/
│   ├── components/     # Svelte components
│   ├── server/         # Server-side logic
│   ├── types/          # TypeScript interfaces
│   ├── api.ts          # API client
│   └── stores.ts       # State management
```

---

## Files to Read First

1. `worker/src/services/ExportJob.ts` - DO implementation
2. `src/lib/server/storage.ts` - Repository pattern
3. `src/lib/api.ts` - API abstraction
4. `src/lib/components/StorageMeter.svelte` - Tiered warnings
5. `AGENT.md` - Project conventions

---

## Path Aliases

```javascript
// svelte.config.js
$lib → ./src/lib
$components → ./src/lib/components
$server → ./src/lib/server
$types → ./src/lib/types
```

---

## Cleanup After Reference

```bash
rm -rf /tmp/amber-ref
```
