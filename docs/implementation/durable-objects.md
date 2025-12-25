# Durable Objects Documentation

This document describes the Cloudflare Durable Objects used for per-user state management.

## Overview

Durable Objects provide:
- Strong consistency for user state
- Real-time coordination
- Persistent storage per instance
- Location-aware routing

## Durable Objects

### DigestJob

Located at: `packages/worker/src/services/DigestJob.ts`

Manages digest generation jobs with progress tracking.

```typescript
export class DigestJob implements DurableObject {
  private state: DurableObjectState;
  private articles: Map<string, Article>;
  private progress: number;
  private status: 'pending' | 'in_progress' | 'completed' | 'failed';

  constructor(state: DurableObjectState) {
    this.state = state;
    this.articles = new Map();
    this.progress = 0;
    this.status = 'pending';
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    switch (url.pathname) {
      case '/start':
        return this.handleStart(request);
      case '/status':
        return this.handleStatus();
      case '/article':
        return this.handleArticle(request);
      case '/complete':
        return this.handleComplete(request);
      default:
        return new Response('Not found', { status: 404 });
    }
  }
}
```

**Operations:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/start` | POST | Start job with topics |
| `/status` | GET | Get current progress |
| `/article` | POST | Add processed article |
| `/complete` | POST | Mark job complete |

**State Schema:**

```typescript
interface JobState {
  id: string;
  userId: string;
  topics: string[];
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number;
  currentStep: string;
  articles: Article[];
  digestId?: string;
  error?: string;
  startedAt: string;
  completedAt?: string;
}
```

**Usage from Worker:**

```typescript
// Get job instance
const id = env.DIGEST_JOB.idFromName(`${userId}:${jobId}`);
const job = env.DIGEST_JOB.get(id);

// Start generation
await job.fetch(new Request('https://do/start', {
  method: 'POST',
  body: JSON.stringify({ topics: ['AI', 'Technology'] }),
}));

// Check status
const status = await job.fetch(new Request('https://do/status'));
const data = await status.json();
console.log(data.progress); // 45
```

### UserState

Located at: `packages/worker/src/services/UserState.ts`

Manages per-user state including preferences and learning data.

```typescript
export class UserState implements DurableObject {
  private state: DurableObjectState;
  private preferences: UserPreferences;
  private feedbackHistory: FeedbackEntry[];
  private topicWeights: Map<string, number>;

  constructor(state: DurableObjectState) {
    this.state = state;
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    switch (url.pathname) {
      case '/preferences':
        return this.handlePreferences(request);
      case '/feedback':
        return this.handleFeedback(request);
      case '/learn':
        return this.handleLearn(request);
      case '/weights':
        return this.handleWeights();
      default:
        return new Response('Not found', { status: 404 });
    }
  }
}
```

**Operations:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/preferences` | GET/PUT | Get or update preferences |
| `/feedback` | POST | Record article feedback |
| `/learn` | POST | Trigger learning from feedback |
| `/weights` | GET | Get topic weights |

**Feedback Learning:**

The UserState object learns from feedback to personalize future digests:

```typescript
async handleFeedback(request: Request): Promise<Response> {
  const { articleId, feedback, topics } = await request.json();

  // Record feedback
  this.feedbackHistory.push({
    articleId,
    feedback,
    topics,
    timestamp: Date.now(),
  });
  await this.state.storage.put('feedbackHistory', this.feedbackHistory);

  // Update topic weights
  const weightDelta = feedback === 'helpful' ? 0.1 : -0.1;
  for (const topic of topics) {
    const current = this.topicWeights.get(topic) ?? 1.0;
    this.topicWeights.set(topic, Math.max(0.1, Math.min(2.0, current + weightDelta)));
  }
  await this.state.storage.put('topicWeights', Object.fromEntries(this.topicWeights));

  return new Response(JSON.stringify({ success: true }));
}
```

## Wrangler Configuration

```toml
# wrangler.toml

[[durable_objects.bindings]]
name = "DIGEST_JOB"
class_name = "DigestJob"

[[durable_objects.bindings]]
name = "USER_STATE"
class_name = "UserState"

[[migrations]]
tag = "v1"
new_classes = ["DigestJob", "UserState"]
```

## Naming Conventions

### DigestJob IDs

Format: `{userId}:{jobId}`

```typescript
const jobId = crypto.randomUUID();
const doId = env.DIGEST_JOB.idFromName(`${userId}:${jobId}`);
```

### UserState IDs

Format: `{userId}`

```typescript
const doId = env.USER_STATE.idFromName(userId);
```

## Storage

Durable Objects have built-in key-value storage:

```typescript
// Write
await this.state.storage.put('key', value);
await this.state.storage.put({ key1: value1, key2: value2 });

// Read
const value = await this.state.storage.get('key');
const values = await this.state.storage.get(['key1', 'key2']);

// Delete
await this.state.storage.delete('key');
await this.state.storage.deleteAll();

// List
const entries = await this.state.storage.list({ prefix: 'article:' });
```

## Alarms

Schedule future work with alarms:

```typescript
// Set alarm
await this.state.storage.setAlarm(Date.now() + 60000); // 1 minute

// Handle alarm
async alarm(): Promise<void> {
  // Cleanup expired jobs
  if (this.status === 'in_progress' && this.isExpired()) {
    this.status = 'failed';
    this.error = 'Job timed out';
    await this.state.storage.put('status', this.status);
  }
}
```

## WebSocket Support

Durable Objects support WebSocket for real-time updates:

```typescript
async fetch(request: Request): Promise<Response> {
  if (request.headers.get('Upgrade') === 'websocket') {
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);

    this.state.acceptWebSocket(server);

    return new Response(null, { status: 101, webSocket: client });
  }
}

async webSocketMessage(ws: WebSocket, message: string): Promise<void> {
  // Handle incoming message
  const data = JSON.parse(message);

  // Broadcast to all connected clients
  this.state.getWebSockets().forEach((socket) => {
    socket.send(JSON.stringify({ type: 'update', data }));
  });
}
```

## Error Handling

```typescript
async fetch(request: Request): Promise<Response> {
  try {
    // Process request
    return await this.processRequest(request);
  } catch (error) {
    // Log error
    console.error('Durable Object error:', error);

    // Return error response
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
```

## Best Practices

### 1. Keep Objects Small

Each Durable Object should manage a focused piece of state:
- DigestJob: Single job lifecycle
- UserState: Single user's preferences

### 2. Batch Storage Operations

```typescript
// Good - single write
await this.state.storage.put({
  status: 'completed',
  completedAt: new Date().toISOString(),
  digestId: digest.id,
});

// Avoid - multiple writes
await this.state.storage.put('status', 'completed');
await this.state.storage.put('completedAt', new Date().toISOString());
await this.state.storage.put('digestId', digest.id);
```

### 3. Handle Cold Starts

```typescript
constructor(state: DurableObjectState) {
  this.state = state;
  // Load state on first request, not constructor
  this.initialized = false;
}

private async ensureInitialized(): Promise<void> {
  if (this.initialized) return;

  const stored = await this.state.storage.get([
    'preferences',
    'feedbackHistory',
    'topicWeights',
  ]);

  this.preferences = stored.get('preferences') ?? defaultPreferences;
  this.feedbackHistory = stored.get('feedbackHistory') ?? [];
  this.topicWeights = new Map(Object.entries(stored.get('topicWeights') ?? {}));

  this.initialized = true;
}
```

### 4. Clean Up Old Data

Use alarms to clean up expired data:

```typescript
async alarm(): Promise<void> {
  // Clean up old feedback entries
  const oneMonthAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;
  this.feedbackHistory = this.feedbackHistory.filter(
    (f) => f.timestamp > oneMonthAgo
  );
  await this.state.storage.put('feedbackHistory', this.feedbackHistory);

  // Schedule next cleanup
  await this.state.storage.setAlarm(Date.now() + 24 * 60 * 60 * 1000);
}
```
