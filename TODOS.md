# The Daily Clearing - Development TODOs

**Project Status:** Split Architecture Implementation
**Last Updated:** December 25, 2025
**Current Session:** Handoff to Web Remote Claude Code

---

## 🎯 Project Architecture

### **Dual Standalone Packages**

```
Python (packages/core)           TypeScript (packages/worker)
├─ Hetzner VPS deployment        ├─ Cloudflare Workers
├─ Local installs                ├─ Edge/serverless
├─ CLI-based                     ├─ API-based
└─ 90% Production Ready ✅       └─ Infrastructure Ready 🔨
```

**CRITICAL:** Both packages must work **100% independently**
- No cross-dependencies
- Same functionality
- Different deployment targets

---

## ✅ COMPLETED (Session 2025-12-25)

### Python Package - WORKING END-TO-END

- [x] Project setup with UV
- [x] Directory structure created
- [x] OpenRouter as PRIMARY provider (DeepSeek V3.2)
- [x] Anthropic as FALLBACK provider
- [x] Real Tavily search integration
- [x] Article fetching and parsing
- [x] HN-style digest synthesis
- [x] Cost tracking ($0.0034 per run)
- [x] Full CLI working: `uv run python src/main.py`
- [x] Test digest generated with real articles

**Output:** `packages/core/outputs/daily_digests/2025-12-25.md`

### Cloudflare Worker - INFRASTRUCTURE

- [x] Wrangler configuration
- [x] D1 database setup and migration (7 tables)
- [x] R2 bucket configuration
- [x] Dev server running (localhost:8787)
- [x] API routes scaffolded
- [x] Test endpoints working
- [x] Environment variables configured

---

## 🚀 PHASE 1: TypeScript Port (NEXT PRIORITY)

**Goal:** Make Cloudflare Worker fully standalone (no Python dependency)

### Step 1: Port Search Service

**File:** `packages/worker/src/services/search.ts`

- [ ] Create Tavily search service
- [ ] HTTP POST to https://api.tavily.com/search
- [ ] Return SearchResult[] interface
- [ ] Test: Search for "AI research" returns results

**Reference:** `packages/core/src/services/search.py`

---

### Step 2: Port LLM Provider

**File:** `packages/worker/src/services/llm.ts`

- [ ] Create OpenRouter provider
- [ ] HTTP POST to https://openrouter.ai/api/v1/chat/completions
- [ ] Use model: `deepseek/deepseek-v3.2`
- [ ] Add token counting and cost tracking
- [ ] Add Anthropic fallback (optional)
- [ ] Test: Generate search query with LLM

**Reference:** `packages/core/src/providers/openrouter.py`

---

### Step 3: Port Article Parser

**File:** `packages/worker/src/services/parser.ts`

- [ ] Fetch article HTML
- [ ] Extract main content (simple extraction or use API)
- [ ] Extract metadata (title, author, date)
- [ ] Return parsed article
- [ ] Test: Parse a Nature.com article

**Reference:** `packages/core/src/agents/tier1_execution/parser_agent.py`

---

### Step 4: Port Digest Generator

**File:** `packages/worker/src/services/digest-generator.ts`

- [ ] Orchestrate: Search → Parse → Synthesize
- [ ] Copy Python prompts EXACTLY (they're tested!)
- [ ] Generate HN-style markdown
- [ ] Track costs
- [ ] Return full digest
- [ ] Test: Generate complete digest

**Reference:** `packages/core/src/orchestrator/main_orchestrator.py`

---

### Step 5: Wire Up API

**File:** `packages/worker/src/api/digests.ts`

- [ ] Remove ORCHESTRATOR_API_URL dependency
- [ ] Call local digest-generator.ts directly
- [ ] Store result in R2
- [ ] Save record to D1
- [ ] Return digest to user
- [ ] Test: POST /api/test/generate-digest

---

### Step 6: End-to-End Testing

- [ ] Generate digest via Worker API
- [ ] Compare output to Python version
- [ ] Verify cost (~$0.0034)
- [ ] Verify quality matches Python
- [ ] Test all error cases

**Success Criteria:**
✅ TypeScript generates same quality digest as Python
✅ Same cost profile (<$0.01)
✅ No Python dependency
✅ Deploys to Cloudflare Workers

---

## 🚀 PHASE 2: Python Production Polish (AFTER TYPESCRIPT)

**Goal:** Make Python package fully production ready for Hetzner/local

### FastAPI HTTP Wrapper

**File:** `packages/core/src/api.py` (NEW)

- [ ] Create FastAPI app
- [ ] POST /api/digest/generate endpoint
- [ ] GET /api/digest/{job_id}/progress endpoint
- [ ] GET /api/digest/{job_id}/result endpoint
- [ ] Background job processing
- [ ] Webhook callbacks on completion
- [ ] Test with curl

**Purpose:** Allows external systems to call Python package via HTTP

---

### Deployment Scripts

- [ ] Create Dockerfile for Python package
- [ ] Create docker-compose.yml
- [ ] Create systemd service file for Hetzner
- [ ] Create deployment script
- [ ] Document Hetzner deployment process

---

### Scheduling & Automation

- [ ] Create cron job for scheduled digests
- [ ] Email delivery integration
- [ ] RSS feed generation
- [ ] Error notifications

---

### Polish & Documentation

- [ ] Add comprehensive logging
- [ ] Add monitoring/health checks
- [ ] Production README.md
- [ ] Deployment guide
- [ ] API documentation

---

## 📊 Package Status Summary

| Package | Status | Deployment | Next Step |
|---------|--------|------------|-----------|
| **Python (core)** | 90% Ready ✅ | Hetzner/Local | FastAPI wrapper |
| **TypeScript (worker)** | 40% Ready 🔨 | Cloudflare | Port core logic |

---

## 🔑 Quick Start Commands

### Python Package
```bash
cd packages/core
uv sync
uv run python src/main.py
# Output: outputs/daily_digests/YYYY-MM-DD.md
```

### TypeScript Worker
```bash
cd packages/worker
pnpm run dev
# Server: http://localhost:8787
curl http://localhost:8787/api/test/env
```

---

## 📁 Important Files

**Python:**
- `packages/core/src/main.py` - Entry point
- `packages/core/secrets.json` - API keys (gitignored)
- `packages/core/config/user_preferences.yaml` - Configuration

**TypeScript:**
- `packages/worker/src/index.ts` - Worker entry
- `packages/worker/.dev.vars` - API keys (gitignored)
- `packages/worker/wrangler.toml` - Cloudflare config

**Documentation:**
- `HANDOFF.md` - Detailed handoff doc (READ THIS FIRST!)
- `CLAUDE.md` - Project instructions
- `docs/v3-spec-hybrid-architecture.md` - Architecture spec

---

## 🎯 Success Metrics

**Phase 1 Complete When:**
- [ ] TypeScript Worker generates digests independently
- [ ] No Python dependency
- [ ] Same quality as Python version
- [ ] Deploys to Cloudflare Workers
- [ ] Cost < $0.01 per digest

**Phase 2 Complete When:**
- [ ] Python package has HTTP API
- [ ] Docker deployment working
- [ ] Scheduled on Hetzner VPS
- [ ] Monitoring in place
- [ ] Email delivery working

---

## ⚠️ Critical Notes

1. **DeepSeek V3.2**: Use model ID `deepseek/deepseek-v3.2`
2. **OpenRouter is PRIMARY**: Anthropic is fallback only
3. **Copy Python prompts exactly**: They're tested and working
4. **Budget**: $0.30 daily target, currently $0.0034 per run
5. **HN Style**: Skeptical, technical, implications-focused

---

## 📞 Handoff Context

See **HANDOFF.md** for complete details:
- What's working (Python end-to-end ✅)
- What needs work (TypeScript port 🔨)
- API keys configured
- Test commands
- Success criteria
- Architecture diagrams

**Start here:** Port `services/search.ts` first - it's the simplest!

---

*Updated: December 25, 2025 | Next: TypeScript search service*
