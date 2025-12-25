# The Daily Clearing - v3 Specification

> Hybrid Python + Cloudflare Architecture
> Version: 3.0
> Date: December 25, 2025

---

## Executive Summary

**The Daily Clearing** is a personalized AI-powered news aggregator that curates, analyzes, and synthesizes news digests in an HN-style format. It supports both self-hosted (Python) and cloud-hosted (Cloudflare Workers) deployments.

**Key Differentiators**:
- Multi-agent architecture for quality, bias detection, and synthesis
- Hybrid stack: Python for logic, Cloudflare for edge/delivery
- Per-user personalization with learning feedback loops
- Beautiful newspaper-style UI with bifold layout
- Multiple delivery channels: Web, RSS, Email

**Domain**: `clearing.autumnsgrove.com` (initial deployment)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         THE DAILY CLEARING                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     DELIVERY LAYER                              │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐             │    │
│  │  │  Web    │  │  RSS    │  │  Email  │  │   API   │             │    │
│  │  │ (Svelte)│  │  Feed   │  │(Resend) │  │  (REST) │             │    │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘             │    │
│  └───────┼────────────┼────────────┼────────────┼──────────────────┘    │
│          │            │            │            │                       │
│  ┌───────▼────────────▼────────────▼────────────▼──────────────────┐    │
│  │                   CLOUDFLARE LAYER                              │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │    │
│  │  │   Workers    │  │      D1      │  │      R2      │           │    │
│  │  │ (Orchestrator│  │  (Users,     │  │  (Digests,   │           │    │
│  │  │  + API)      │  │   History)   │  │   Cache)     │           │    │
│  │  └──────┬───────┘  └──────────────┘  └──────────────┘           │    │
│  │         │                                                       │    │
│  │  ┌──────▼───────────────────────────────────────────────────┐   │    │
│  │  │              DURABLE OBJECTS (per-user)                  │   │    │
│  │  │  - Digest generation state                               │   │    │
│  │  │  - Article processing queue                              │   │    │
│  │  │  - SQLite for intermediate results                       │   │    │
│  │  └──────┬───────────────────────────────────────────────────┘   │    │
│  └─────────┼───────────────────────────────────────────────────────┘    │
│            │                                                            │
│  ┌─────────▼────────────────────────────────────────────────────────┐   │
│  │                    COMPUTE LAYER                                 │   │
│  │                                                                  │   │
│  │  ┌───────────────────────┐     ┌───────────────────────────┐     │   │
│  │  │  ON-DEMAND (Workers)  │     │  EPHEMERAL (Hetzner VPS)  │     │   │
│  │  │  - Quick regeneration │     │  - Provision on-demand    │     │   │
│  │  │  - Single-user digest │     │  - Run for 30-60 minutes  │     │   │
│  │  │  - 30-second timeout  │     │  - Auto-destruct after    │     │   │
│  │  └───────────────────────┘     │  - Cost: ~$0.005/digest   │     │   │
│  │                                │  - Hourly billing         │     │   │
│  │                                │  - 90% cost savings!      │     │   │
│  │                                └───────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    AGENT LAYER (Python)                           │  │
│  │                                                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  TIER 1: EXECUTION (Haiku/DeepSeek - cheap, fast)           │  │  │
│  │  │  ┌────────────┐ ┌────────────┐ ┌────────────┐               │  │  │
│  │  │  │   Search   │ │   Fetch    │ │   Parse    │               │  │  │
│  │  │  │   Agent    │ │   Agent    │ │   Agent    │               │  │  │
│  │  │  └────────────┘ └────────────┘ └────────────┘               │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  TIER 2: REASONING (Sonnet/DeepSeek - smart, parallel)      │  │  │
│  │  │  ┌────────────┐ ┌────────────┐ ┌────────────┐               │  │  │
│  │  │  │  Quality   │ │    Bias    │ │ Synthesis  │               │  │  │
│  │  │  │   Agent    │ │   Agent    │ │   Agent    │               │  │  │
│  │  │  └────────────┘ └────────────┘ └────────────┘               │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Dual Deployment Model

### Self-Hosted (Python)

For users who want full control:

```bash
# Clone and configure
git clone https://github.com/AutumnsGrove/AgenticNewspaper
cd AgenticNewspaper
cp secrets_template.json secrets.json
# Add your API keys

# Configure preferences
vim config/user_preferences.yaml

# Run locally
python src/main.py

# Output: outputs/daily_digests/YYYY-MM-DD.md
```

**Requirements**:
- Python 3.11+
- OpenRouter API key (for model access)
- Optional: Tavily API key (for search)

**Features**:
- Full customization
- Local model support (Ollama, LMStudio)
- No recurring costs beyond API usage
- Markdown file output

### Cloud-Hosted (Cloudflare)

For the SaaS offering:

**User Flow**:
1. Sign up at `clearing.autumnsgrove.com`
2. Configure topics, sources, delivery preferences
3. Choose plan: Free (limited) or Paid ($X/month)
4. Receive personalized digests via Web/RSS/Email

**Infrastructure**:
- Cloudflare Workers for orchestration and API
- Durable Objects for per-user state
- D1 for user accounts, history, and job tracking
- R2 for digest storage and cache
- Hetzner VPS for ephemeral digest generation (on-demand, hourly billing)
  - Provisioned via Hetzner API when needed
  - Auto-destroyed after completion
  - 90% cost savings vs persistent server

---

## Agent Architecture

### Tier 1: Execution Agents

Fast, cheap, high-volume operations.

**Model**: DeepSeek V3.2 via OpenRouter ($0.27/$1.10 per 1M tokens)

#### Search Agent

```python
class SearchAgent:
    """Generates search queries and finds relevant articles."""

    def generate_queries(self, topic: str, preferences: UserPreferences) -> list[str]:
        """Use LLM to generate smart search queries for a topic."""

    def execute_search(self, queries: list[str]) -> list[ArticleURL]:
        """Execute searches via Tavily/Brave API."""

    def score_relevance(self, articles: list[ArticleURL], topic: str) -> list[ScoredArticle]:
        """Initial relevance scoring (0.0-1.0)."""
```

#### Fetch Agent

```python
class FetchAgent:
    """Fetches article content from URLs."""

    def fetch(self, url: str, timeout: int = 30) -> RawContent:
        """Fetch URL content with proper headers and error handling."""

    def detect_format(self, content: RawContent) -> ContentFormat:
        """Detect: HTML, PDF, plaintext, markdown."""
```

#### Parse Agent

```python
class ParseAgent:
    """Extracts article content using libraries (NOT LLM)."""

    def parse(self, content: RawContent) -> ParsedArticle:
        """
        Use newspaper3k or readability-lxml for extraction.
        NO LLM CALLS - deterministic library-based parsing.
        """

    def extract_metadata(self, article: ParsedArticle) -> ArticleMetadata:
        """Extract title, author, date, word count."""
```

**Important**: Parsing uses libraries, not LLMs. This is deterministic, fast, and free.

### Tier 2: Reasoning Agents

Smart, parallel, quality-focused operations.

**Model**: DeepSeek V3.2 or Claude Sonnet (configurable)

#### Quality Agent

```python
class QualityAgent:
    """Evaluates article quality and relevance."""

    def evaluate(self, article: ParsedArticle, preferences: UserPreferences) -> QualityScore:
        """
        Returns:
        - relevance_score (0.0-1.0)
        - quality_score (0.0-1.0)
        - key_points: list[str]
        - skip_reason: Optional[str]
        """
```

#### Bias Agent

```python
class BiasAgent:
    """Detects bias and finds alternative perspectives."""

    def analyze(self, article: ParsedArticle) -> BiasAnalysis:
        """
        Returns:
        - bias_direction: left | center | right | unknown
        - bias_confidence: float
        - loaded_language: list[str]
        - missing_perspectives: list[str]
        """
```

#### Synthesis Agent

```python
class SynthesisAgent:
    """Creates the final HN-style digest."""

    def synthesize(self, articles: list[AnalyzedArticle], preferences: UserPreferences) -> Digest:
        """
        Creates complete digest with:
        - Per-topic sections
        - HN-style summaries (technical, skeptical, implications-focused)
        - Cross-story connections
        - Skeptic's corner callouts
        """
```

### Agent Orchestration Pattern

Based on Forage's proven architecture:

```python
async def generate_digest(user_id: str, preferences: UserPreferences) -> Digest:
    # TIER 1: Generation (sequential)
    search_agent = SearchAgent(tier1_provider)

    articles = []
    for topic in preferences.topics:
        queries = await search_agent.generate_queries(topic)
        urls = await search_agent.execute_search(queries)
        articles.extend(urls)

    # TIER 1: Fetch + Parse (parallel, chunked)
    fetch_agent = FetchAgent()
    parse_agent = ParseAgent()

    parsed = await parallel_process(
        articles,
        lambda url: fetch_and_parse(fetch_agent, parse_agent, url),
        chunk_size=10,
        max_concurrent=12
    )

    # TIER 2: Evaluation (parallel swarm)
    quality_agent = QualityAgent(tier2_provider)
    bias_agent = BiasAgent(tier2_provider)

    analyzed = await parallel_process(
        parsed,
        lambda article: evaluate_article(quality_agent, bias_agent, article),
        chunk_size=10,
        max_concurrent=12
    )

    # Filter by quality threshold
    filtered = [a for a in analyzed if a.quality_score >= preferences.min_quality]

    # TIER 2: Synthesis (single call with all context)
    synthesis_agent = SynthesisAgent(tier2_provider)
    digest = await synthesis_agent.synthesize(filtered, preferences)

    return digest
```

---

## Data Models

### Core Types

```python
@dataclass
class UserPreferences:
    user_id: str
    topics: list[Topic]
    sources: list[Source]
    delivery: DeliveryConfig
    style: StyleConfig
    thresholds: ThresholdConfig

@dataclass
class Topic:
    name: str
    keywords: list[str]
    priority: int  # 1-5

@dataclass
class DeliveryConfig:
    frequency: Frequency  # hourly | daily | weekly | biweekly | monthly
    delivery_time: str  # "06:00" UTC
    channels: list[Channel]  # web | rss | email
    lookback_hours: int  # How far back to search

@dataclass
class StyleConfig:
    tone: str  # "hn-style" | "formal" | "casual"
    skepticism_level: int  # 1-5
    technical_depth: int  # 1-5
    include_bias_analysis: bool
    include_cross_connections: bool

@dataclass
class ParsedArticle:
    url: str
    title: str
    content: str
    author: Optional[str]
    published_date: Optional[datetime]
    source: str
    word_count: int

@dataclass
class AnalyzedArticle(ParsedArticle):
    relevance_score: float
    quality_score: float
    bias_analysis: Optional[BiasAnalysis]
    key_points: list[str]

@dataclass
class Digest:
    digest_id: str
    user_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    sections: list[DigestSection]
    metadata: DigestMetadata
    markdown: str  # Final rendered output
```

---

## Delivery Formats

### Markdown (Core Output)

All digests are generated as markdown first, then rendered to other formats.

```markdown
# The Daily Clearing

**December 25, 2025** · Vol. 1, No. 47

---

## Artificial Intelligence

### DeepSeek V3.2 Benchmarks Show 90% Cost Reduction
*arxiv.org · Relevance: 82%*

The Chinese AI lab's latest release activates only 37B of its 685B
parameters during inference, achieving GPT-4 class performance at
a fraction of the cost...

> **Why it matters**: Cost democratization could reshape the AI
> landscape, enabling smaller players to compete.

> **Skeptic's corner**: Benchmark gaming is rampant. Real-world
> performance remains to be seen.

[Read full article →](https://arxiv.org/...)

---

## Cross-Story Connections

The cost reduction in AI inference (DeepSeek) combined with the
superconductor research progress suggests a broader trend toward...

---

## Digest Stats

- **Articles scanned**: 847
- **Articles included**: 12
- **Topics covered**: 4
- **Bias flags**: 2
- **Cost**: $0.04
- **Generated**: 6:00 AM UTC
```

### Web (Svelte)

Bifold newspaper layout with:
- Two-column design (like a real newspaper)
- Page-turn animations
- Lucide icons (no emojis)
- Typography-focused design
- Dark/light theme support
- Mobile-responsive (single column on small screens)

### RSS

Per-user RSS feed at:
```
https://clearing.autumnsgrove.com/rss/{user_id}/{secret_token}
```

Each entry is a complete digest. Feed includes:
- Full digest content in `<content:encoded>`
- Per-article links in description
- Categories for topics covered

### Email (via Resend)

HTML email with:
- Inline CSS for compatibility
- Plain text fallback
- Unsubscribe link
- Feedback links for preference learning

---

## Frequency & Lookback Logic

| Frequency | Lookback | Delivery | Use Case |
|-----------|----------|----------|----------|
| Hourly | 1 hour | On the hour | Breaking news junkies |
| Daily (AM) | 24 hours | 6:00 AM | Morning briefing |
| Daily (PM) | 12 hours | 6:00 PM | Evening recap |
| Weekly | 7 days | Monday 6:00 AM | Week in review |
| Biweekly | 14 days | Alternating Mondays | Casual readers |
| Monthly | 30 days | 1st of month | Big picture |

**On-demand** mode: User triggers generation manually, looks back based on their configured frequency.

---

## Topic System

### Predefined Topics (Suggested)

```yaml
topics:
  - name: "AI & Machine Learning"
    keywords: ["artificial intelligence", "machine learning", "LLM", "neural network"]

  - name: "Science Breakthroughs"
    keywords: ["research", "discovery", "peer-reviewed", "study"]

  - name: "Cybersecurity"
    keywords: ["vulnerability", "breach", "security", "CVE"]

  - name: "Programming & Dev Tools"
    keywords: ["programming", "framework", "library", "open source"]

  - name: "Startups & Business"
    keywords: ["startup", "funding", "acquisition", "IPO"]

  # ... more predefined
```

### User-Defined Topics

Users can create custom topics with:
- Name
- Keywords (comma-separated)
- Priority (1-5)
- Preferred sources (optional)

### Vibe Mode (Future)

User describes what they want in natural language:
```
"I want to keep up with AI developments, especially around
open source models and cost reduction. I'm skeptical of hype
and prefer technical deep-dives over press releases."
```

Agent interprets this and generates topic configuration.

---

## LLM Provider Configuration

### OpenRouter Integration

```python
class OpenRouterProvider:
    """Multi-model access via OpenRouter."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str, model: str, data_policy: str = "deny"):
        self.api_key = api_key
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Data-Policy": data_policy,  # "deny" for zero retention
        }
```

### Model Tiers

| Tier | Default Model | Cost | Use Case |
|------|---------------|------|----------|
| Tier 1 | `deepseek/deepseek-v3.2` | $0.27/$1.10 per 1M | Search, scoring |
| Tier 2 | `deepseek/deepseek-v3.2` | $0.27/$1.10 per 1M | Analysis, synthesis |
| Tier 2 (premium) | `anthropic/claude-sonnet` | $3/$15 per 1M | High-quality synthesis |

### Privacy Settings

All API calls use zero data retention:
```
X-Data-Policy: deny
```

This ensures article content and user preferences are not stored by inference providers.

---

## Database Schema (D1)

```sql
-- Users
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  subscription_tier TEXT DEFAULT 'free',
  preferences_json TEXT
);

-- Digests
CREATE TABLE digests (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  generated_at DATETIME NOT NULL,
  period_start DATETIME NOT NULL,
  period_end DATETIME NOT NULL,
  frequency TEXT NOT NULL,
  r2_key TEXT NOT NULL,  -- Points to full digest in R2
  article_count INTEGER,
  topics_json TEXT,
  cost_usd REAL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Feedback (for learning)
CREATE TABLE feedback (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  digest_id TEXT NOT NULL,
  article_url TEXT,
  feedback_type TEXT,  -- 'like' | 'dislike' | 'read' | 'skip'
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (digest_id) REFERENCES digests(id)
);

-- Cost tracking
CREATE TABLE usage (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  month TEXT NOT NULL,  -- 'YYYY-MM'
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  cost_usd REAL DEFAULT 0,
  digest_count INTEGER DEFAULT 0,
  UNIQUE(user_id, month)
);

-- Indexes
CREATE INDEX idx_digests_user ON digests(user_id, generated_at DESC);
CREATE INDEX idx_feedback_user ON feedback(user_id, created_at DESC);
CREATE INDEX idx_usage_user_month ON usage(user_id, month);
```

---

## Durable Object Schema

Per-user digest generation state:

```sql
-- Single row tracking current generation
CREATE TABLE digest_job (
  id TEXT PRIMARY KEY,
  status TEXT,  -- pending | searching | fetching | analyzing | synthesizing | complete | failed
  batch_num INTEGER DEFAULT 0,
  articles_found INTEGER DEFAULT 0,
  articles_parsed INTEGER DEFAULT 0,
  articles_analyzed INTEGER DEFAULT 0,
  current_topic TEXT,
  error_message TEXT,
  started_at DATETIME,
  updated_at DATETIME
);

-- Accumulated articles
CREATE TABLE articles (
  id TEXT PRIMARY KEY,
  url TEXT UNIQUE,
  title TEXT,
  content TEXT,
  source TEXT,
  topic TEXT,
  relevance_score REAL,
  quality_score REAL,
  bias_direction TEXT,
  key_points_json TEXT,
  fetched_at DATETIME
);

-- Processing artifacts
CREATE TABLE artifacts (
  id INTEGER PRIMARY KEY,
  artifact_type TEXT,  -- 'search_results' | 'synthesis_draft' | 'final_digest'
  content TEXT,
  created_at DATETIME
);
```

---

## Cost Projections

### Per-Digest Costs (DeepSeek V3.2)

| Component | Tokens | Cost |
|-----------|--------|------|
| Search queries (5 topics × 3 queries) | ~2,000 | $0.0005 |
| Relevance scoring (50 articles) | ~10,000 | $0.003 |
| Quality analysis (20 articles) | ~30,000 | $0.009 |
| Bias detection (20 articles) | ~20,000 | $0.006 |
| Synthesis | ~15,000 | $0.016 |
| **Total per digest** | ~77,000 | **~$0.035** |

### Monthly Projections

| Plan | Frequency | Digests/mo | Cost/mo |
|------|-----------|------------|---------|
| Free | Weekly | 4 | $0.14 |
| Basic | Daily | 30 | $1.05 |
| Pro | Daily + On-demand | 60 | $2.10 |

### Ephemeral Processing (Hetzner On-Demand)

**Per Digest**:
- Server provision: 1-2 minutes
- Digest generation: 20-30 minutes
- Upload & destroy: 30 seconds
- Total server time: ~30 minutes
- Cost: ~$0.005 per digest (CPX11 @ $0.01/hour)

**Monthly (60 digests/month for 1 user)**:
- Compute: 60 × $0.005 = $0.30
- API costs: 60 × $0.051 = $3.06
- Total: $3.36/month

**Cost Comparison**:
- Ephemeral Hetzner: $40/year
- Persistent Hetzner: $97/year
- Savings: 59% cheaper!

---

## Implementation Phases

### Phase 1: MVP (Python Core)

**Goal**: Working digest generation, markdown output

- [ ] Swap mock agents for real implementations
- [ ] Integrate OpenRouter for LLM calls
- [ ] Use newspaper3k for parsing (not LLM)
- [ ] Integrate Tavily for search
- [ ] Generate real digests with real articles
- [ ] Output to markdown files

**Deliverable**: `python src/main.py` generates a real, readable digest

### Phase 2: Visualization

**Goal**: See what the digest looks like

- [ ] Create basic Svelte app
- [ ] Markdown → HTML rendering
- [ ] Implement bifold newspaper layout
- [ ] Add Lucide icons
- [ ] Test typography and styling

**Deliverable**: Load a markdown digest and see the newspaper UI

### Phase 3: Cloudflare Integration

**Goal**: Cloud-hosted version

- [ ] Port Python agents to work with Workers
- [ ] Implement DigestJob Durable Object
- [ ] Set up D1 schema
- [ ] Set up R2 for digest storage
- [ ] Create API endpoints

**Deliverable**: Generate digest via Workers API

### Phase 4: User System

**Goal**: Multi-user support

- [ ] User authentication (Heartwood or custom)
- [ ] Preference management
- [ ] Per-user digest generation
- [ ] Delivery scheduling (cron)

**Deliverable**: Multiple users can sign up and receive digests

### Phase 5: Delivery Channels

**Goal**: Web, RSS, Email

- [ ] Web reader with history
- [ ] RSS feed generation
- [ ] Email delivery via Resend
- [ ] Notification preferences

**Deliverable**: All delivery channels working

### Phase 6: Intelligence

**Goal**: Smart features

- [ ] Bias detection agent
- [ ] Cross-story connections
- [ ] Feedback collection
- [ ] Preference learning

**Deliverable**: Digests that get smarter over time

---

## File Structure (Proposed)

```
AgenticNewspaper/
├── AGENT.md                    # Project instructions
├── TODOS.md                    # Task tracking
├── CHARM-OF-NAMING.md          # Why we keep spec versions
│
├── packages/
│   ├── core/                   # Python agent system
│   │   ├── src/
│   │   │   ├── agents/
│   │   │   │   ├── tier1/
│   │   │   │   │   ├── search.py
│   │   │   │   │   ├── fetch.py
│   │   │   │   │   └── parse.py
│   │   │   │   └── tier2/
│   │   │   │       ├── quality.py
│   │   │   │       ├── bias.py
│   │   │   │       └── synthesis.py
│   │   │   ├── providers/
│   │   │   │   ├── openrouter.py
│   │   │   │   └── base.py
│   │   │   ├── models/
│   │   │   │   └── article.py
│   │   │   ├── orchestrator.py
│   │   │   └── main.py
│   │   ├── config/
│   │   │   └── user_preferences.yaml
│   │   ├── outputs/
│   │   │   └── daily_digests/
│   │   └── pyproject.toml
│   │
│   ├── web/                    # Svelte frontend
│   │   ├── src/
│   │   │   ├── routes/
│   │   │   ├── lib/
│   │   │   │   ├── components/
│   │   │   │   │   ├── DigestReader.svelte
│   │   │   │   │   ├── ArticleCard.svelte
│   │   │   │   │   ├── TopicSection.svelte
│   │   │   │   │   └── BifoldLayout.svelte
│   │   │   │   ├── stores/
│   │   │   │   └── api/
│   │   │   └── app.html
│   │   ├── svelte.config.js
│   │   └── package.json
│   │
│   └── worker/                 # Cloudflare Workers
│       ├── src/
│       │   ├── index.ts
│       │   ├── services/
│       │   │   ├── DigestJob.ts   # Durable Object
│       │   │   └── delivery.ts
│       │   └── types/
│       ├── schemas/
│       │   └── d1-schema.sql
│       └── wrangler.toml
│
├── references/                 # Repo exploration docs
│   ├── groveengine-patterns.md
│   ├── forage-patterns.md
│   ├── grovebloom-patterns.md
│   └── amber-patterns.md
│
└── docs/
    ├── v3-spec-hybrid-architecture.md  # This file
    ├── intelligent-news-aggregator-spec-v2.md
    └── intelligent-news-aggregator-spec-orig.md
```

---

## Open Questions

1. **Pricing model**: What should free vs paid tiers include?
2. **Source priority**: Should users be able to rank sources?
3. **Raindrop integration**: Import saved articles for personalized digest?
4. **Archive access**: How long should digest history be available?
5. **Collaborative digests**: Shared topic configurations between users?

---

## Success Criteria

**MVP is successful when**:
- [ ] `python src/main.py` generates a real digest with real articles
- [ ] The digest is genuinely useful to read
- [ ] Cost per digest is under $0.05
- [ ] Generation time is under 2 minutes

**v1.0 is successful when**:
- [ ] Users can sign up and configure preferences
- [ ] Digests are delivered via at least 2 channels
- [ ] The web UI looks like a newspaper
- [ ] At least 10 users are actively using it

---

*This specification supersedes v2. For historical context, see earlier spec versions.*
