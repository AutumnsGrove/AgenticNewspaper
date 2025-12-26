# The Daily Clearing

An intelligent news aggregator that uses AI agents to curate, analyze, and synthesize personalized news digests in a Hacker News style.

## 🎯 Project Overview

This project implements a sophisticated multi-agent system using OpenRouter (DeepSeek V3.2) and Anthropic's Claude for AI processing, with dual deployment options: self-hosted Python or cloud-hosted Cloudflare Workers. The system searches, fetches, analyzes, and synthesizes articles based on your interests, delivering high-quality summaries with technical depth and skeptical analysis.

**Project Status:** Implementation Complete (~90%) + Polish
**Current State:** Python package working end-to-end, TypeScript services ported, Web UI deployed
**Cost per Digest:** ~$0.0034 (well under budget)

## 📁 Project Structure

```
AgenticNewspaper/
├── README.md                    # You are here!
├── TODOS.md                     # Current development status & next steps
├── HANDOFF.md                   # Latest session handoff documentation
├── CLAUDE.md                    # Project instructions for Claude Code
├── .gitignore                   # Git exclusions (secrets, cache, etc.)
│
├── packages/                    # Monorepo packages
│   ├── core/                    # Python package (self-hosted)
│   │   ├── src/                 # Source code
│   │   │   ├── agents/          # Tier 1 & 2 AI agents
│   │   │   ├── services/        # Search, fetch, parser services
│   │   │   ├── providers/       # OpenRouter, Anthropic LLM providers
│   │   │   ├── orchestrator/    # Main digest orchestrator
│   │   │   └── main.py          # CLI entry point
│   │   ├── config/              # Configuration files
│   │   ├── outputs/             # Generated digests
│   │   └── tests/               # Test suite
│   │
│   ├── worker/                  # TypeScript package (Cloudflare Workers)
│   │   ├── src/
│   │   │   ├── services/        # Ported services (search, llm, parser, digest)
│   │   │   ├── api/             # API routes & test endpoints
│   │   │   └── index.ts         # Worker entry point
│   │   ├── schemas/             # D1 database migrations
│   │   └── wrangler.toml        # Cloudflare configuration
│   │
│   └── web/                     # SvelteKit web frontend
│       ├── src/
│       │   ├── lib/             # Components, stores, utilities
│       │   ├── routes/          # SvelteKit routes
│       │   └── hooks.server.ts  # Authentication hooks
│       └── tests/               # Vitest tests
│
├── shared/                      # Shared resources
│   └── prompts.json             # Unified AI prompts for both packages
│
├── docs/                        # Documentation
│   ├── v3-spec-hybrid-architecture.md   # Latest architecture spec (v3)
│   ├── implementation/          # Implementation details
│   │   ├── README.md
│   │   ├── agents.md            # Agent architecture
│   │   ├── api-routes.md        # API documentation
│   │   └── durable-objects.md   # Cloudflare DO setup
│   └── specs/                   # Historical specs (v1, v2)
│
└── AgentUsage/                  # Claude Code guides & patterns
    └── README.md                # Guide index
```

## 🚀 Quick Start

### For New Users

Choose your deployment path:

**Option 1: Self-Hosted (Python) - Recommended for local use**
```bash
cd packages/core
uv sync                           # Install dependencies
cp secrets_template.json secrets.json  # Add your API keys
uv run python src/main.py         # Generate your first digest!
# Output: outputs/daily_digests/YYYY-MM-DD.md
```

**Option 2: Cloud-Hosted (Cloudflare Workers)**
```bash
cd packages/worker
pnpm install                      # Install dependencies
cp .dev.vars.example .dev.vars    # Add your API keys
pnpm run dev                      # Start dev server
# Test: curl http://localhost:8787/api/test/generate-digest
```

**Option 3: Web UI**
```bash
cd packages/web
pnpm install
pnpm run dev
# Visit: http://localhost:5173
```

### For Developers

1. **Understand the architecture:**
   - Read [`HANDOFF.md`](HANDOFF.md) - Latest session status & what's working
   - Read [`docs/v3-spec-hybrid-architecture.md`](docs/v3-spec-hybrid-architecture.md) - Current architecture (v3)
   - Check [`docs/implementation/README.md`](docs/implementation/README.md) - Implementation details

2. **Next development tasks:**
   - Read [`TODOS.md`](TODOS.md) - Current priorities and next steps
   - See TypeScript worker testing checklist
   - Review Python package FastAPI wrapper plans

3. **Contributing:**
   - Follow [`CLAUDE.md`](CLAUDE.md) - Project instructions and conventions
   - Check [`AgentUsage/README.md`](AgentUsage/README.md) - Development guides

## 📖 Key Documentation

### Essential Reading

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [`HANDOFF.md`](HANDOFF.md) | **Latest session status** | First - what's working now |
| [`v3-spec-hybrid-architecture.md`](docs/v3-spec-hybrid-architecture.md) | **Current architecture (v3)** | Second - understand dual deployment |
| [`TODOS.md`](TODOS.md) | **Current tasks & next steps** | Always - track what's needed |
| [`implementation/README.md`](docs/implementation/README.md) | **Implementation details** | When coding - technical reference |
| [`CLAUDE.md`](CLAUDE.md) | **Project conventions** | When contributing - follow standards |

### Package-Specific

| Document | Purpose |
|----------|---------|
| [`packages/core/README.md`](packages/core/README.md) | Python package - self-hosted deployment |
| [`packages/worker/README.md`](packages/worker/README.md) | TypeScript worker - Cloudflare deployment |
| [`packages/web/README.md`](packages/web/README.md) | SvelteKit frontend - web UI |

### Implementation Details

| Document | Purpose |
|----------|---------|
| [`docs/implementation/agents.md`](docs/implementation/agents.md) | AI agent architecture & prompts |
| [`docs/implementation/api-routes.md`](docs/implementation/api-routes.md) | API endpoint documentation |
| [`docs/implementation/durable-objects.md`](docs/implementation/durable-objects.md) | Cloudflare Durable Objects setup |

### Historical (v1, v2)

The `docs/specs/` and `docs/architecture/` folders contain earlier specs for reference. Always use v3 docs for current work.

## 🏗️ System Architecture

### Dual Deployment Model

```
┌──────────────────────────────────────────────────────────────────────┐
│                          THE DAILY CLEARING                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────┐     ┌──────────────────────────────┐   │
│  │  Python Package (core)  │     │  TypeScript Worker (worker)  │   │
│  ├─────────────────────────┤     ├──────────────────────────────┤   │
│  │  ✅ Working End-to-End  │     │  ✅ Services Ported          │   │
│  │  - Self-hosted          │     │  - Cloudflare Workers        │   │
│  │  - Hetzner VPS          │     │  - Edge deployment           │   │
│  │  - Local installs       │     │  - D1 + R2 storage           │   │
│  │  - CLI: python main.py  │     │  - API endpoints             │   │
│  └─────────────────────────┘     └──────────────────────────────┘   │
│           100% INDEPENDENT              100% INDEPENDENT            │
└──────────────────────────────────────────────────────────────────────┘

                      ┌────────────────────┐
                      │  Web Frontend (web)│
                      ├────────────────────┤
                      │  ✅ UI Complete    │
                      │  - SvelteKit       │
                      │  - Cloudflare Pages│
                      │  - Auth integrated │
                      └────────────────────┘
```

### Agent Tiers (Both Packages)

- **Tier 1 (Execution):** Search, Fetch, Parser - Fast, simple tasks (DeepSeek/Haiku)
- **Tier 2 (Reasoning):** Quality, Bias, Synthesis - Deep analysis (DeepSeek/Sonnet)

### Technology Stack

**Python Package:**
- Language: Python 3.11+
- Package Manager: UV
- LLM: OpenRouter (DeepSeek V3.2) primary, Anthropic fallback
- Search: Tavily API
- Output: CLI-generated markdown digests

**TypeScript Worker:**
- Language: TypeScript
- Runtime: Cloudflare Workers
- Storage: D1 (SQLite), R2 (object storage)
- LLM: OpenRouter (DeepSeek V3.2)
- Search: Tavily API
- Output: API endpoints, stored in R2

**Web Frontend:**
- Framework: SvelteKit 5
- Deployment: Cloudflare Pages
- Auth: GroveAuth OAuth 2.0
- UI: Bifold newspaper-style layout

See [`docs/v3-spec-hybrid-architecture.md`](docs/v3-spec-hybrid-architecture.md) for complete architecture details.

## 📅 Development Status

### ✅ Completed

**Phase 1-2: Core Implementation** (Dec 2025)
- ✅ Python package with full digest generation
- ✅ OpenRouter/DeepSeek integration (primary)
- ✅ Anthropic Claude fallback provider
- ✅ Tavily search integration
- ✅ Article parsing and synthesis
- ✅ HN-style digest output
- ✅ Cost tracking ($0.0034/digest)
- ✅ TypeScript services ported
- ✅ Web frontend with auth

### 🚧 In Progress

**Phase 3: Testing & Polish**
- [ ] TypeScript worker local testing
- [ ] Python FastAPI HTTP wrapper
- [ ] Deployment automation
- [ ] End-to-end integration tests
- [ ] Production monitoring

### 📋 Planned

**Phase 4: Advanced Features**
- Bias detection & multi-perspective analysis
- Fact verification
- Historical trend analysis
- Email/RSS delivery
- Scheduled digest generation

See [`TODOS.md`](TODOS.md) for detailed current priorities and next steps.

## 🎨 Features

### ✅ Implemented

**Core Digest Generation:**
- ✅ Multi-topic news search via Tavily API
- ✅ Intelligent article fetching & parsing
- ✅ Quality scoring & filtering
- ✅ Hacker News-style skeptical synthesis
- ✅ Daily digest generation (markdown output)
- ✅ Cost tracking (~$0.0034 per digest)

**Dual Deployment:**
- ✅ Self-hosted Python CLI package
- ✅ Cloudflare Workers TypeScript services
- ✅ Unified prompts across both implementations
- ✅ Independent operation (no cross-dependencies)

**Web Interface:**
- ✅ SvelteKit 5 bifold newspaper layout
- ✅ GroveAuth OAuth 2.0 authentication
- ✅ Responsive design
- ✅ User preferences UI
- ✅ Digest history browsing

**Infrastructure:**
- ✅ Cloudflare D1 database (7 tables)
- ✅ R2 object storage for digests
- ✅ Test endpoints for all services
- ✅ Environment configuration

### 📋 Planned

**Advanced Analysis:**
- ⏳ Bias detection & multi-perspective analysis
- ⏳ Fact verification
- ⏳ Cross-story connection finding
- ⏳ Source credibility scoring

**Delivery & Automation:**
- ⏳ Email delivery (Resend integration)
- ⏳ RSS feed generation
- ⏳ Scheduled digest generation (cron/Workers)
- ⏳ On-demand regeneration

**Polish & Scale:**
- ⏳ Historical trend analysis
- ⏳ Python FastAPI HTTP wrapper
- ⏳ Comprehensive testing suite
- ⏳ Production monitoring & alerts

## 🔧 Configuration

### API Keys Required

| Key | Service | Where to Get | Used By |
|-----|---------|--------------|---------|
| `OPENROUTER_API_KEY` | LLM (DeepSeek V3.2) | https://openrouter.ai | Both packages |
| `TAVILY_API_KEY` | Search | https://tavily.com | Both packages |
| `ANTHROPIC_API_KEY` | LLM fallback (optional) | https://console.anthropic.com | Both packages |

### Python Package Configuration

**File:** `packages/core/secrets.json`
```json
{
  "openrouter_api_key": "sk-or-v1-...",
  "tavily_api_key": "tvly-...",
  "anthropic_api_key": "sk-ant-api03-..."
}
```

**File:** `packages/core/config/user_preferences.yaml`
```yaml
topics:
  - name: "AI & ML"
    keywords: ["LLM", "transformer", "deep learning"]
  - name: "Climate Tech"
    keywords: ["renewable energy", "carbon capture"]

sources:
  - "Hacker News"
  - "Ars Technica"
  - "Nature.com"

style:
  technical_depth: high
  skepticism_level: moderate
  summary_length: medium
```

### TypeScript Worker Configuration

**File:** `packages/worker/.dev.vars`
```bash
ENVIRONMENT=development
OPENROUTER_API_KEY=sk-or-v1-...
TAVILY_API_KEY=tvly-...
JWT_SECRET=your-random-secret
```

**Production secrets (Cloudflare):**
```bash
wrangler secret put OPENROUTER_API_KEY
wrangler secret put TAVILY_API_KEY
wrangler secret put JWT_SECRET
```

### Web Frontend Configuration

**File:** `packages/web/.env`
```bash
# Points to Cloudflare Worker API
PUBLIC_API_URL=https://your-worker.workers.dev
```

**Note:** All `secrets.json`, `.dev.vars`, and `.env` files are gitignored.

## 📊 Cost Analysis

**Current Performance (Dec 2025):**
- **Per Digest:** ~$0.0034 USD
- **Daily Budget:** $0.30
- **Digests per Day:** ~85 possible (way over target!)

**Cost Breakdown:**
| Operation | Tokens | Cost |
|-----------|--------|------|
| Search query generation | ~100 | $0.00003 |
| Relevance scoring (per article) | ~100 | $0.00003 |
| Topic synthesis (3 topics) | ~1500 | $0.0002 |
| **Full digest (3 topics, 15 articles)** | **~5000** | **~$0.0034** |

**Why so cheap?**
- Using DeepSeek V3.2 via OpenRouter ($0.27/$0.55 per 1M tokens)
- 90% cost savings vs. Claude Sonnet
- Smart prompt engineering
- Efficient token usage

See [`docs/v3-spec-hybrid-architecture.md`](docs/v3-spec-hybrid-architecture.md) for detailed cost analysis.

## 🤝 Contributing

This is currently a personal project. Development tracking:
- [`TODOS.md`](TODOS.md) - Current priorities & next steps
- [`HANDOFF.md`](HANDOFF.md) - Latest session status
- GitHub Issues - Bug reports & feature requests

**Development Guidelines:**
- Read [`CLAUDE.md`](CLAUDE.md) for project conventions
- Check [`AgentUsage/README.md`](AgentUsage/README.md) for Claude Code patterns
- Follow existing code style
- Add tests for new features
- Update documentation

## 📝 License

MIT License (to be added)

## 🔗 Useful Links

**External Services:**
- [OpenRouter](https://openrouter.ai) - LLM provider (DeepSeek V3.2)
- [Tavily API](https://tavily.com) - News search
- [Anthropic Console](https://console.anthropic.com) - Fallback LLM
- [Cloudflare Dashboard](https://dash.cloudflare.com) - Workers, D1, R2

**Documentation:**
- [Architecture (v3)](docs/v3-spec-hybrid-architecture.md) - Current system design
- [Implementation Docs](docs/implementation/README.md) - Technical details
- [HANDOFF.md](HANDOFF.md) - What's working now

**Deployment:**
- Web UI: `clearing.autumnsgrove.com` (Cloudflare Pages)
- Auth: GroveAuth OAuth 2.0 (`heartwood.grove.place`)

---

**Last Updated:** December 26, 2025
**Version:** 0.9.0 (Beta)
**Status:** Implementation ~90% Complete

*Built with Python, TypeScript, SvelteKit, and Cloudflare*
*Powered by DeepSeek V3.2 via OpenRouter*
