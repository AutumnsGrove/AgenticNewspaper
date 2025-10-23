# Intelligent News Aggregator - Project Specification

**Version:** 1.0  
**Date:** October 17, 2025  
**Status:** Planning Phase

---

## 📋 Executive Summary

An autonomous news aggregation service powered by Claude Agent SDK that delivers personalized, high-quality news digests. The system uses **strategic model selection** (Haiku for execution, Sonnet for reasoning) and **specialized subagents** to efficiently fetch, analyze, and synthesize news from multiple sources while maintaining low token costs.

### Key Differentiators
- **Multi-agent architecture**: Specialized subagents handle focused tasks independently
- **Intelligent analysis**: Sonnet-powered reasoning for bias detection, fact verification, and synthesis
- **Cost-optimized**: Haiku for fetching/parsing, Sonnet only for complex reasoning
- **Self-improving**: Learns from user feedback to refine content selection over time

---

## 🎯 Project Goals

1. **Reduce information overload**: Present only relevant, high-quality news
2. **Save time**: Automate research that typically takes 30+ minutes daily
3. **Increase awareness**: Surface important stories user might miss
4. **Maintain objectivity**: Cross-reference sources, flag bias, verify facts
5. **Optimize costs**: Keep token usage low through smart agent orchestration

---

## 🏗️ System Architecture

### High-Level Flow

```
User Preferences → Main Orchestrator → Search Strategy
                                     ↓
                            Format Detector Agent
                                     ↓
                        ┌────────────┴────────────┐
                        ↓                         ↓
                 Parser Subagents          Fetcher Subagents
            (HTML, PDF, etc.)           (APIs, RSS, Web)
                        ↓                         ↓
                        └────────────┬────────────┘
                                     ↓
                            Content Analysis Agent
                          (Bias, Quality, Relevance)
                                     ↓
                            Synthesis Agent
                          (Organize, Summarize)
                                     ↓
                          Markdown Output + Archive
```

### Agent Hierarchy

**Main Orchestrator** (Sonnet)
- Plans daily research strategy
- Coordinates all subagents
- Makes high-level decisions
- Synthesizes final output

**Tier 1: Execution Agents** (Haiku)
- Search & Fetch Agent
- Format Detection Agent
- Parser Subagents (via OmniParser)
- Validation Agent

**Tier 2: Reasoning Agents** (Sonnet)
- Content Analysis Agent
- Bias Detection Agent
- Fact Verification Agent
- Synthesis Agent

**Tier 3: Optional Agents** (Sonnet)
- Research Agent (deep dives)
- Trend Analysis Agent
- Comparative Analysis Agent

---

## 🔧 Technical Architecture

### Directory Structure

```
intelligent-news-aggregator/
├── pyproject.toml                    # UV package config
├── README.md
├── .env.example
├── config/
│   ├── user_preferences.yaml         # User's topics, sources, frequency
│   └── agent_configs.yaml            # Model selection, token limits
├── src/
│   ├── main.py                       # Entry point
│   ├── orchestrator/
│   │   ├── main_agent.py             # Main Sonnet orchestrator
│   │   └── strategy_planner.py       # Research strategy generation
│   ├── agents/
│   │   ├── tier1_execution/
│   │   │   ├── search_agent.py       # Haiku - search query generation
│   │   │   ├── fetch_agent.py        # Haiku - content fetching
│   │   │   ├── format_detector.py    # Haiku - detect content format
│   │   │   └── validation_agent.py   # Haiku - quality checks
│   │   ├── tier2_reasoning/
│   │   │   ├── analysis_agent.py     # Sonnet - content analysis
│   │   │   ├── bias_detector.py      # Sonnet - bias detection
│   │   │   ├── fact_checker.py       # Sonnet - cross-reference facts
│   │   │   └── synthesis_agent.py    # Sonnet - final synthesis
│   │   └── tier3_advanced/
│   │       ├── research_agent.py     # Sonnet - deep research
│   │       └── trend_agent.py        # Sonnet - trend analysis
│   ├── tools/
│   │   ├── web_tools.py              # MCP tools for web search
│   │   ├── fetch_tools.py            # MCP tools for content fetching
│   │   ├── parser_tools.py           # MCP tools for OmniParser
│   │   └── storage_tools.py          # MCP tools for archiving
│   ├── parsers/
│   │   └── omniparser_integration.py # OmniParser wrapper
│   ├── models/
│   │   ├── article.py                # Article data model
│   │   ├── digest.py                 # Daily digest model
│   │   └── preferences.py            # User preferences model
│   └── utils/
│       ├── markdown_formatter.py     # Output formatting
│       ├── obsidian_links.py         # [[wiki-link]] generation
│       └── metrics.py                # Token usage tracking
├── outputs/
│   ├── daily_digests/                # Generated news digests
│   └── archives/                     # Historical data
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── docs/
    ├── architecture.md
    ├── agent_behaviors.md
    └── user_guide.md
```

---

## 🤖 Agent Specifications

### 1. Main Orchestrator Agent (Sonnet)

**Model:** `claude-sonnet-4-20250514`  
**Token Budget:** 20,000 tokens per run  
**Role:** Strategic planning and coordination

**Responsibilities:**
- Read user preferences
- Generate daily research plan
- Coordinate subagent execution
- Handle errors and retries
- Synthesize final output
- Track token usage across all agents

**Sample Prompt:**
```python
"""
You are the News Orchestrator. Your goal is to create a personalized
daily news digest based on the user's preferences.

User Preferences:
{preferences}

Today's Strategy:
1. Parse preferences to identify {n} distinct topics
2. For each topic, delegate to Search Agent to find articles
3. Delegate to Format Detector + appropriate Parser for each URL
4. Send content to Analysis Agent for quality/relevance scoring
5. For high-quality articles, delegate to Bias Detector
6. Collect results and delegate to Synthesis Agent
7. Format final digest and save

Coordinate efficiently - each subagent reports back a summary,
not full content. Make decisions based on summaries.
"""
```

---

### 2. Search & Fetch Agent (Haiku)

**Model:** `claude-haiku-4-20250514`  
**Token Budget:** 2,000 tokens per query  
**Role:** Fast search and content retrieval

**Tools:**
- `web_search` - Tavily/Brave search
- `web_fetch` - Fetch article content
- `rss_fetch` - RSS feed parsing

**Workflow:**
```python
async def search_topic(topic: str, preferences: SearchPreferences) -> List[ArticleURL]:
    """
    1. Generate optimized search query
    2. Filter by date range (last 24h)
    3. Apply source filters (include/exclude)
    4. Return list of promising URLs with metadata
    """
```

**Output to Orchestrator:**
```json
{
  "topic": "AI policy developments",
  "urls_found": 12,
  "high_quality_urls": [
    {
      "url": "https://...",
      "title": "...",
      "source": "...",
      "published": "2025-10-17",
      "snippet": "...",
      "relevance_score": 0.92
    }
  ],
  "tokens_used": 1840
}
```

---

### 3. Format Detector & Parser Agent (Haiku)

**Model:** `claude-haiku-4-20250514`  
**Token Budget:** 1,000 tokens per document  
**Role:** Detect format and route to appropriate parser

**Tools:**
- `detect_format` - Magic bytes + content analysis
- `omniparser.parse_document` - Universal parser
- `extract_article` - Article extraction tools

**Workflow:**
```python
async def parse_content(url: str, raw_content: bytes) -> ParsedArticle:
    """
    1. Detect content format (HTML, PDF, etc.)
    2. Route to appropriate OmniParser subparser
    3. Extract clean text, metadata, images
    4. Return structured article
    """
```

**Integration with OmniParser:**
```python
from omniparser import parse_document

# OmniParser handles format-specific parsing
doc = parse_document(
    content_path,
    options={
        "extract_images": False,  # News doesn't need images
        "clean_text": True,
        "detect_chapters": False   # Articles don't have chapters
    }
)

article = ParsedArticle(
    title=doc.metadata.title or extract_title_from_content(doc.content),
    content=doc.content,
    author=doc.metadata.author,
    published_date=doc.metadata.publication_date,
    word_count=doc.word_count
)
```

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
    "has_paywall": false
  },
  "tokens_used": 850
}
```

---

### 4. Content Analysis Agent (Sonnet)

**Model:** `claude-sonnet-4-20250514`  
**Token Budget:** 5,000 tokens per article  
**Role:** Deep analysis of content quality and relevance

**Responsibilities:**
- Assess relevance to user's interests (0-1 score)
- Evaluate source credibility
- Identify key claims and evidence
- Detect opinion vs. fact
- Flag potential misinformation signals

**Workflow:**
```python
async def analyze_article(article: ParsedArticle, user_interests: List[str]) -> AnalysisResult:
    """
    Analyzes article against user preferences using Sonnet reasoning.
    
    Returns:
    - relevance_score: 0.0-1.0
    - quality_score: 0.0-1.0
    - key_points: List[str]
    - concerns: List[str]  # e.g., "Unverified claim", "Single source"
    - recommendation: "include" | "exclude" | "investigate_further"
    """
```

**Evaluation Criteria:**
- **Relevance:** Does it match user's topics?
- **Timeliness:** How recent is the information?
- **Credibility:** Is the source trustworthy?
- **Substance:** Does it provide new insights?
- **Balance:** Does it present multiple perspectives?

**Output to Orchestrator:**
```json
{
  "article_id": "abc-123",
  "relevance_score": 0.87,
  "quality_score": 0.92,
  "key_points": [
    "New policy affects 50M users",
    "Implementation starts Q1 2026"
  ],
  "concerns": [],
  "recommendation": "include",
  "reasoning": "Highly relevant, well-sourced, significant impact",
  "tokens_used": 4200
}
```

---

### 5. Bias Detection Agent (Sonnet)

**Model:** `claude-sonnet-4-20250514`  
**Token Budget:** 3,000 tokens per article  
**Role:** Identify bias and verify claims

**Responsibilities:**
- Detect political/ideological bias
- Identify loaded language
- Flag unverified claims
- Cross-reference with other sources
- Suggest alternative perspectives

**Workflow:**
```python
async def detect_bias(article: ParsedArticle, related_articles: List[ParsedArticle]) -> BiasReport:
    """
    1. Analyze language for bias indicators
    2. Compare framing with related articles
    3. Identify unsupported assertions
    4. Check for missing context
    5. Return bias assessment + recommendations
    """
```

**Output to Orchestrator:**
```json
{
  "article_id": "abc-123",
  "bias_score": 0.3,  // 0 = neutral, 1 = highly biased
  "bias_direction": "left-leaning",
  "indicators": [
    "Loaded language in paragraph 3",
    "Omits counter-argument from opposing group"
  ],
  "verified_claims": 5,
  "unverified_claims": 1,
  "recommendation": "include_with_note",
  "note": "Generally factual but consider reading alternative perspective",
  "alternative_sources": ["https://..."],
  "tokens_used": 2800
}
```

---

### 6. Synthesis Agent (Sonnet)

**Model:** `claude-sonnet-4-20250514`  
**Token Budget:** 10,000 tokens per digest  
**Role:** Create final organized digest

**Responsibilities:**
- Organize articles by topic/theme
- Write concise summaries
- Create connections between stories
- Format for readability
- Add metadata and links

**Workflow:**
```python
async def synthesize_digest(
    articles: List[AnalyzedArticle],
    preferences: UserPreferences
) -> DailyDigest:
    """
    1. Group articles by theme
    2. Identify top stories
    3. Write executive summary
    4. Create topic sections
    5. Add source citations
    6. Format as markdown
    7. Return complete digest
    """
```

**Output Structure:**
```markdown
# Daily News Digest - October 17, 2025

**Generated:** 6:00 AM EST  
**Articles Analyzed:** 45 | **Included:** 12 | **Reading Time:** ~15 minutes

---

## 🔥 Top Stories

### AI Policy: EU Passes Landmark Regulation
The European Parliament approved sweeping AI regulations affecting...

**Key Points:**
- Affects all AI systems deployed in EU (estimated 2000+ companies)
- Mandatory audits for high-risk AI starting January 2026
- Fines up to 6% of global revenue for violations

**Sources:** [Reuters](https://...), [TechCrunch](https://...) *(verified across 3 sources)*  
**Analysis:** Significant policy shift; likely to influence US regulation. Moderate left-leaning coverage overall.

---

## 📊 Technology

### Three articles on this topic

#### 1. OpenAI Announces GPT-5 Release Timeline
[...]

---

## 🌍 Climate & Environment

[...]

---

## 📈 Business & Economy

[...]

---

## Metadata
- **Total Sources:** 8 (NY Times, Reuters, TechCrunch, The Verge, ArXiv, Nature, WSJ, Bloomberg)
- **Token Usage:** Main: 18,400 | Search: 6,200 | Analysis: 22,000 | Total: 46,600
- **Processing Time:** 42 seconds
- **Next Update:** Tomorrow 6:00 AM EST
```

---

## 🔄 System Workflow

### Daily Execution Flow

```python
async def run_daily_digest():
    """
    Main execution pipeline for daily news aggregation.
    """
    # 1. Initialize Main Orchestrator
    orchestrator = MainOrchestratorAgent()
    
    # 2. Load user preferences
    preferences = load_user_preferences("config/user_preferences.yaml")
    
    # 3. Start orchestration
    async with orchestrator.create_session() as session:
        # Orchestrator plans and delegates to subagents
        digest = await orchestrator.generate_digest(preferences)
    
    # 4. Save output
    save_digest(digest, f"outputs/daily_digests/{today}.md")
    
    # 5. Update metrics
    log_metrics(digest.metadata.token_usage)
    
    # 6. Archive raw data
    archive_articles(digest.articles, f"outputs/archives/{today}/")
```

### Orchestrator Internal Logic

```python
class MainOrchestratorAgent:
    async def generate_digest(self, prefs: UserPreferences) -> DailyDigest:
        options = ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            max_turns=50,
            agents={
                "search": SearchAgent().definition,
                "parser": ParserAgent().definition,
                "analyzer": AnalysisAgent().definition,
                "bias_detector": BiasDetectorAgent().definition,
                "synthesizer": SynthesisAgent().definition,
            },
            mcp_servers={
                "web_tools": create_web_tools_server(),
                "parser_tools": create_parser_tools_server(),
            }
        )
        
        async with ClaudeSDKClient(options) as client:
            await client.connect(f"""
            Generate today's news digest based on these preferences:
            
            {prefs.to_yaml()}
            
            Orchestration Plan:
            1. For each topic in preferences:
               - Use 'search' subagent to find articles (Haiku, fast)
               - Results summary only, not full content
            
            2. For each promising article:
               - Use 'parser' subagent to fetch + parse (Haiku, fast)
               - Get article summary, not full text
            
            3. Filter articles:
               - Use 'analyzer' subagent for quality assessment (Sonnet, smart)
               - Only analyze articles that seem relevant
            
            4. For high-quality articles:
               - Use 'bias_detector' subagent (Sonnet, smart)
               - Cross-reference claims
            
            5. Final synthesis:
               - Use 'synthesizer' subagent (Sonnet, smart)
               - Create organized, readable digest
            
            Token optimization:
            - Main context only sees summaries, not full articles
            - Subagents work independently with isolated contexts
            - Total budget: 50,000 tokens across all agents
            
            Return the final digest markdown.
            """)
            
            # Collect result
            result = await client.receive_response()
            return self._extract_digest(result)
```

---

## 📦 Data Models

### UserPreferences

```python
@dataclass
class UserPreferences:
    topics: List[Topic]
    sources: SourcePreferences
    update_frequency: str  # "daily", "twice_daily"
    output_format: str     # "markdown", "html", "json"
    max_articles: int
    reading_time_target: int  # minutes
    
@dataclass
class Topic:
    name: str
    keywords: List[str]
    priority: int  # 1-10
    min_articles: int
    max_articles: int

@dataclass
class SourcePreferences:
    preferred_sources: List[str]
    excluded_sources: List[str]
    require_verification: bool  # Cross-check claims?
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
    word_count: int
    format: str  # "html", "pdf", etc.
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
    key_points: List[str]
    concerns: List[str]
    verified_claims: int
    unverified_claims: int
    recommendation: str  # "include", "exclude", "investigate"
    reasoning: str
```

### DailyDigest

```python
@dataclass
class DailyDigest:
    date: datetime
    articles: List[AnalyzedArticle]
    topics: Dict[str, List[AnalyzedArticle]]
    summary: str
    metadata: DigestMetadata
    markdown_content: str

@dataclass
class DigestMetadata:
    total_articles_analyzed: int
    articles_included: int
    sources_used: List[str]
    token_usage: TokenUsage
    processing_time: float
    
@dataclass
class TokenUsage:
    orchestrator: int
    search_agents: int
    parser_agents: int
    analysis_agents: int
    synthesis_agent: int
    total: int
```

---

## 🚀 Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal:** Basic orchestrator + one search agent

**Deliverables:**
- Main orchestrator agent (Sonnet)
- Search agent (Haiku)
- User preferences system
- Basic markdown output
- Token usage tracking

**Success Criteria:**
- Can search one topic
- Returns list of URLs
- Generates simple report

---

### Phase 2: Content Acquisition (Week 2)
**Goal:** Fetch and parse articles

**Deliverables:**
- Format detector agent (Haiku)
- OmniParser integration
- Fetch agent with error handling
- Article data model
- Basic validation

**Success Criteria:**
- Parse HTML articles successfully
- Handle paywalls gracefully
- Extract metadata accurately
- Parse 10+ formats via OmniParser

---

### Phase 3: Intelligent Analysis (Week 3-4)
**Goal:** Quality and bias assessment

**Deliverables:**
- Content analysis agent (Sonnet)
- Bias detection agent (Sonnet)
- Fact verification logic
- Relevance scoring
- Multi-source comparison

**Success Criteria:**
- Accurate relevance scores (>85% user agreement)
- Detect obvious bias
- Flag unverified claims
- Cross-reference facts across sources

---

### Phase 4: Synthesis & Output (Week 5)
**Goal:** Beautiful, organized digests

**Deliverables:**
- Synthesis agent (Sonnet)
- Markdown formatting
- Topic grouping
- Summary generation
- Obsidian-compatible links

**Success Criteria:**
- Readable, well-organized output
- Accurate summaries
- Proper citations
- <15 min reading time

---

### Phase 5: Optimization & Polish (Week 6)
**Goal:** Performance and cost optimization

**Deliverables:**
- Token usage optimization
- Parallel agent execution
- Caching layer
- Error recovery
- Comprehensive testing

**Success Criteria:**
- <50,000 tokens per digest
- <60 seconds execution time
- >95% reliability
- Graceful error handling

---

### Phase 6: Advanced Features (Week 7-8)
**Goal:** Deep research and trend analysis

**Deliverables:**
- Research agent for deep dives
- Trend analysis agent
- Historical comparison
- Custom alerts
- API for programmatic access

**Success Criteria:**
- Deep research on demand
- Identify emerging trends
- Historical context
- Personalized alerts

---

## 🔧 Configuration

### user_preferences.yaml

```yaml
topics:
  - name: "AI & Machine Learning"
    keywords:
      - "artificial intelligence"
      - "machine learning"
      - "LLM"
      - "GPT"
    priority: 10
    min_articles: 3
    max_articles: 8
    
  - name: "Technology Policy"
    keywords:
      - "tech regulation"
      - "privacy laws"
      - "antitrust"
    priority: 8
    min_articles: 2
    max_articles: 5

sources:
  preferred_sources:
    - "nytimes.com"
    - "reuters.com"
    - "techcrunch.com"
    - "arstechnica.com"
    - "nature.com"
    - "arxiv.org"
  
  excluded_sources:
    - "clickbait-site.com"
    - "unreliable-source.net"
  
  require_verification: true

output:
  format: "markdown"
  max_articles: 15
  reading_time_target: 15  # minutes
  include_summaries: true
  include_bias_notes: true
  
schedule:
  frequency: "daily"
  time: "06:00"
  timezone: "America/New_York"
```

### agent_configs.yaml

```yaml
orchestrator:
  model: "claude-sonnet-4-20250514"
  max_tokens: 20000
  max_turns: 50
  
tier1_agents:  # Execution - use Haiku
  search:
    model: "claude-haiku-4-20250514"
    max_tokens: 2000
    max_turns: 5
  
  fetch:
    model: "claude-haiku-4-20250514"
    max_tokens: 1000
    max_turns: 3
  
  parser:
    model: "claude-haiku-4-20250514"
    max_tokens: 1500
    max_turns: 5

tier2_agents:  # Reasoning - use Sonnet
  analyzer:
    model: "claude-sonnet-4-20250514"
    max_tokens: 5000
    max_turns: 10
  
  bias_detector:
    model: "claude-sonnet-4-20250514"
    max_tokens: 3000
    max_turns: 8
  
  synthesizer:
    model: "claude-sonnet-4-20250514"
    max_tokens: 10000
    max_turns: 15

tier3_agents:  # Advanced - use Sonnet
  researcher:
    model: "claude-sonnet-4-20250514"
    max_tokens: 15000
    max_turns: 30
  
  trend_analyzer:
    model: "claude-sonnet-4-20250514"
    max_tokens: 8000
    max_turns: 20

token_budget:
  daily_limit: 100000
  alert_threshold: 80000
```

---

## 📊 Success Metrics

### User Experience
- **Time Saved:** 25+ minutes per day (vs. manual browsing)
- **Relevance:** >85% of articles rated "relevant" by user
- **Coverage:** Capture >90% of important stories in user's domains
- **Reading Time:** 15-20 minutes for full digest

### Technical Performance
- **Token Efficiency:** <50,000 tokens per digest
- **Speed:** <60 seconds end-to-end
- **Reliability:** >95% successful runs
- **Accuracy:** >90% bias detection accuracy

### Cost Optimization
- **Daily Cost:** <$0.50 per user (target)
- **Token Distribution:**
  - Tier 1 (Haiku): ~30% of tokens, ~10% of cost
  - Tier 2 (Sonnet): ~70% of tokens, ~90% of cost
- **Efficiency Gain:** 3x more articles analyzed vs. single-agent approach

---

## 🔒 Privacy & Ethics

### Data Handling
- User preferences stored locally only
- No article content stored permanently (only URLs)
- Optional cloud sync (encrypted)
- No data sold or shared

### Bias Mitigation
- Transparent bias detection methodology
- Multiple perspectives presented
- User can adjust bias sensitivity
- Regular bias detection audits

### Source Diversity
- Encourage diverse source selection
- Alert if sources are too ideologically similar
- Suggest alternative perspectives
- Track source diversity over time

---

## 🧪 Testing Strategy

### Unit Tests
- Agent behavior validation
- Tool integration tests
- Data model tests
- Parser integration tests

### Integration Tests
- End-to-end digest generation
- Multi-agent coordination
- Error handling and recovery
- Token usage validation

### Quality Tests
- Relevance scoring accuracy
- Bias detection validation
- Summary quality assessment
- User acceptance testing

---

## 🚢 Deployment

### Development
```bash
# Setup
uv init intelligent-news-aggregator
cd intelligent-news-aggregator
uv add anthropic-claude-sdk tavily omniparser

# Configure
cp .env.example .env
# Add API keys: ANTHROPIC_API_KEY, TAVILY_API_KEY

# Edit preferences
vim config/user_preferences.yaml

# Run
uv run python src/main.py
```

### Production
```bash
# Schedule daily run (cron)
0 6 * * * cd /path/to/project && uv run python src/main.py

# Or systemd timer
systemctl enable --user news-aggregator.timer
systemctl start --user news-aggregator.timer
```

### Monitoring
- Token usage dashboard
- Error rate tracking
- User satisfaction surveys
- Performance metrics (Prometheus/Grafana)

---

## 📚 Future Enhancements

### Phase 2 Features
- [ ] Multi-language support
- [ ] Video/podcast summarization
- [ ] Mobile app
- [ ] Email delivery option
- [ ] Social media integration

### Phase 3 Features
- [ ] Collaborative digests (team/family)
- [ ] Custom alert rules
- [ ] Historical trend analysis
- [ ] Expert commentary integration
- [ ] Interactive Q&A with digest content

---

## 📖 References

- [Claude Agent SDK Documentation](https://docs.claude.com/en/api/agent-sdk)
- [OmniParser Project](https://github.com/yourusername/omniparser)
- [Tavily Search API](https://docs.tavily.com)
- [News Aggregation Best Practices](https://example.com)

---

**Document Version:** 1.0  
**Last Updated:** October 17, 2025  
**Maintained By:** [Your Name]  
**License:** MIT
