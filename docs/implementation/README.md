# Implementation Documentation

This directory contains detailed implementation documentation for The Daily Clearing news aggregator system.

## Package Structure

The system is organized as a monorepo with three main packages:

```
packages/
├── core/           # Python - AI agents, providers, database
├── web/            # TypeScript/Svelte - Frontend application
└── worker/         # TypeScript - Cloudflare Workers API
```

## Documentation Index

### Core Package
- [Agents](./agents.md) - AI agent implementations (Search, Parser, Quality, Bias, Connection)
- [Providers](./providers.md) - LLM provider integrations (OpenRouter, Anthropic)
- [Database](./database.md) - SQLite and D1 database layers
- [Models](./models.md) - Data models (Article, Digest, User)

### Web Package
- [Components](./components.md) - Svelte component architecture
- [Stores](./stores.md) - Svelte stores for state management
- [API Client](./api-client.md) - Frontend API integration

### Worker Package
- [API Routes](./api-routes.md) - Cloudflare Workers API endpoints
- [Durable Objects](./durable-objects.md) - Per-user state management
- [Storage](./storage.md) - R2, D1, and KV integration

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- pnpm
- Wrangler CLI

### Development Setup

```bash
# Install dependencies
pnpm install
cd packages/core && uv sync

# Run tests
pnpm test           # TypeScript tests
uv run pytest       # Python tests

# Start development
pnpm dev            # Web app
wrangler dev        # Worker
```

## Architecture Overview

### Tier 1 Agents (Fast Execution)
- **Search Agent**: Tavily API integration for news discovery
- **Fetch Agent**: HTTP client for article retrieval
- **Parser Agent**: newspaper3k-based content extraction

### Tier 2 Agents (Deep Reasoning)
- **Quality Agent**: Content quality assessment (0-1 score)
- **Bias Agent**: Political bias detection (left/center/right)
- **Connection Agent**: Cross-article similarity analysis

### Cloud Infrastructure
- **Cloudflare Workers**: Edge API deployment
- **D1**: SQLite-compatible distributed database
- **R2**: Object storage for digests
- **Durable Objects**: Stateful user sessions

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your-key
TAVILY_API_KEY=your-key

# Optional (OpenRouter)
OPENROUTER_API_KEY=your-key
```

### Wrangler Configuration

The `wrangler.toml` file configures all Cloudflare bindings:
- D1 database
- R2 bucket
- KV namespace
- Durable Object bindings
