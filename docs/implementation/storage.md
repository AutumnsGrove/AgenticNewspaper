# Storage Documentation

This document describes the storage systems used in The Daily Clearing.

## Overview

The system uses multiple Cloudflare storage services:
- **D1**: User data, preferences, digest metadata
- **R2**: Full digest content, cached articles
- **KV**: Session tokens, rate limiting

## R2 Object Storage

Located at: `packages/worker/src/services/storage.ts`

### Bucket Structure

```
clearing-bucket/
├── digests/
│   └── {userId}/
│       └── {digestId}/
│           ├── digest.json      # Full digest data
│           ├── digest.md        # Markdown version
│           └── digest.html      # HTML version (optional)
├── articles/
│   └── {articleHash}/
│       └── content.json         # Cached article content
└── exports/
    └── {userId}/
        └── {exportId}.json      # User data exports
```

### Storing Digests

```typescript
export async function storeDigest(
  env: Env,
  userId: string,
  digestId: string,
  digest: Digest,
  markdown: string,
  html?: string
): Promise<string> {
  const baseKey = `digests/${userId}/${digestId}`;

  // Store JSON
  await env.R2_BUCKET.put(
    `${baseKey}/digest.json`,
    JSON.stringify(digest),
    {
      httpMetadata: {
        contentType: 'application/json',
      },
      customMetadata: {
        userId,
        digestId,
        createdAt: new Date().toISOString(),
      },
    }
  );

  // Store Markdown
  await env.R2_BUCKET.put(
    `${baseKey}/digest.md`,
    markdown,
    {
      httpMetadata: {
        contentType: 'text/markdown',
      },
    }
  );

  // Store HTML if provided
  if (html) {
    await env.R2_BUCKET.put(
      `${baseKey}/digest.html`,
      html,
      {
        httpMetadata: {
          contentType: 'text/html',
        },
      }
    );
  }

  return baseKey;
}
```

### Retrieving Digests

```typescript
export async function getDigest(
  env: Env,
  userId: string,
  digestId: string
): Promise<StoredDigest | null> {
  const key = `digests/${userId}/${digestId}/digest.json`;
  const object = await env.R2_BUCKET.get(key);

  if (!object) return null;

  const digest = await object.json<Digest>();

  return {
    digest,
    metadata: {
      etag: object.etag,
      uploaded: object.uploaded,
      size: object.size,
    },
  };
}
```

### Listing User Digests

```typescript
export async function listUserDigests(
  env: Env,
  userId: string,
  limit = 20
): Promise<string[]> {
  const prefix = `digests/${userId}/`;
  const listed = await env.R2_BUCKET.list({
    prefix,
    limit,
    delimiter: '/',
  });

  // Extract digest IDs from prefixes
  return listed.delimitedPrefixes.map((p) =>
    p.replace(prefix, '').replace('/', '')
  );
}
```

### Deleting Digests

```typescript
export async function deleteDigest(
  env: Env,
  userId: string,
  digestId: string
): Promise<void> {
  const prefix = `digests/${userId}/${digestId}/`;
  const listed = await env.R2_BUCKET.list({ prefix });

  await Promise.all(
    listed.objects.map((obj) => env.R2_BUCKET.delete(obj.key))
  );
}
```

## KV Storage

Used for session tokens and caching.

### Session Management

```typescript
// Store session
await env.KV.put(
  `session:${sessionId}`,
  JSON.stringify({
    userId,
    createdAt: Date.now(),
  }),
  {
    expirationTtl: 7 * 24 * 60 * 60, // 7 days
  }
);

// Get session
const session = await env.KV.get(`session:${sessionId}`, 'json');

// Delete session
await env.KV.delete(`session:${sessionId}`);
```

### Rate Limiting

```typescript
// Check rate limit
const key = `ratelimit:${userId}:${action}`;
const current = parseInt(await env.KV.get(key) || '0');

if (current >= limit) {
  throw new RateLimitError('Too many requests');
}

// Increment counter
await env.KV.put(key, String(current + 1), {
  expirationTtl: windowSeconds,
});
```

### Feature Flags

```typescript
// Get feature flag
const enabled = await env.KV.get(`feature:${flagName}`) === 'true';

// Set feature flag
await env.KV.put(`feature:${flagName}`, 'true');
```

## Wrangler Configuration

```toml
# wrangler.toml

[[r2_buckets]]
binding = "R2_BUCKET"
bucket_name = "clearing-digests"

[[kv_namespaces]]
binding = "KV"
id = "abc123..."

[[d1_databases]]
binding = "DB"
database_name = "clearing-db"
database_id = "def456..."
```

## Storage Patterns

### Content Deduplication

Hash-based storage prevents duplicate article storage:

```typescript
function getArticleHash(url: string, content: string): string {
  const data = `${url}:${content}`;
  return crypto.subtle.digest('SHA-256', new TextEncoder().encode(data))
    .then((hash) => Array.from(new Uint8Array(hash))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join(''));
}

// Store article by hash
const hash = await getArticleHash(article.url, article.content);
const key = `articles/${hash}/content.json`;

const existing = await env.R2_BUCKET.head(key);
if (!existing) {
  await env.R2_BUCKET.put(key, JSON.stringify(article));
}
```

### Conditional Requests

Use ETags for efficient caching:

```typescript
export async function getDigestIfModified(
  env: Env,
  userId: string,
  digestId: string,
  ifNoneMatch?: string
): Promise<StoredDigest | null | 'not_modified'> {
  const key = `digests/${userId}/${digestId}/digest.json`;
  const object = await env.R2_BUCKET.get(key, {
    onlyIf: ifNoneMatch ? { etagDoesNotMatch: ifNoneMatch } : undefined,
  });

  if (object === null) {
    // Check if it exists at all
    const head = await env.R2_BUCKET.head(key);
    return head ? 'not_modified' : null;
  }

  return {
    digest: await object.json(),
    metadata: { etag: object.etag },
  };
}
```

### Multipart Uploads

For large digests, use multipart uploads:

```typescript
export async function storeLargeDigest(
  env: Env,
  key: string,
  content: ReadableStream
): Promise<void> {
  const upload = await env.R2_BUCKET.createMultipartUpload(key);

  try {
    const parts: R2UploadedPart[] = [];
    let partNumber = 1;

    // Upload in chunks
    for await (const chunk of content) {
      const part = await upload.uploadPart(partNumber, chunk);
      parts.push(part);
      partNumber++;
    }

    await upload.complete(parts);
  } catch (error) {
    await upload.abort();
    throw error;
  }
}
```

## Error Handling

```typescript
try {
  await env.R2_BUCKET.put(key, content);
} catch (error) {
  if (error instanceof Error) {
    if (error.message.includes('EntityTooLarge')) {
      throw new StorageError('Content too large', 413);
    }
    if (error.message.includes('QuotaExceeded')) {
      throw new StorageError('Storage quota exceeded', 507);
    }
  }
  throw error;
}
```

## Cleanup and Maintenance

### Automatic Expiration

Use R2 lifecycle rules for automatic cleanup:

```typescript
// Objects older than 90 days in exports/ are deleted
// Configure via Cloudflare dashboard
```

### Manual Cleanup

```typescript
export async function cleanupOldDigests(
  env: Env,
  userId: string,
  keepCount: number
): Promise<number> {
  const allDigests = await listUserDigests(env, userId, 1000);

  if (allDigests.length <= keepCount) return 0;

  // Sort by date (assuming ID contains timestamp)
  const sorted = allDigests.sort().reverse();
  const toDelete = sorted.slice(keepCount);

  await Promise.all(
    toDelete.map((id) => deleteDigest(env, userId, id))
  );

  return toDelete.length;
}
```

## Performance Tips

### 1. Batch Operations

```typescript
// Good: Parallel uploads
await Promise.all([
  env.R2_BUCKET.put('key1', content1),
  env.R2_BUCKET.put('key2', content2),
  env.R2_BUCKET.put('key3', content3),
]);

// Avoid: Sequential uploads
await env.R2_BUCKET.put('key1', content1);
await env.R2_BUCKET.put('key2', content2);
await env.R2_BUCKET.put('key3', content3);
```

### 2. Use head() for Existence Checks

```typescript
// Good: Metadata only
const exists = await env.R2_BUCKET.head(key);

// Avoid: Full download
const object = await env.R2_BUCKET.get(key);
```

### 3. Range Requests for Large Files

```typescript
// Read first 1KB only
const object = await env.R2_BUCKET.get(key, {
  range: { offset: 0, length: 1024 },
});
```
