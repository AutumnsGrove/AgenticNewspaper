# Intelligent News Aggregator - Project TODOs

**Project Status:** Planning → Implementation
**Current Phase:** Phase 1 (Week 1)
**Last Updated:** October 23, 2025

---

## 🎯 Current Focus: Phase 1 - Core Loop (Week 1)

**Goal:** Generate your first readable digest by end of week
**Target Completion:** End of Week 1

### Day 1-2: Project Setup & Agent SDK

**Project Initialization**
- [ ] Initialize project with UV
  ```bash
  uv init intelligent-news-aggregator
  cd intelligent-news-aggregator
  uv add anthropic-claude-sdk requests pyyaml
  ```

- [ ] Create directory structure
  ```bash
  mkdir -p src/{orchestrator,agents/{tier1_execution,tier2_reasoning},mcp_servers,models,utils}
  mkdir -p config outputs/{daily_digests,archives} data docs web tests
  ```

- [ ] Copy template files to project
  - [ ] `config/user_preferences.yaml` (from config/user-preferences-template.yaml)
  - [ ] Simplify for Phase 1 (2 topics, 3 sources only)

- [ ] Create `secrets.json` with API keys
  ```json
  {
    "anthropic_api_key": "sk-ant-api03-...",
    "tavily_api_key": "tvly-...",
    "comment": "Add your API keys here"
  }
  ```

- [ ] Create `.gitignore`
  ```
  secrets.json
  *.pyc
  __pycache__/
  .venv/
  data/*.db
  outputs/archives/
  .DS_Store
  ```

- [ ] Create `pyproject.toml`
  ```toml
  [project]
  name = "intelligent-news-aggregator"
  version = "0.1.0"
  description = "Personalized news digest with Agent SDK + MCP"
  requires-python = ">=3.11"
  dependencies = [
      "anthropic-claude-sdk",
      "requests",
      "pyyaml",
      "newspaper3k",
      "beautifulsoup4",
      "lxml"
  ]
  ```

**Agent SDK Test**
- [ ] Create `tests/test_agent_sdk_connection.py`
  - [ ] Test loading API key from secrets.json
  - [ ] Test creating simple Agent SDK client
  - [ ] Test "Hello World" agent response
  - [ ] Verify it works before continuing

---

### Day 3-4: Orchestrator + Search Agent

**Main Orchestrator**
- [ ] Implement `src/orchestrator/main_agent.py`
  - [ ] Load user preferences from YAML
  - [ ] Create Agent SDK orchestrator
  - [ ] Define subagents (search, parser, synthesis)
  - [ ] Initialize MCP servers
  - [ ] Create orchestration loop
  - [ ] Handle errors gracefully

- [ ] Create `src/utils/config_loader.py`
  - [ ] Load `secrets.json`
  - [ ] Load `user_preferences.yaml`
  - [ ] Validate configuration

**Search Agent**
- [ ] Implement `src/agents/tier1_execution/search_agent.py`
  - [ ] Agent SDK subagent definition
  - [ ] System prompt for search specialist
  - [ ] Tool access: `llm_complete`, `web_search`
  - [ ] Query generation logic (use LLM via MCP)
  - [ ] Execute searches (Tavily/Brave API)
  - [ ] Return top 10-15 URLs per topic
  - [ ] Include initial relevance scores

- [ ] Create `src/models/article.py`
  ```python
  @dataclass
  class ArticleURL:
      url: str
      title: str
      source: str
      published_date: Optional[datetime]
      snippet: str
      initial_relevance_score: float
  ```

**MCP Server (Basic)**
- [ ] Implement `src/mcp_servers/base_provider.py`
  - [ ] BaseLLMProvider abstract class
  - [ ] LLMResponse dataclass

- [ ] Implement `src/mcp_servers/claude_mcp_server.py`
  - [ ] ClaudeMCPServer class
  - [ ] `complete()` method (Haiku only for now)
  - [ ] Token counting
  - [ ] Cost calculation
  - [ ] Health check

- [ ] Create `src/mcp_servers/__init__.py`
  - [ ] `create_mcp_servers()` function
  - [ ] Load from secrets.json

**Testing**
- [ ] Can orchestrator load config?
- [ ] Can orchestrator delegate to search agent?
- [ ] Does search agent return URLs?
- [ ] Are costs being tracked?

---

### Day 5: Parser Agent

**Fetch Agent**
- [ ] Implement `src/agents/tier1_execution/fetch_agent.py`
  - [ ] Agent SDK subagent definition
  - [ ] Fetch article content with requests
  - [ ] Handle timeouts (30s max)
  - [ ] Handle HTTP errors (404, 500, etc.)
  - [ ] Return raw HTML + metadata

**Parser Agent**
- [ ] Implement `src/agents/tier1_execution/parser_agent.py`
  - [ ] Agent SDK subagent definition
  - [ ] Detect content format (HTML, PDF, etc.)
  - [ ] Extract article using newspaper3k or readability
  - [ ] Extract metadata (title, author, date)
  - [ ] Clean text (remove ads, navigation, etc.)
  - [ ] Return ParsedArticle

- [ ] Update `src/models/article.py`
  ```python
  @dataclass
  class ParsedArticle:
      article_id: str
      url: str
      title: str
      content: str
      author: Optional[str]
      published_date: Optional[datetime]
      source: str
      word_count: int
      reading_time_minutes: int
  ```

**Testing**
- [ ] Can fetch 10 URLs successfully?
- [ ] Can parse HTML articles?
- [ ] Does error handling work (timeouts, 404s)?
- [ ] Is text clean and readable?

---

### Day 6: Synthesis Agent

**Synthesis Agent**
- [ ] Implement `src/agents/tier2_reasoning/synthesis_agent.py`
  - [ ] Agent SDK subagent definition
  - [ ] System prompt for HN-style synthesis
  - [ ] Uses MCP → Claude Sonnet
  - [ ] Group articles by topic
  - [ ] Write summaries (technical, skeptical, implications-focused)
  - [ ] Format as markdown
  - [ ] Return complete digest

**Markdown Formatter**
- [ ] Implement `src/utils/markdown_formatter.py`
  - [ ] Digest template
  - [ ] HN-style formatting
  - [ ] Source citations
  - [ ] Metadata section

**Testing**
- [ ] Does synthesis create readable summaries?
- [ ] Is HN style authentic (technical, skeptical)?
- [ ] Is markdown properly formatted?
- [ ] Does it group articles by topic?

---

### Day 7: End-to-End Integration

**Main Entry Point**
- [ ] Implement `src/main.py`
  - [ ] Load configuration
  - [ ] Create orchestrator
  - [ ] Run full pipeline
  - [ ] Save digest to `outputs/daily_digests/YYYY-MM-DD.md`
  - [ ] Print cost summary
  - [ ] Handle errors gracefully

**End-to-End Test**
- [ ] Run `uv run python src/main.py`
- [ ] Check `outputs/daily_digests/` for generated digest
- [ ] **Read the digest** - does it make sense?
- [ ] Check cost - is it <$0.30?
- [ ] Check logs - any errors?

**Fixes & Refinement**
- [ ] Fix any bugs found in E2E test
- [ ] Improve error messages
- [ ] Add logging
- [ ] Optimize if needed

**Documentation**
- [ ] Add README.md (basic usage)
- [ ] Document configuration
- [ ] Add example digest to repository

---

## ✅ Phase 1 Completion Checklist

Before moving to Phase 2, ensure:

- [ ] Can search 2 topics (AI/ML, Science)
- [ ] Can fetch and parse 20+ articles
- [ ] Can generate digest with 8-12 articles
- [ ] Digest is actually readable (not gibberish)
- [ ] Costs <$0.30
- [ ] **You actually read it and found it useful**

**If any checklist item fails, fix it before Phase 2!**

---

## 📋 Phase 2: Intelligence & Quality (Week 2)

**Status:** Not Started
**Goal:** Make digest actually useful with quality filtering

### High-Level Tasks

- [ ] Implement content analysis agent (relevance + quality scoring)
- [ ] Add quality threshold filtering (5-20 articles based on scores)
- [ ] Expand to 5 topics
- [ ] Expand to 8 sources
- [ ] Improve HN-style writing in synthesis agent
- [ ] Test: Read digest 3+ consecutive days

**Details:** See `docs/development-phases.md` → Phase 2

---

## 📋 Phase 3: Multi-Perspective Analysis (Week 3)

**Status:** Not Started
**Goal:** Add intelligence that beats manual reading

### High-Level Tasks

- [ ] Implement bias detection agent
- [ ] Implement fact verification agent
- [ ] Add alternative perspective finding
- [ ] Add cross-story connection analysis
- [ ] Expand to all 9 topic categories
- [ ] Test: Does it feel smarter than manual reading?

**Details:** See `docs/development-phases.md` → Phase 3

---

## 📋 Phase 4: Scale + Web UI (Week 4)

**Status:** Not Started
**Goal:** Production-ready with web interface

### High-Level Tasks

- [ ] Add comprehensive error handling
- [ ] Implement token usage optimization
- [ ] Create Flask/FastAPI web UI
- [ ] Add passive feedback tracking
- [ ] Implement SQLite database (article history)
- [ ] Create Docker deployment
- [ ] Set up 30-day article retention
- [ ] Deploy to Raspberry Pi

**Details:** See `docs/development-phases.md` → Phase 4

---

## 📋 Phase 5: Self-Improvement (Week 5)

**Status:** Not Started
**Goal:** System learns from reading patterns

### High-Level Tasks

- [ ] Add rich feedback UI (rate articles 1-5)
- [ ] Implement learning algorithm
- [ ] Auto-update user preferences
- [ ] Add historical trend analysis
- [ ] Expand to 15+ sources
- [ ] Test: Do preferences adapt over time?

**Details:** See `docs/development-phases.md` → Phase 5

---

## 📋 Phase 6: Polish + Optimization (Week 6)

**Status:** Not Started
**Goal:** GitHub-ready portfolio piece

### High-Level Tasks

- [ ] Write comprehensive tests (>80% coverage)
- [ ] Complete all documentation
- [ ] Performance benchmarking
- [ ] Optional: Implement Kimi K2 MCP server
- [ ] Optional: Add on-demand refresh
- [ ] Optional: Advanced trend analysis
- [ ] Polish for GitHub showcase

**Details:** See `docs/development-phases.md` → Phase 6

---

## 🚀 Future Enhancements (Post-v2.0)

**Ideas for later:**

- [ ] Multi-language support
- [ ] Audio digest (text-to-speech)
- [ ] Email delivery option
- [ ] Mobile app
- [ ] Collaborative digests
- [ ] Custom alert rules
- [ ] Video/podcast summarization
- [ ] Interactive Q&A with articles

---

## 📝 Notes & Decisions

### 2025-10-23: BaseProject Integration
- Integrated BaseProject template from https://github.com/AutumnsGrove/BaseProject
- Added ClaudeUsage/ directory with 18+ comprehensive workflow guides
- Created CLAUDE.md with project-specific instructions
- Created secrets_template.json for API key management
- Updated .gitignore to include .claude/ directory
- All BaseProject workflow guides now available in ClaudeUsage/ directory

### 2025-10-23: Project Kickoff
- Decided on Agent SDK + MCP architecture
- User preferences finalized (9 topics, HN style)
- 6-week timeline approved
- Phase 1 scope: 2 topics, 3 sources, 4 agents

### Next Decision Points
- **End of Week 1:** Is Phase 1 digest good enough to continue?
- **End of Week 2:** Are quality filters working?
- **End of Week 4:** Web UI or stay with markdown?
- **End of Week 5:** Is learning algorithm worth the complexity?

---

## 🐛 Known Issues & Blockers

**None yet** - will track as development progresses

---

## ⏰ Time Tracking

| Phase | Planned | Actual | Status |
|-------|---------|--------|--------|
| Phase 1 | 7 days | — | In Progress |
| Phase 2 | 7 days | — | Not Started |
| Phase 3 | 7 days | — | Not Started |
| Phase 4 | 7 days | — | Not Started |
| Phase 5 | 7 days | — | Not Started |
| Phase 6 | 7 days | — | Not Started |
| **Total** | **42 days** | **—** | **—** |

---

**Remember:** The goal is to build something you'll actually use, not just a GitHub project. If you're not reading the digests, something is wrong!
