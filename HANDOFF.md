# 🚀 Project Handoff - The Daily Clearing

**Status:** Python package working end-to-end. TypeScript port in progress.
**Date:** December 25, 2025
**Session:** Local development → Web remote Claude Code

---

## ✅ What's Working (TESTED & DEPLOYED)

### Python Package (`packages/core/`) - **PRODUCTION READY**

✅ **Full end-to-end digest generation working!**

```bash
cd packages/core
uv run python src/main.py
```

**Results:**
- ✅ Real Tavily search (7 articles fetched)
- ✅ DeepSeek V3.2 via OpenRouter ($0.0034 per run)
- ✅ Real URLs (Nature, ArXiv, HN)
- ✅ HN-style skeptical analysis
- ✅ Cost: 99% under budget ($0.30 target)

**Configuration:**
- API Keys: `packages/core/secrets.json`
- OpenRouter: PRIMARY provider
- Anthropic: FALLBACK provider (optional)
- Tavily: Search API

**Key Files:**
- `src/main.py` - Entry point
- `src/orchestrator/main_orchestrator.py` - Digest generation
- `src/agents/` - Search, parse, synthesis agents
- `src/providers/` - OpenRouter + Anthropic
- `src/services/search.py` - Tavily integration

---

### Cloudflare Worker (`packages/worker/`) - **IN PROGRESS**

✅ **Infrastructure setup complete:**
- ✅ Wrangler dev server running (http://localhost:8787)
- ✅ D1 database migrated (7 tables)
- ✅ R2 buckets configured
- ✅ API routes scaffolded
- ✅ Test endpoints working

**Status:**
- Database: ✅ Connected
- API: ✅ Running
- Core Logic: ❌ **NEEDS TYPESCRIPT PORT**

**What's Missing:**
- TypeScript implementations of:
  - Search service (Tavily)
  - LLM provider (OpenRouter/DeepSeek)
  - Article parsing
  - Digest synthesis
  - Full orchestration

---

## 🎯 Architecture Decision (CRITICAL)

### **Split Standalone Architecture**

```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│  Python Package             │     │  TypeScript Worker           │
│  (packages/core)            │     │  (packages/worker)           │
├─────────────────────────────┤     ├──────────────────────────────┤
│  ✅ WORKING                 │     │  🔨 IN PROGRESS              │
│  - Hetzner VPS              │     │  - Cloudflare Workers        │
│  - Local installs           │     │  - Edge deployment           │
│  - Full standalone          │     │  - Full standalone           │
│  - CLI: python src/main.py  │     │  - No Python dependency      │
└─────────────────────────────┘     └──────────────────────────────┘

    INDEPENDENT                         INDEPENDENT
    No HTTP API needed                  No Python calls
```

**Key Point:** Both packages should work **100% independently**:
- Python: Does NOT need TypeScript
- TypeScript: Does NOT need Python
- Same functionality, different deployment targets

---

## 📋 IMMEDIATE NEXT STEPS

### Priority 1: Port Core Logic to TypeScript

**Create these services in `packages/worker/src/services/`:**

1. **`llm.ts`** - OpenRouter/DeepSeek provider
   - Copy logic from Python `src/providers/openrouter.py`
   - HTTP calls to OpenRouter API
   - Model: `deepseek/deepseek-chat` (v3.2)

2. **`search.ts`** - Tavily search
   - Copy logic from Python `src/services/search.py`
   - HTTP POST to `https://api.tavily.com/search`
   - Return SearchResult[]

3. **`parser.ts`** - Article parsing
   - Fetch article HTML
   - Extract content (use readability-like logic or API)
   - Return parsed text

4. **`digest-generator.ts`** - Main orchestration
   - Combine search + parse + synthesis
   - Call LLM for HN-style analysis
   - Return markdown digest

### Priority 2: Wire Up API Endpoint

**Update `packages/worker/src/api/digests.ts`:**

```typescript
// Instead of calling ORCHESTRATOR_API_URL (Python),
// call local TypeScript digest-generator directly:

import { generateDigest } from '../services/digest-generator';

digests.post('/generate', async (c) => {
  const result = await generateDigest(c.env, preferences);
  return c.json(result);
});
```

### Priority 3: Test End-to-End

```bash
# Test Cloudflare Worker digest generation
curl -X POST http://localhost:8787/api/test/generate-digest
```

---

## 🔑 API Keys Configured

**Both packages have API keys:**

**Python** (`packages/core/secrets.json`):
```json
{
  "openrouter_api_key": "sk-or-v1-[CONFIGURED]",
  "tavily_api_key": "tvly-dev-[CONFIGURED]",
  "anthropic_api_key": "[OPTIONAL]"
}
```

**TypeScript** (`packages/worker/.dev.vars`):
```bash
OPENROUTER_API_KEY=sk-or-v1-[CONFIGURED]
TAVILY_API_KEY=tvly-dev-[CONFIGURED]
ANTHROPIC_API_KEY=[OPTIONAL]
JWT_SECRET=your-secret-key
```

---

## 📁 Project Structure

```
AgenticNewspaper/
├── packages/
│   ├── core/              # Python - WORKING ✅
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── orchestrator/
│   │   │   ├── agents/
│   │   │   ├── providers/
│   │   │   └── services/
│   │   ├── secrets.json   # API keys
│   │   └── pyproject.toml
│   │
│   └── worker/            # TypeScript - IN PROGRESS 🔨
│       ├── src/
│       │   ├── index.ts
│       │   ├── api/       # ✅ Routes scaffolded
│       │   └── services/  # ❌ NEEDS: llm.ts, search.ts, etc
│       ├── .dev.vars      # API keys
│       └── wrangler.toml
│
├── TODOS.md              # Original todos (outdated)
├── HANDOFF.md           # THIS FILE
└── README.md
```

---

## 🧪 How to Test

### Python Package (Working)
```bash
cd packages/core
uv run python src/main.py

# Output: outputs/daily_digests/2025-12-25.md
# Cost: ~$0.0034
```

### TypeScript Worker (Dev Server)
```bash
# Already running in background!
curl http://localhost:8787/health
curl http://localhost:8787/api/test/env
curl http://localhost:8787/api/test/db
```

---

## 🚨 Critical Context

1. **OpenRouter is PRIMARY**, Anthropic is fallback
2. **DeepSeek V3.2** via `deepseek/deepseek-chat` model
3. **Tavily search** returns real articles (not mocks)
4. **HN-style** skeptical tone in synthesis
5. **Budget:** $0.30 target, currently ~$0.0034 per run

---

## 📝 Recent Commits

```
481f343 Integrate real Tavily search and DeepSeek V3.2
083ed0f Fix provider integration to use OpenRouter as primary
120b3ba Update local development setup and provider configuration
```

---

## ❓ Questions to Answer

1. **Should TypeScript also support Anthropic fallback?** (Yes, copy pattern from Python)
2. **Article parsing strategy?** (Python uses newspaper3k - TS could use Cloudflare's fetch + simple extraction)
3. **Synthesis prompt?** (Copy exact prompt from Python `synthesis_agent.py`)

---

## 🎯 Success Criteria

**TypeScript port is complete when:**

✅ Can search Tavily for articles
✅ Can call OpenRouter/DeepSeek for LLM
✅ Can parse article content
✅ Can generate HN-style digest markdown
✅ Same cost (<$0.01 per digest)
✅ Same output quality as Python

**Then both packages work independently!**

---

## 💡 Tips for Next Session

1. **Start with `services/search.ts`** - simplest to port
2. **Copy Python prompts exactly** - they're tested and working
3. **Use Python output as reference** - should match quality
4. **Test incrementally** - search → parse → LLM → full
5. **Keep costs low** - DeepSeek is 10x cheaper than Claude

---

## 🔗 Useful References

- Python working digest: `packages/core/outputs/daily_digests/2025-12-25.md`
- Python search: `packages/core/src/services/search.py`
- Python providers: `packages/core/src/providers/openrouter.py`
- TypeScript types: `packages/worker/src/types/index.ts`

---

**Ready to port! The Python version proves the concept works - now just translate to TypeScript for Cloudflare deployment.**
