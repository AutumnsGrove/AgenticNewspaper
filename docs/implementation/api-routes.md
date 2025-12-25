# API Routes Documentation

This document describes the Cloudflare Workers API endpoints.

## Base URL

```
Production: https://clearing.autumnsgrove.com/api
Development: http://localhost:8787/api
```

## Authentication

All authenticated endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <jwt-token>
```

## Endpoints

### Authentication

#### POST /api/auth/register

Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "token": "eyJ...",
  "user": {
    "id": "user_abc123",
    "email": "user@example.com",
    "name": "John Doe",
    "subscriptionTier": "free"
  }
}
```

#### POST /api/auth/login

Authenticate and receive JWT token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Response:**
```json
{
  "token": "eyJ...",
  "user": {
    "id": "user_abc123",
    "email": "user@example.com",
    "subscriptionTier": "basic"
  }
}
```

#### POST /api/auth/logout

Invalidate current session (requires auth).

#### POST /api/auth/refresh

Refresh JWT token (requires auth).

**Response:**
```json
{
  "token": "eyJ..."
}
```

### User Management

#### GET /api/users/me

Get current user profile (requires auth).

**Response:**
```json
{
  "id": "user_abc123",
  "email": "user@example.com",
  "name": "John Doe",
  "subscriptionTier": "basic",
  "emailVerified": true,
  "createdAt": "2025-01-15T10:00:00Z"
}
```

#### PATCH /api/users/me

Update user profile (requires auth).

**Request:**
```json
{
  "name": "Jane Doe"
}
```

### Preferences

#### GET /api/preferences

Get user preferences (requires auth).

**Response:**
```json
{
  "topics": [
    {
      "name": "AI",
      "keywords": ["artificial intelligence", "machine learning"],
      "priority": 5,
      "enabled": true
    }
  ],
  "delivery": {
    "frequency": "daily_am",
    "deliveryTimeUtc": "06:00",
    "channels": ["web", "email"],
    "timezone": "America/New_York"
  },
  "style": {
    "tone": "hn-style",
    "skepticismLevel": 3,
    "technicalDepth": 4,
    "includeBiasAnalysis": true,
    "includeCrossConnections": true,
    "maxArticlesPerTopic": 5
  }
}
```

#### PATCH /api/preferences

Update preferences (requires auth).

#### POST /api/preferences/topics

Add a new topic (requires auth).

**Request:**
```json
{
  "name": "Science",
  "keywords": ["research", "discovery"],
  "priority": 4,
  "enabled": true
}
```

#### DELETE /api/preferences/topics/:name

Remove a topic (requires auth).

### Digests

#### GET /api/digests

List user's digests (requires auth).

**Query Parameters:**
- `limit`: Number of digests (default: 10, max: 50)
- `offset`: Pagination offset

**Response:**
```json
{
  "digests": [
    {
      "id": "digest_abc123",
      "title": "Morning Brief",
      "createdAt": "2025-01-15T06:00:00Z",
      "articleCount": 15,
      "averageQuality": 0.82
    }
  ],
  "total": 42
}
```

#### GET /api/digests/latest

Get the most recent digest (requires auth).

**Response:**
```json
{
  "id": "digest_abc123",
  "title": "Morning Brief",
  "subtitle": "Your personalized news digest",
  "createdAt": "2025-01-15T06:00:00Z",
  "articles": [...],
  "connections": [...],
  "metadata": {
    "totalArticles": 15,
    "averageQuality": 0.82,
    "topicCoverage": {
      "AI": 5,
      "Technology": 4,
      "Science": 3
    }
  }
}
```

#### GET /api/digests/:id

Get a specific digest (requires auth).

#### POST /api/digests/generate

Start digest generation (requires auth).

**Request:**
```json
{
  "topics": ["AI", "Technology"]
}
```

**Response:**
```json
{
  "jobId": "job_xyz789",
  "status": "pending"
}
```

#### GET /api/digests/status/:jobId

Check generation job status (requires auth).

**Response:**
```json
{
  "jobId": "job_xyz789",
  "status": "in_progress",
  "progress": 45,
  "currentStep": "Analyzing articles..."
}
```

Or when complete:
```json
{
  "jobId": "job_xyz789",
  "status": "completed",
  "progress": 100,
  "digestId": "digest_abc123"
}
```

#### POST /api/digests/:id/feedback

Submit article feedback (requires auth).

**Request:**
```json
{
  "articleId": "article_123",
  "feedback": "helpful"
}
```

### RSS Feeds

#### GET /api/rss/:userId

Get user's RSS feed (public, uses user token in URL).

**Response:** RSS 2.0 XML feed

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>The Daily Clearing - John's Feed</title>
    <link>https://clearing.autumnsgrove.com</link>
    <description>Personalized news digest</description>
    <item>
      <title>Morning Brief - Jan 15, 2025</title>
      <link>https://clearing.autumnsgrove.com/digest/abc123</link>
      <pubDate>Wed, 15 Jan 2025 06:00:00 GMT</pubDate>
      <description>...</description>
    </item>
  </channel>
</rss>
```

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is required",
    "details": {
      "field": "email"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid auth token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

## Rate Limits

| Tier | Digests/Day | API Calls/Hour |
|------|-------------|----------------|
| Free | 1 | 100 |
| Basic | 3 | 500 |
| Pro | 10 | 2000 |

## Webhooks (Coming Soon)

Subscribe to digest generation events:

```json
{
  "event": "digest.generated",
  "data": {
    "digestId": "digest_abc123",
    "userId": "user_xyz",
    "articleCount": 15
  }
}
```
