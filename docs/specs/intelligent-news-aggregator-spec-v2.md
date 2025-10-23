# Intelligent News Aggregator - Project Specification v2.0

**Version:** 2.0
**Date:** October 23, 2025
**Status:** Planning Phase
**Changes from v1.0:** Added progressive source expansion, feedback loop, source tiers, cost monitoring, MCP architecture, revised phases, and user-specific preferences

---

## 📋 Executive Summary

An autonomous news aggregation service powered by **Claude Agent SDK** that delivers personalized, high-quality news digests in **HN comment style**. The system uses **Agent SDK orchestration** with **MCP-wrapped model providers** for flexibility, enabling strategic model selection (Haiku/Kimi K2 for execution, Sonnet for reasoning) while maintaining low token costs.

### Key Differentiators v2.0

- **Agent SDK orchestrator** with MCP-based model flexibility for subagents
- **HN-style analysis**: Technical, skeptical, implications-focused summaries
- **Self-improving**: Rich feedback system learns from reading patterns
- **Quality over quantity**: 5-20 articles/day based on quality threshold, not fixed count
- **Cost-optimized**: Start with Claude, easy path to Kimi K2 via MCP for 60% cost reduction
- **Progressive expansion**: Start with familiar sources (HN, The Verge), grow to 15+ sources
- **Tech-focused with breadth**: Deep tech coverage + science, space, climate, energy, economics

---

## 🎯 Project Goals

### Primary Goals
1. **Actually get read**: Build something useful enough to use daily (success = 5+ consecutive days)
2. **Reduce information overload**: Present only relevant, high-quality news (5-20 articles vs. 100+ available)
3. **Save time**: Automate research that typically requires checking multiple sites
4. **Maintain objectivity**: Cross-reference sources, flag bias, provide multiple perspectives
5. **Learn and improve**: Adapt to reading patterns over time

### Secondary Goals
6. **Learning project**: Master Claude Agent SDK multi-agent architecture
7. **Portfolio piece**: Demonstrate complex agentic systems on GitHub
8. **Cost efficiency**: Keep token usage optimized (<$0.50/day, <$15/month)

---

## 👤 User Profile & Preferences

### Current News Consumption
- **Primary sources**: Hacker News, The Verge
- **Frequency**: Irregular (wants to be more consistent)
- **Time available**: 15-20 minutes/day for news
- **Social media**: Minimal (off Twitter, Facebook, Instagram, TikTok, Reddit)

### Desired Coverage

**Topics** (in priority order):

1. **AI & Machine Learning** (Priority: 10/10)
   - LLMs, neural networks, ML breakthroughs
   - Exclude: Crypto hype, blockchain, NFTs
   - Min 2 articles, max 5 articles

2. **Science Breakthroughs** (Priority: 9/10)
   - Physics, biology, chemistry discoveries
   - Sources: Mix of peer-reviewed (Nature, Science) + journalism (Quanta, Scientific American) + tech coverage (Ars Technica)
   - Min 1 article, max 4 articles

3. **Space Exploration** (Priority: 8/10)
   - SpaceX, NASA, astronomy, cosmology
   - Min 1 article, max 3 articles

4. **Climate Solutions** (Priority: 8/10)
   - Renewable energy, carbon capture, climate tech
   - **Positive framing only** - solutions, not doom
   - Exclude: Climate denial, disaster coverage
   - Min 1 article, max 3 articles

5. **Energy** (Priority: 7/10)
   - Nuclear, fusion, batteries, grid tech
   - Min 0 articles, max 3 articles

6. **Longevity & Health Tech** (Priority: 7/10)
   - Biohacking, medical advances, aging research
   - Min 0 articles, max 2 articles

7. **Economics & Markets** (Priority: 6/10)
   - Macro trends, economic policy
   - Exclude: Stock tips, day trading, get-rich-quick
   - Min 0 articles, max 2 articles

8. **Tech-Adjacent Politics** (Priority: 6/10)
   - AI regulation, climate policy, science funding, tech antitrust
   - **Exclude general politics** - only tech/science policy
   - Min 0 articles, max 2 articles

9. **Weird & Interesting** (Priority: 5/10)
   - The kind of stuff that hits HN front page
   - Unexpected discoveries, fascinating projects
   - Min 0 articles, max 2 articles

### Quality Preferences
- **Writing style**: HN comment style - technical, slightly skeptical, focuses on "why this matters" and implications
- **Volume**: Quality threshold (5-20 articles based on relevance/quality scores, not fixed count)
- **Sources**: Mix of premium (Nature, NYT) + quality tech (Ars, Verge) + aggregators (HN)
- **Bias handling**: Flag it clearly, provide alternate perspectives, but don't lecture

---

## 🏗️ System Architecture v2.0

### High-Level Flow

```
User Preferences → Main Orchestrator (Agent SDK)
                           ↓
                   Strategy Planning
                           ↓
              ┌────────────┴────────────┐
              ↓                         ↓
      Search Strategy          Source Selection
              ↓                         ↓
      Format Detector           Fetcher Subagents
         (via MCP)                 (via MCP)
              ↓                         ↓
         Parser Agents ← Content ← Fetch Complete
         (via MCP)
              ↓
      Content Analysis Agent
       (Bias, Quality, Relevance)
              ↓
      Synthesis Agent
   (Organize, Summarize HN-style)
              ↓
   Markdown Output + Archive + Feedback Tracking
```

### Architecture Philosophy v2.0

**Agent SDK for Orchestration:**
- Main orchestrator uses Claude Agent SDK
- Handles complex multi-agent coordination
- Subagents defined in Agent SDK framework

**MCP for Model Flexibility:**
- Each subagent uses MCP tools to call LLM providers
- Easy to swap Haiku → Kimi K2 for cost optimization
- Can run multiple providers side-by-side for comparison

**Result:**
- Best of both worlds: Agent SDK's powerful orchestration + MCP's model flexibility
- Start simple (all Claude), optimize later (Kimi K2 for execution agents)
- No architecture rewrite needed for optimization

### Agent Hierarchy v2.0

**Main Orchestrator** (Agent SDK + Claude Sonnet)
- Plans daily research strategy
- Coordinates all subagents via Agent SDK
- Makes high-level decisions
- Synthesizes final output
- Tracks token usage and costs

**Tier 1: Execution Agents** (Agent SDK subagents + MCP → Haiku/Kimi K2)
- Search & Fetch Agent
- Format Detection Agent
- Parser Subagents
- Validation Agent
- *Phase 1: Haiku via MCP | Phase 6: Optionally swap to Kimi K2 via MCP*

**Tier 2: Reasoning Agents** (Agent SDK subagents + MCP → Sonnet)
- Content Analysis Agent
- Bias Detection Agent
- Fact Verification Agent
- Synthesis Agent (HN-style writing)
- *Always Sonnet - reasoning requires intelligence*

**Tier 3: Advanced Agents** (Agent SDK subagents + MCP → Sonnet, optional)
- Research Agent (deep dives)
- Trend Analysis Agent
- *Only invoked on-demand or weekly*

---

## 🔧 Technical Architecture v2.0

### Directory Structure

```
intelligent-news-aggregator/
├── pyproject.toml                    # UV package config
├── README.md
├── .env.example
├── secrets.json                      # API keys (git ignored)
├── TODOS.md                          # Project task tracking
├── config/
│   ├── user_preferences.yaml         # User's topics, sources, frequency
│   ├── agent_configs.yaml            # Model selection, token limits
│   └── source_tiers.yaml             # Source quality classifications
├── src/
│   ├── main.py                       # Entry point
│   ├── orchestrator/
│   │   ├── main_agent.py             # Main Agent SDK orchestrator (Sonnet)
│   │   ├── strategy_planner.py       # Research strategy generation
│   │   └── cost_tracker.py           # Token & cost monitoring
│   ├── agents/
│   │   ├── tier1_execution/
│   │   │   ├── search_agent.py       # Search query generation (Haiku/Kimi)
│   │   │   ├── fetch_agent.py        # Content fetching (Haiku/Kimi)
│   │   │   ├── format_detector.py    # Detect content format (Haiku/Kimi)
│   │   │   └── validation_agent.py   # Quality checks (Haiku/Kimi)
│   │   ├── tier2_reasoning/
│   │   │   ├── analysis_agent.py     # Content analysis (Sonnet)
│   │   │   ├── bias_detector.py      # Bias detection (Sonnet)
│   │   │   ├── fact_checker.py       # Cross-reference facts (Sonnet)
│   │   │   └── synthesis_agent.py    # HN-style synthesis (Sonnet)
│   │   └── tier3_advanced/
│   │       ├── research_agent.py     # Deep research (Sonnet, optional)
│   │       └── trend_agent.py        # Trend analysis (Sonnet, optional)
│   ├── mcp_servers/
│   │   ├── claude_mcp_server.py      # Claude provider via MCP
│   │   ├── kimi_mcp_server.py        # Kimi K2 provider via MCP (Phase 6)
│   │   └── mcp_config.yaml           # MCP server configurations
│   ├── tools/
│   │   ├── web_tools.py              # MCP tools for web search (Tavily/Brave)
│   │   ├── fetch_tools.py            # MCP tools for content fetching
│   │   ├── parser_tools.py           # MCP tools for parsing
│   │   └── storage_tools.py          # MCP tools for archiving
│   ├── parsers/
│   │   └── format_handlers.py        # HTML, PDF, RSS parsing
│   ├── models/
│   │   ├── article.py                # Article data model
│   │   ├── digest.py                 # Daily digest model
│   │   ├── preferences.py            # User preferences model
│   │   └── feedback.py               # Reading feedback model
│   ├── feedback/
│   │   ├── tracker.py                # Passive tracking (file access, time)
│   │   ├── learner.py                # Learning algorithm
│   │   └── storage.py                # Feedback data storage (SQLite)
│   └── utils/
│       ├── markdown_formatter.py     # Output formatting (HN style)
│       ├── cost_calculator.py        # Token → cost calculations
│       └── metrics.py                # Performance metrics
├── outputs/
│   ├── daily_digests/                # Generated news digests (kept forever)
│   └── archives/                     # Article content (30-day retention)
├── data/
│   ├── feedback.db                   # SQLite: reading feedback
│   ├── article_history.db            # SQLite: 30-day article cache
│   └── cost_history.db               # SQLite: token usage tracking
├── web/                              # Phase 4-5: Flask/FastAPI web UI
│   ├── app.py                        # Web server
│   ├── templates/                    # HTML templates
│   └── static/                       # CSS, JS
├── docker/
│   ├── Dockerfile.arm64              # Raspberry Pi optimized
│   ├── docker-compose.yml            # Full stack deployment
│   └── .dockerignore
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── docs/
    ├── mcp-subagent-architecture.md  # MCP integration details
    ├── feedback-system.md            # Feedback & learning
    ├── development-phases.md         # 6-phase detailed plan
    └── deployment-guide.md           # Raspberry Pi setup
```

---

## 🤖 Agent Specifications v2.0

### 1. Main Orchestrator Agent (Agent SDK + Claude Sonnet)

**Model:** `claude-sonnet-4-20250514` via Agent SDK
**Token Budget:** 20,000 tokens per run
**Role:** Strategic planning and coordination

**Agent SDK Configuration:**
```python
orchestrator_options = ClaudeAgentOptions(
    model="claude-sonnet-4-20250514",
    max_turns=50,
    agents={
        "search": search_agent.definition,
        "parser": parser_agent.definition,
        "analyzer": analysis_agent.definition,
        "bias_detector": bias_detector_agent.definition,
        "synthesizer": synthesis_agent.definition,
    },
    mcp_servers={
        "claude_provider": create_claude_mcp_server(),
        "web_tools": create_web_tools_server(),
        "parser_tools": create_parser_tools_server(),
    }
)
```

**System Prompt:**
```
You are the News Orchestrator using Claude Agent SDK. Your goal is to create
a personalized daily news digest in HN comment style - technical, skeptical,
focused on implications.

User Preferences:
{preferences}

Today's Strategy:
1. Review topics and quality thresholds
2. For each topic, delegate to Search Agent (aim for 50+ candidates)
3. Delegate to Parser for promising URLs
4. Send content to Analysis Agent for quality/relevance scoring
5. FILTER: Only keep articles with relevance_score > 0.7 AND quality_score > 0.75
6. For kept articles, delegate to Bias Detector
7. Collect 5-20 highest-scoring articles
8. Delegate to Synthesis Agent for HN-style digest
9. Track token usage and costs
10. Format final digest and save

Quality threshold enforcement:
- Target: 5-20 articles
- If <5 articles pass threshold: Lower threshold to 0.65 relevance
- If >20 articles pass threshold: Raise threshold to 0.8 relevance
- Never include articles below quality_score 0.7

Coordinate efficiently - subagents report summaries, not full content.
```

---

### 2. Search & Fetch Agent (Agent SDK subagent + MCP → Haiku/Kimi)

**Model:** `claude-haiku-4-20250514` via MCP (Phase 1-5) | `kimi-k2` via MCP (Phase 6 optional)
**Token Budget:** 2,000 tokens per query
**Role:** Fast search and content retrieval

**MCP Tools Available:**
- `web_search` - Tavily/Brave search
- `web_fetch` - Fetch article content
- `rss_fetch` - RSS feed parsing

**Workflow:**
```python
async def search_topic(topic: Topic, source_tier: str) -> List[ArticleURL]:
    """
    1. Generate optimized search query for topic
    2. Filter by date range (last 24h for daily, 48h for breaking)
    3. Apply source filters (tier-based)
    4. Return list of promising URLs with metadata
    5. Aim for 10-15 URLs per topic (orchestrator will filter)
    """
```

**Output to Orchestrator:**
```json
{
  "topic": "AI Policy Developments",
  "search_queries_used": ["EU AI regulation 2025", "AI Act compliance"],
  "urls_found": 23,
  "high_quality_urls": [
    {
      "url": "https://...",
      "title": "EU Parliament Passes AI Regulation Act",
      "source": "reuters.com",
      "source_tier": "premium",
      "published": "2025-10-23T09:15:00Z",
      "snippet": "...",
      "initial_relevance_score": 0.94
    }
  ],
  "tokens_used": 1840,
  "cost": "$0.00046"
}
```

---

### 3. Format Detector & Parser Agent (Agent SDK subagent + MCP → Haiku/Kimi)

**Model:** `claude-haiku-4-20250514` via MCP
**Token Budget:** 1,500 tokens per document
**Role:** Detect format and extract clean content

**MCP Tools:**
- `detect_format` - Magic bytes + content analysis
- `parse_html` - HTML article extraction
- `parse_pdf` - PDF text extraction
- `extract_article` - Reader mode extraction

**Output to Orchestrator:**
```json
{
  "url": "https://...",
  "format": "html",
  "parsing_successful": true,
  "article_summary": {
    "title": "...",
    "author": "...",
    "word_count": 1200,
    "has_paywall": false,
    "reading_time_minutes": 5
  },
  "tokens_used": 1320,
  "cost": "$0.00033"
}
```

---

### 4. Content Analysis Agent (Agent SDK subagent + MCP → Sonnet)

**Model:** `claude-sonnet-4-20250514` via MCP
**Token Budget:** 5,000 tokens per article
**Role:** Deep analysis of content quality and relevance

**Responsibilities:**
- Assess relevance to user's interests (0-1 score)
- Evaluate source credibility based on source tier
- Identify key claims and evidence
- Detect opinion vs. fact
- Flag potential misinformation signals
- **HN-style analysis**: What are the implications? Why does this matter?

**Evaluation Criteria:**
- **Relevance:** Does it match user's topics? (0-1 score)
- **Timeliness:** How recent? Breaking news > 1-day-old
- **Credibility:** Source tier + evidence quality
- **Substance:** New insights vs. rehash?
- **Balance:** Multiple perspectives?

**Output to Orchestrator:**
```json
{
  "article_id": "abc-123",
  "relevance_score": 0.87,
  "quality_score": 0.92,
  "key_points_hn_style": [
    "New policy affects 50M users - mandatory compliance by Q1 2026",
    "Penalties up to 6% global revenue - significantly higher than GDPR",
    "Implementation timeline is aggressive - many companies unprepared",
    "Likely to influence US regulation given tech industry lobbying"
  ],
  "implications": "This could reshape AI industry globally, not just EU",
  "concerns": [],
  "recommendation": "include",
  "reasoning": "Highly relevant to AI policy topic, well-sourced from Reuters, significant long-term impact",
  "tokens_used": 4200,
  "cost": "$0.0126"
}
```

---

### 5. Bias Detection Agent (Agent SDK subagent + MCP → Sonnet)

**Model:** `claude-sonnet-4-20250514` via MCP
**Token Budget:** 3,000 tokens per article
**Role:** Identify bias and suggest alternative perspectives

**Responsibilities:**
- Detect political/ideological bias (but only flag, don't lecture)
- Identify loaded language
- Flag unverified claims
- Suggest alternative perspectives (find 1-2 alternate sources)
- Check for missing context

**Output to Orchestrator:**
```json
{
  "article_id": "abc-123",
  "bias_score": 0.3,
  "bias_direction": "slightly-pro-regulation",
  "indicators": [
    "Emphasizes benefits to consumers, less focus on industry concerns",
    "Quote selection favors regulation supporters 3:1"
  ],
  "verified_claims": 8,
  "unverified_claims": 1,
  "recommendation": "include_with_note",
  "note": "Generally factual. For business perspective, see WSJ coverage.",
  "alternative_sources": [
    {"url": "https://wsj.com/...", "perspective": "business impact focus"},
    {"url": "https://eff.org/...", "perspective": "civil liberties angle"}
  ],
  "tokens_used": 2800,
  "cost": "$0.0084"
}
```

---

### 6. Synthesis Agent (Agent SDK subagent + MCP → Sonnet)

**Model:** `claude-sonnet-4-20250514` via MCP
**Token Budget:** 10,000 tokens per digest
**Role:** Create HN-style organized digest

**Responsibilities:**
- Organize articles by topic/theme
- Write summaries in HN comment style (technical, skeptical, implications-focused)
- Create connections between stories
- Format for readability
- Add metadata and source citations

**HN Writing Style Guidelines:**
```
DO:
- Focus on "why this matters" and implications
- Be skeptical - question claims, note missing info
- Include technical details HN readers care about
- Point out connections to other stories
- Note when something is overblown or underappreciated
- Mention what the HN comments are discussing (if from HN)

DON'T:
- Use marketing language or hype
- Be unnecessarily negative
- Over-explain basic concepts to HN audience
- Editorialize without technical backing
```

**Output Structure:**
```markdown
# 📰 Daily Tech Digest
**{date}** | {time} EST

**Quick Stats:** {n} articles analyzed | {m} included | ~{t} min read time
**Sources:** {source list}

---

## 🚀 Top Story

### {Title in HN Style}
{2-3 paragraph summary focusing on implications and "why this matters"}

**Technical Details:**
- {Specific technical point}
- {Numbers, specs, or concrete data}
- {Implementation details}

**What This Means:**
{HN-style analysis of implications}

**Discussion Points:**
- {What HN commenters are debating}
- {Technical concerns raised}
- {Alternative perspectives}

**Sources:** [{Name}](url), [{Name}](url) | **Bias note:** {if applicable}

---

## 🤖 AI & Machine Learning ({n} articles)

### 1. {Title}
{Summary in HN style}

**Key Points:**
- {Technical detail}
- {Implication}

**Source:** [{Name}](url) | **Read time:** {n} min

---

[More sections...]

---

## 🔗 Connections & Patterns

**Emerging Trend:** {Pattern spotted across multiple stories}

**Connecting the Dots:** {How stories relate - HN-style analysis}

**Worth Watching:** {Future developments to monitor}

---

## 🔧 Digest Metadata

**Generation Stats:**
- Articles fetched: {n}
- Articles analyzed: {n}
- Articles included: {n}
- Filtered out: {n} (reasons: {breakdown})

**Quality Scores:**
- Average relevance: {score}
- Average quality: {score}
- Articles with bias notes: {n}

**Processing:**
- Total time: {n} seconds
- Token usage: {breakdown by agent}
- Cost: ${amount}
- Budget remaining: ${monthly_budget - spent}

**Next Digest:** {date} at {time} EST
```

---

## 🔄 System Workflow v2.0

### Daily Execution Flow

```python
async def run_daily_digest():
    """
    Main execution pipeline for daily news aggregation.
    Uses Agent SDK for orchestration + MCP for model flexibility.
    """
    # 1. Load preferences and initialize tracking
    preferences = load_user_preferences("config/user_preferences.yaml")
    cost_tracker = CostTracker()

    # 2. Initialize Agent SDK orchestrator
    orchestrator_options = ClaudeAgentOptions(
        model="claude-sonnet-4-20250514",
        max_turns=50,
        agents=load_all_subagent_definitions(),
        mcp_servers=load_mcp_servers(),
    )

    # 3. Run orchestration
    async with ClaudeSDKClient(orchestrator_options) as client:
        await client.connect(generate_orchestrator_prompt(preferences))
        digest = await client.receive_response()

    # 4. Parse and save digest
    digest_data = parse_digest_output(digest)
    save_digest(digest_data, f"outputs/daily_digests/{today}.md")

    # 5. Update cost tracking
    cost_tracker.log_run(digest_data.metadata.token_usage)

    # 6. Archive articles (30-day retention)
    archive_articles(digest_data.articles, f"outputs/archives/{today}/")

    # 7. Clean up old archives (>30 days)
    cleanup_old_archives(retention_days=30)

    # 8. Track passive feedback (file access)
    track_digest_created(digest_data.digest_id, timestamp=now())

    # 9. Check budget alerts
    if cost_tracker.monthly_cost > ALERT_THRESHOLD:
        send_cost_alert(cost_tracker.monthly_cost)
```

---

## 📊 Data Models v2.0

### UserPreferences

```python
@dataclass
class UserPreferences:
    topics: List[Topic]
    sources: SourcePreferences
    update_frequency: str  # "daily", "twice_daily"
    writing_style: str     # "hn_comment_style"
    quality_threshold: QualityThreshold
    max_articles: int      # Maximum per digest (20)
    min_articles: int      # Minimum per digest (5)
    reading_time_target: int  # minutes (15-20)

@dataclass
class Topic:
    name: str
    keywords: List[str]
    exclude_keywords: List[str]  # NEW: Exclusions like "crypto", "blockchain"
    priority: int  # 1-10
    min_articles: int
    max_articles: int
    framing_preference: Optional[str]  # e.g., "positive_only" for climate

@dataclass
class SourcePreferences:
    tier1_premium: List[str]      # Always include if relevant
    tier2_quality: List[str]      # Include if highly relevant
    tier3_aggregators: List[str]  # Use for discovery, verify elsewhere
    blocklist: List[str]          # Never include
    require_verification: bool

@dataclass
class QualityThreshold:
    min_relevance_score: float  # 0.7 default
    min_quality_score: float    # 0.75 default
    adaptive: bool              # True = adjust based on article volume
```

### ParsedArticle

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
    source_tier: str  # NEW: "premium", "quality", "aggregator"
    word_count: int
    reading_time_minutes: int
    format: str
    metadata: Dict[str, Any]
```

### AnalysisResult

```python
@dataclass
class AnalysisResult:
    article_id: str
    relevance_score: float
    quality_score: float
    bias_score: float
    key_points_hn_style: List[str]  # NEW: HN-style key points
    implications: str               # NEW: "Why this matters"
    concerns: List[str]
    verified_claims: int
    unverified_claims: int
    recommendation: str
    reasoning: str
    tokens_used: int
    cost: float  # NEW: Cost tracking per analysis
```

### DailyDigest

```python
@dataclass
class DailyDigest:
    digest_id: str
    date: datetime
    articles: List[AnalyzedArticle]
    topics: Dict[str, List[AnalyzedArticle]]
    top_story: Optional[AnalyzedArticle]
    connections: str  # NEW: Cross-story connections
    summary: str
    metadata: DigestMetadata
    markdown_content: str

@dataclass
class DigestMetadata:
    total_articles_analyzed: int
    articles_included: int
    articles_filtered: Dict[str, int]  # NEW: Reasons for filtering
    sources_used: List[str]
    quality_stats: QualityStats  # NEW: Average scores
    token_usage: TokenUsage
    cost: float  # NEW: Total cost for digest
    processing_time: float

@dataclass
class TokenUsage:
    orchestrator: int
    search_agents: int
    parser_agents: int
    analysis_agents: int
    synthesis_agent: int
    total: int
    breakdown_by_model: Dict[str, int]  # NEW: Haiku vs Sonnet vs Kimi
```

### ReadingFeedback (NEW)

```python
@dataclass
class ReadingFeedback:
    digest_id: str
    article_id: str
    timestamp: datetime

    # Passive tracking
    file_accessed: bool
    time_spent_seconds: Optional[int]

    # Active feedback (Phase 5)
    relevance_rating: Optional[int]  # 1-5
    quality_rating: Optional[int]    # 1-5
    bias_accuracy_rating: Optional[int]  # 1-5
    marked_favorite: bool
    marked_irrelevant: bool
    notes: Optional[str]

@dataclass
class LearningInsights:
    """Generated from feedback history"""
    topic_preferences: Dict[str, float]  # Learned weights
    source_trust: Dict[str, float]       # Source reliability per user
    optimal_article_count: int           # Learned from reading patterns
    best_reading_time: str               # When user actually reads
    keyword_adjustments: Dict[str, List[str]]  # Keywords to add/remove
```

---

## 🚀 Implementation Phases (Revised for Fast Value)

### Phase 1: Core Loop (Week 1)
**Goal:** Generate your first readable digest by end of week

**Scope:**
- Main orchestrator (Agent SDK + Sonnet)
- Search agent (Haiku via MCP)
- Parser agent (Haiku via MCP)
- Basic synthesis (Sonnet via MCP)
- **Sources:** HN, The Verge, Ars Technica only
- **Topics:** AI/ML and Science only
- **Output:** Simple markdown digest

**Success Criteria:**
- [ ] Can search 2 topics
- [ ] Fetch and parse 20+ articles
- [ ] Generate digest with 8-12 articles
- [ ] Digest is actually readable
- [ ] Costs <$0.30

**Deliverables:**
- `src/orchestrator/main_agent.py`
- `src/agents/tier1_execution/search_agent.py`
- `src/agents/tier1_execution/fetch_agent.py`
- `src/agents/tier2_reasoning/synthesis_agent.py`
- `src/mcp_servers/claude_mcp_server.py`
- `outputs/daily_digests/2025-10-23.md` (your first digest!)

---

### Phase 2: Intelligence & Quality (Week 2)
**Goal:** Make it actually useful - you read it multiple days in a row

**Additions:**
- Content analysis agent (relevance + quality scoring)
- Quality threshold filtering
- Expand to 5 topics
- Expand to 8 sources
- HN-style writing improvements

**Success Criteria:**
- [ ] Only includes relevant articles (you read >80% of them)
- [ ] Quality scores accurately predict what you want to read
- [ ] HN-style summaries feel right
- [ ] You actually read digests 3+ days in a row

**Deliverables:**
- `src/agents/tier2_reasoning/analysis_agent.py`
- Updated synthesis agent with HN style
- Expanded source coverage

---

### Phase 3: Multi-Perspective Analysis (Week 3)
**Goal:** Add the intelligence that makes this better than manual reading

**Additions:**
- Bias detection agent
- Fact verification
- Alternative perspective finding
- Cross-story connections
- Expand to all 9 topic categories

**Success Criteria:**
- [ ] Bias detection catches obvious bias
- [ ] Alternative perspectives are actually useful
- [ ] Cross-story connections are insightful
- [ ] Full topic coverage working

**Deliverables:**
- `src/agents/tier2_reasoning/bias_detector.py`
- `src/agents/tier2_reasoning/fact_checker.py`
- Updated synthesis for connections

---

### Phase 4: Scale + Web UI (Week 4)
**Goal:** Production-ready with basic web interface

**Additions:**
- Error handling & retry logic
- Token optimization
- Cost monitoring dashboard
- Flask/FastAPI web UI for reading digests
- Passive feedback tracking (file access)
- Article history database (30-day retention)

**Success Criteria:**
- [ ] >95% successful runs
- [ ] Cost <$0.50/digest
- [ ] Web UI works on Raspberry Pi
- [ ] Can browse past digests
- [ ] Tracking which articles get read

**Deliverables:**
- `web/app.py` (Flask UI)
- `src/feedback/tracker.py`
- `data/feedback.db` (SQLite)
- Docker deployment

---

### Phase 5: Self-Improvement (Week 5)
**Goal:** System learns from your reading patterns

**Additions:**
- Rich feedback UI (rate articles)
- Learning algorithm
- Personalization engine
- Historical trend analysis
- Source expansion (to 15+ sources)

**Success Criteria:**
- [ ] System adapts to reading patterns
- [ ] Topic weights adjust automatically
- [ ] Can provide feedback on articles
- [ ] Relevance improves over time

**Deliverables:**
- `src/feedback/learner.py`
- `web/templates/feedback.html`
- Learning algorithm implementation

---

### Phase 6: Polish + Optimization (Week 6)
**Goal:** GitHub-ready + cost optimization

**Additions:**
- Kimi K2 MCP server (optional cost optimization)
- Comprehensive testing
- Documentation completion
- Performance benchmarking
- Optional: Trend analysis agent
- Optional: On-demand refresh

**Success Criteria:**
- [ ] Complete test coverage
- [ ] Full documentation
- [ ] Can swap to Kimi K2 if desired
- [ ] Ready to showcase on GitHub
- [ ] Costs optimized to <$10/month

**Deliverables:**
- `src/mcp_servers/kimi_mcp_server.py`
- Complete test suite
- README, architecture docs
- Performance reports

---

## 💰 Cost Optimization v2.0

### Token Budget & Costs

**Phase 1-5 (All Claude):**
```
Orchestrator (Sonnet): 20K tokens × $3/MTok = $0.060
Search (Haiku): 5 topics × 2K = 10K × $0.25/MTok = $0.0025
Fetch (Haiku): 30 articles × 1K = 30K × $0.25/MTok = $0.0075
Parse (Haiku): 30 articles × 1.5K = 45K × $0.25/MTok = $0.0113
Analysis (Sonnet): 20 kept × 5K = 100K × $3/MTok = $0.30
Bias (Sonnet): 12 included × 3K = 36K × $3/MTok = $0.108
Synthesis (Sonnet): 1 × 10K = 10K × $3/MTok = $0.03

Total per digest: ~$0.52
Monthly (30 days): ~$15.60
```

**Phase 6 (Kimi K2 for Tier 1):**
```
Orchestrator (Sonnet): $0.060 (no change)
Search (Kimi K2): 10K × $0.05/MTok = $0.0005
Fetch (Kimi K2): 30K × $0.05/MTok = $0.0015
Parse (Kimi K2): 45K × $0.05/MTok = $0.0023
Analysis (Sonnet): $0.30 (no change)
Bias (Sonnet): $0.108 (no change)
Synthesis (Sonnet): $0.03 (no change)

Total per digest: ~$0.50 (4% reduction)
Monthly savings: ~$0.60 (not huge, but free optimization via MCP)
```

**Cost Monitoring:**
- Daily budget alert at $0.50
- Weekly report on trends
- Monthly cap at $20 (hard stop)
- Optimization suggestions when >$15/month

---

## 🔒 Privacy & Data Retention v2.0

### Data Storage Policy

**Permanent:**
- Generated digests (markdown files)
- Feedback data (ratings, learning)
- Cost/metrics history

**30-Day Retention:**
- Full article content
- Parsing results
- Analysis details

**Auto-Cleanup:**
- Articles older than 30 days deleted
- Only URL + title + scores retained for history

**Privacy:**
- All data stored locally (SQLite, filesystem)
- No cloud sync unless explicitly enabled
- No telemetry or external tracking
- API keys in `secrets.json` (git ignored)

---

## 🧪 Testing Strategy

### Unit Tests
- Agent behavior validation
- MCP provider integration
- Data model tests
- Quality scoring algorithms

### Integration Tests
- End-to-end digest generation
- Multi-agent coordination via Agent SDK
- Error handling and recovery
- Token usage validation
- Feedback learning accuracy

### Quality Tests
- Relevance scoring accuracy (compare to manual ratings)
- Bias detection validation
- HN-style writing quality
- User acceptance testing (do you actually read it?)

---

## 🚢 Deployment (Raspberry Pi)

### Docker Setup

```yaml
# docker-compose.yml
version: '3.8'
services:
  news-aggregator:
    build:
      context: .
      dockerfile: docker/Dockerfile.arm64
    volumes:
      - ./outputs:/app/outputs
      - ./data:/app/data
      - ./config:/app/config
      - ./secrets.json:/app/secrets.json:ro
    environment:
      - TZ=America/New_York
    restart: unless-stopped
    mem_limit: 512m  # Pi limitation

  web-ui:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./outputs/daily_digests:/usr/share/nginx/html/digests:ro
      - ./web/static:/usr/share/nginx/html/static:ro
```

### Cron Schedule

```bash
# Run daily at 6:00 AM
0 6 * * * cd /home/pi/news-aggregator && docker-compose run news-aggregator
```

---

## 📚 Future Enhancements (Post-v2.0)

### Phase 7+ Ideas
- [ ] Multi-language support
- [ ] Audio digest (text-to-speech)
- [ ] Email delivery option
- [ ] Mobile app
- [ ] Collaborative digests (share with friends)
- [ ] Custom alert rules (notify on specific keywords)
- [ ] Video/podcast summarization
- [ ] Interactive Q&A with digest content

---

## 📖 References

- [Claude Agent SDK Documentation](https://docs.anthropic.com/en/api/claude-agent-sdk)
- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/)
- [Tavily Search API](https://docs.tavily.com)
- [Kimi K2 API Documentation](https://platform.moonshot.cn/)

---

**Document Version:** 2.0
**Last Updated:** October 23, 2025
**License:** MIT
