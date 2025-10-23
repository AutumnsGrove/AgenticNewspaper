# Development Phases - Detailed Implementation Plan

**Version:** 2.0
**Date:** October 23, 2025
**Total Timeline:** 6 weeks
**Philosophy:** Fast time-to-value → Incremental complexity → Production-ready

---

## Phase Overview

| Phase | Week | Goal | Key Deliverable |
|-------|------|------|-----------------|
| **Phase 1** | 1 | Core Loop | You can read your first digest |
| **Phase 2** | 2 | Intelligence | Digest is actually useful |
| **Phase 3** | 3 | Multi-Perspective | Smarter than manual reading |
| **Phase 4** | 4 | Scale + Web UI | Production-ready with UI |
| **Phase 5** | 5 | Self-Improvement | System learns from you |
| **Phase 6** | 6 | Polish + Optimize | GitHub-ready portfolio piece |

---

## Phase 1: Core Loop (Week 1)

### Goal
Generate your first readable digest by end of week. Prove the concept works.

### Scope
- **Sources:** HN, The Verge, Ars Technica (3 sources only)
- **Topics:** AI/ML and Science (2 topics only)
- **Agents:** Orchestrator, Search, Parser, Synthesis (4 agents only)
- **Output:** Simple markdown digest

### Detailed Tasks

#### Day 1-2: Project Setup & Agent SDK

- [ ] Initialize project with UV
  ```bash
  uv init intelligent-news-aggregator
  cd intelligent-news-aggregator
  uv add anthropic-claude-sdk requests pyyaml
  ```

- [ ] Create directory structure
  ```bash
  mkdir -p src/{orchestrator,agents/{tier1_execution,tier2_reasoning},mcp_servers,models,utils}
  mkdir -p config outputs/{daily_digests,archives} data
  ```

- [ ] Create `secrets.json` and `.gitignore`
- [ ] Load config: `config/user_preferences.yaml` (simplified for Phase 1)
- [ ] Test Agent SDK connection with simple "Hello World" agent

#### Day 3-4: Orchestrator + Search Agent

- [ ] Implement `src/orchestrator/main_agent.py`
  - Agent SDK orchestrator setup
  - Load user preferences
  - Delegate to search agent
  - Collect results

- [ ] Implement `src/agents/tier1_execution/search_agent.py`
  - Agent SDK subagent definition
  - Uses MCP → Claude Haiku for query generation
  - Calls Tavily/Brave search API
  - Returns 10-15 URLs per topic

- [ ] Implement `src/mcp_servers/claude_mcp_server.py`
  - Basic Claude MCP server (Haiku only for now)
  - LLM completion function
  - Cost tracking

- [ ] Test: Can orchestrator delegate to search and get URLs back?

#### Day 5: Parser Agent

- [ ] Implement `src/agents/tier1_execution/fetch_agent.py`
  - Fetch article content (requests library)
  - Handle timeouts and errors
  - Return raw HTML

- [ ] Implement `src/agents/tier1_execution/parser_agent.py`
  - Detect HTML format
  - Extract article text (newspaper3k or readability)
  - Extract metadata (title, author, date)
  - Return clean text

- [ ] Test: Can fetch and parse 10 articles successfully?

#### Day 6: Synthesis Agent

- [ ] Implement `src/agents/tier2_reasoning/synthesis_agent.py`
  - Uses MCP → Claude Sonnet
  - Groups articles by topic
  - Writes simple summaries
  - Formats as markdown

- [ ] Implement `src/utils/markdown_formatter.py`
  - Template for digest output
  - HN-style formatting

- [ ] Test: Can generate readable digest from 10 articles?

#### Day 7: End-to-End Integration

- [ ] Implement `src/main.py`
  - Orchestrate full pipeline
  - Save digest to `outputs/daily_digests/YYYY-MM-DD.md`

- [ ] Run full pipeline end-to-end
- [ ] Generate your first real digest!
- [ ] Read it - does it make sense?

### Success Criteria

- [x] Can search 2 topics (AI/ML, Science)
- [ ] Fetch and parse 20+ articles
- [ ] Generate digest with 8-12 articles
- [ ] Digest is actually readable (not gibberish)
- [ ] Costs <$0.30
- [ ] **You actually read it**

### Expected Cost

- Orchestrator: ~10K tokens × $3/MTok = $0.03
- Search: 2 topics × 2K × $0.25/MTok = $0.001
- Parser: 20 articles × 1K × $0.25/MTok = $0.005
- Synthesis: 1 × 5K × $3/MTok = $0.015
- **Total: ~$0.05** (very cheap in Phase 1)

---

## Phase 2: Intelligence & Quality (Week 2)

### Goal
Make it actually useful - you read it multiple days in a row.

### Additions

- [ ] Content analysis agent (relevance + quality scoring)
- [ ] Quality threshold filtering (5-20 articles based on scores)
- [ ] Expand to 5 topics (add Space, Climate Solutions, Energy)
- [ ] Expand to 8 sources (add Nature, Science, Reuters, NYT, Bloomberg)
- [ ] Improve HN-style writing (technical, skeptical, implications)

### Detailed Tasks

#### Day 1-2: Analysis Agent

- [ ] Implement `src/agents/tier2_reasoning/analysis_agent.py`
  - Uses MCP → Claude Sonnet
  - Scores relevance (0-1) to user topics
  - Scores quality (0-1) based on credibility, substance
  - Extracts key points (3-5 bullets, HN style)
  - Identifies implications ("why this matters")

- [ ] Add `src/models/article.py` with AnalysisResult dataclass

- [ ] Test: Does analysis accurately predict which articles you want to read?

#### Day 3-4: Quality Filtering

- [ ] Implement quality threshold enforcement in orchestrator
  - Filter articles: relevance > 0.7 AND quality > 0.75
  - Adaptive threshold (if <5 articles, lower threshold; if >20, raise threshold)
  - Select top 5-20 articles

- [ ] Update synthesis agent to handle variable article counts

- [ ] Test: Do you read >80% of articles in digest now?

#### Day 5-6: Topic & Source Expansion

- [ ] Add 3 more topics to user_preferences.yaml:
  - Space Exploration
  - Climate Solutions (positive framing only)
  - Energy

- [ ] Add 5 more sources:
  - nature.com
  - science.org
  - reuters.com
  - nytimes.com
  - bloomberg.com

- [ ] Update search agent to handle more sources
- [ ] Add source tier system (premium vs. quality vs. aggregator)

#### Day 7: HN-Style Writing Improvements

- [ ] Update synthesis agent prompt for HN style:
  - Technical details matter
  - Skeptical tone (question claims)
  - Focus on implications and "why this matters"
  - Include "what HN comments are discussing" if from HN

- [ ] Test: Does the writing feel right for a technical audience?

### Success Criteria

- [ ] Only includes relevant articles (you read >80% of them)
- [ ] Quality scores accurately predict what you want to read
- [ ] HN-style summaries feel authentic
- [ ] You actually read digests 3+ consecutive days
- [ ] Variable article count (5-20) based on quality, not fixed
- [ ] Covers 5 topics from 8 sources

### Expected Cost

- Orchestrator: ~15K tokens = $0.045
- Search: 5 topics × 2K × $0.25/MTok = $0.0025
- Parser: 30 articles × 1K × $0.25/MTok = $0.0075
- Analysis: 20 articles × 5K × $3/MTok = $0.30
- Synthesis: 1 × 8K × $3/MTok = $0.024
- **Total: ~$0.38/digest**

---

## Phase 3: Multi-Perspective Analysis (Week 3)

### Goal
Add intelligence that makes this better than manual reading - bias detection, fact checking, alternative perspectives.

### Additions

- [ ] Bias detection agent
- [ ] Fact verification agent
- [ ] Alternative perspective finding
- [ ] Cross-story connection analysis
- [ ] Expand to all 9 topic categories

### Detailed Tasks

#### Day 1-2: Bias Detection

- [ ] Implement `src/agents/tier2_reasoning/bias_detector.py`
  - Detect political/ideological bias
  - Identify loaded language
  - Compare framing with related articles
  - Flag unverified claims
  - **Don't lecture** - just flag objectively

- [ ] Test: Does it catch obvious bias (e.g., partisan sources)?

#### Day 3-4: Fact Verification & Alternatives

- [ ] Implement `src/agents/tier2_reasoning/fact_checker.py`
  - Cross-reference claims across sources
  - Identify contradictions
  - Count verified vs. unverified claims

- [ ] Add alternative perspective finding:
  - Search for opposing viewpoints
  - Find 1-2 alternate sources with different framing
  - Include in digest

- [ ] Test: Are alternative perspectives actually useful?

#### Day 5: Cross-Story Connections

- [ ] Update synthesis agent to identify patterns:
  - Emerging trends across multiple stories
  - Connections between topics (e.g., AI regulation + tech policy)
  - "Connecting the dots" section in digest

- [ ] Add "What to Watch" section (future developments)

#### Day 6-7: Full Topic Expansion

- [ ] Add remaining 4 topics:
  - Longevity & Health Tech
  - Economics & Markets
  - Tech-Adjacent Politics
  - Weird & Interesting

- [ ] Test full 9-topic coverage

- [ ] Refine filtering to ensure balanced topic distribution

### Success Criteria

- [ ] Bias detection catches obvious bias
- [ ] Alternative perspectives add value (not just noise)
- [ ] Cross-story connections are insightful
- [ ] Full 9-topic coverage working
- [ ] Digests feel smarter than manual reading
- [ ] You continue reading digests consistently

### Expected Cost

- Orchestrator: ~18K tokens = $0.054
- Search: 5 topics × 2K × $0.25/MTok = $0.0025
- Parser: 40 articles × 1K × $0.25/MTok = $0.01
- Analysis: 25 articles × 5K × $3/MTok = $0.375
- Bias: 15 articles × 3K × $3/MTok = $0.135
- Fact Check: 15 articles × 2K × $3/MTok = $0.09
- Synthesis: 1 × 10K × $3/MTok = $0.03
- **Total: ~$0.70/digest** (higher due to more intelligence)

---

## Phase 4: Scale + Web UI (Week 4)

### Goal
Production-ready with basic web interface for viewing digests.

### Additions

- [ ] Error handling & retry logic
- [ ] Token usage optimization
- [ ] Cost monitoring dashboard
- [ ] Flask/FastAPI web UI
- [ ] Passive feedback tracking (file access)
- [ ] Article history database (SQLite)
- [ ] Docker deployment
- [ ] 30-day article retention with auto-cleanup

### Detailed Tasks

#### Day 1-2: Error Handling & Optimization

- [ ] Add retry logic for failed API calls
- [ ] Handle paywalled articles gracefully
- [ ] Implement timeout handling
- [ ] Add validation agent (check completeness, quality)

- [ ] Optimize token usage:
  - Truncate very long articles
  - Avoid duplicate processing
  - Cache search results (6 hours)

- [ ] Test: >95% successful runs

#### Day 3-4: Web UI (Flask)

- [ ] Implement `web/app.py`
  - Flask application
  - Route: `/` - list all digests
  - Route: `/digest/<date>` - view specific digest
  - Route: `/api/track/access` - log file access

- [ ] Create `web/templates/digest.html`
  - Clean, readable article display
  - HN-style aesthetic (minimal, text-focused)
  - Responsive design (works on phone)

- [ ] Implement passive tracking:
  - Log when digest accessed
  - Infer reading time from file access patterns

- [ ] Test on Raspberry Pi: Does it run smoothly with 512MB RAM?

#### Day 5-6: Database & Cost Tracking

- [ ] Implement `data/feedback.db` (SQLite)
  - Tables: digests, articles, passive_tracking
  - Store article metadata

- [ ] Implement `src/utils/cost_calculator.py`
  - Track token usage by agent
  - Calculate costs
  - Generate cost reports

- [ ] Add cost dashboard to web UI:
  - Daily cost
  - Weekly trend
  - Monthly projection
  - Breakdown by agent

- [ ] Implement 30-day retention:
  - Auto-delete article content after 30 days
  - Keep digests forever
  - Keep metadata forever

#### Day 7: Docker Deployment

- [ ] Create `docker/Dockerfile.arm64` (for Raspberry Pi)
- [ ] Create `docker/docker-compose.yml`
- [ ] Test deployment on Raspberry Pi
- [ ] Set up cron job for daily 6AM runs
- [ ] Test: Runs reliably unattended?

### Success Criteria

- [ ] >95% successful runs
- [ ] Cost <$0.50/digest
- [ ] Web UI works on Raspberry Pi
- [ ] Can browse past digests
- [ ] Tracking which articles get read
- [ ] Docker deployment working
- [ ] Auto-cleanup working

### Expected Cost

- Same as Phase 3 but optimized: **~$0.52/digest**

---

## Phase 5: Self-Improvement (Week 5)

### Goal
System learns from your reading patterns and adapts.

### Additions

- [ ] Rich feedback UI (rate articles 1-5)
- [ ] Learning algorithm
- [ ] Automatic preference updates
- [ ] Historical trend analysis
- [ ] Source expansion to 15+ sources

### Detailed Tasks

#### Day 1-2: Active Feedback UI

- [ ] Add feedback form to web UI:
  - Rate relevance (1-5 stars)
  - Rate quality (1-5 stars)
  - Rate bias detection accuracy (1-5 stars)
  - Mark favorite / irrelevant
  - Optional notes

- [ ] Implement `POST /api/feedback/submit`
- [ ] Store in `active_feedback` table

#### Day 3-4: Learning Algorithm

- [ ] Implement `src/feedback/learner.py`
  - Analyze feedback patterns
  - Learn topic weights (increase priority for topics you read)
  - Learn source trust (prioritize sources you rate highly)
  - Learn optimal article count
  - Adjust quality thresholds

- [ ] Auto-update `user_preferences.yaml` based on learning

- [ ] Generate learning reports (show what changed and why)

#### Day 5: Historical Analysis

- [ ] Add trend analysis agent (optional):
  - Identify emerging topics over time
  - Compare coverage this week vs. last month
  - Predict topics you'll care about

- [ ] Add "Insights" section to digest:
  - Emerging trends
  - Pattern changes
  - Recommendations

#### Day 6-7: Source Expansion

- [ ] Add 7 more sources:
  - quantamagazine.org
  - scientificamerican.com
  - economist.com
  - mit.edu
  - stanford.edu
  - wired.com
  - engadget.com

- [ ] Total: 15 sources across 9 topics

- [ ] Test: System handles increased volume?

### Success Criteria

- [ ] System adapts to reading patterns
- [ ] Topic weights adjust automatically
- [ ] Can provide feedback on articles
- [ ] Relevance improves over time (measure it!)
- [ ] Learning reports are insightful
- [ ] 15 sources integrated

### Expected Cost

- Same as Phase 4: **~$0.52/digest**
- Learning runs weekly (not per digest): **+$0.10/week**

---

## Phase 6: Polish + Optimization (Week 6)

### Goal
GitHub-ready portfolio piece with optional cost optimization.

### Additions

- [ ] Comprehensive testing
- [ ] Documentation completion
- [ ] Performance benchmarking
- [ ] Optional: Kimi K2 MCP server for cost optimization
- [ ] Optional: On-demand refresh (vs. daily only)
- [ ] Optional: Trend analysis agent

### Detailed Tasks

#### Day 1-2: Testing

- [ ] Write unit tests:
  - Agent behavior tests
  - MCP provider tests
  - Data model tests
  - Quality scoring tests

- [ ] Write integration tests:
  - End-to-end digest generation
  - Multi-agent coordination
  - Error handling
  - Token usage validation

- [ ] Achieve >80% test coverage

#### Day 3-4: Documentation

- [ ] Complete README.md:
  - Project overview
  - Installation guide
  - Usage instructions
  - Configuration guide
  - FAQ

- [ ] Add code comments and docstrings

- [ ] Create deployment guide for Raspberry Pi

- [ ] Add architecture diagrams (export from Mermaid)

#### Day 5: Performance Optimization

- [ ] Benchmark current performance:
  - Processing time
  - Token usage
  - Cost per digest
  - Memory usage

- [ ] Identify bottlenecks
- [ ] Optimize slow operations
- [ ] Target: <60 seconds end-to-end

#### Day 6-7: Optional Enhancements

- [ ] Implement `src/mcp_servers/kimi_mcp_server.py`
  - Kimi K2 provider
  - Update config to use for Tier 1 agents
  - Test cost savings (should be ~4% reduction)

- [ ] Optional: On-demand refresh
  - Web UI button to generate digest immediately
  - Background processing queue

- [ ] Optional: Advanced trend analysis agent
  - Weekly trend digest
  - Predictive insights

### Success Criteria

- [ ] Complete test coverage
- [ ] Full documentation
- [ ] Can swap to Kimi K2 if desired
- [ ] Ready to showcase on GitHub
- [ ] Costs optimized to <$10/month
- [ ] Processing time <60 seconds

### Expected Cost

- **All Claude:** $0.52/digest × 30 = **$15.60/month**
- **With Kimi K2 (optional):** $0.50/digest × 30 = **$15.00/month**

---

## Weekly Milestones Summary

### Week 1 (Phase 1)
**Deliverable:** Your first digest
**Status Check:** Did you read it? Was it useful?

### Week 2 (Phase 2)
**Deliverable:** Useful digest with quality filtering
**Status Check:** Did you read 3+ consecutive days?

### Week 3 (Phase 3)
**Deliverable:** Intelligent digest with bias detection
**Status Check:** Does it feel smarter than manual reading?

### Week 4 (Phase 4)
**Deliverable:** Production deployment with web UI
**Status Check:** Running reliably on Raspberry Pi?

### Week 5 (Phase 5)
**Deliverable:** Self-improving system
**Status Check:** Are preferences adapting to your behavior?

### Week 6 (Phase 6)
**Deliverable:** GitHub-ready portfolio piece
**Status Check:** Would you be proud to share this?

---

## Risk Mitigation

### If You Fall Behind

**Week 1 slippage:**
- Cut scope to 1 topic, 2 sources
- Skip synthesis agent, just list articles
- Goal: Prove basic flow works

**Week 2-3 slippage:**
- Skip bias detection (add later)
- Use simpler quality scoring
- Stick to original 5 topics

**Week 4 slippage:**
- Skip web UI, use markdown only
- Deploy without Docker (direct Python)

**Week 5-6 slippage:**
- Make these optional "nice-to-haves"
- Focus on core functionality

---

## Daily Check-In Questions

Ask yourself each day:

1. **Did I make measurable progress today?**
2. **Is the code working (not just written)?**
3. **Am I on track to hit this week's milestone?**
4. **Do I need to cut scope to stay on schedule?**

---

**Document Version:** 2.0
**Last Updated:** October 23, 2025
