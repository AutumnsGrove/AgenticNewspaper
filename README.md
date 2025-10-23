# Agentic Newspaper

An intelligent news aggregator that uses AI agents to curate, analyze, and synthesize personalized news digests in a Hacker News style.

## 🎯 Project Overview

This project implements a sophisticated multi-agent system using Anthropic's Claude Agent SDK and Model Context Protocol (MCP) to automatically generate daily, personalized news digests. The system searches, fetches, analyzes, and synthesizes articles based on your interests, delivering high-quality summaries with technical depth and skeptical analysis.

**Project Status:** Planning → Implementation (Phase 1)
**Timeline:** 6-week development cycle
**Current Phase:** Week 1 - Core Loop Development

## 📁 Project Structure

```
AgenticNewspaper/
├── README.md                    # You are here!
├── TODOS.md                     # Current task tracking & development plan
├── .gitignore                   # Git exclusions (secrets, cache, etc.)
│
├── config/                      # Configuration files
│   └── user-preferences-template.yaml   # User preferences template
│
└── docs/                        # All documentation
    ├── specs/                   # Project specifications
    │   ├── intelligent-news-aggregator-spec-v2.md     # Latest spec (v2)
    │   ├── intelligent-news-aggregator-spec.md        # Original spec
    │   ├── spec.md              # Initial specification
    │   └── spec_linked.md       # Linked spec reference
    │
    ├── architecture/            # System architecture docs
    │   ├── news-aggregator-architecture-v2.md         # Latest architecture (v2)
    │   ├── news-aggregator-architecture.md            # Original architecture
    │   └── news-aggregator-architecture_linked.md     # Linked reference
    │
    ├── diagrams/                # Visual diagrams & flowcharts
    │   ├── news-aggregator-architecture_0_flowchart.png    # Main flow
    │   ├── news-aggregator-architecture_1_flowchart.png    # Agent interactions
    │   ├── news-aggregator-architecture_2_sequenceDiagram.png  # Sequence diagram
    │   └── spec_0_graph.png     # Specification graph
    │
    ├── development-phases.md    # 6-week development roadmap
    ├── feedback-system.md       # User feedback & learning system design
    ├── mcp-subagent-architecture.md  # MCP server architecture details
    └── quick-start-implementation.md # Quick implementation guide
```

## 🚀 Quick Start

### Where to Begin

1. **New to the project?** Start here:
   - Read [`docs/specs/intelligent-news-aggregator-spec-v2.md`](docs/specs/intelligent-news-aggregator-spec-v2.md) - Understand what we're building
   - Review [`docs/architecture/news-aggregator-architecture-v2.md`](docs/architecture/news-aggregator-architecture-v2.md) - See how it works
   - Check [`docs/diagrams/`](docs/diagrams/) - Visualize the system flow

2. **Ready to implement?**
   - Read [`TODOS.md`](TODOS.md) - Current development tasks (Phase 1 - Week 1)
   - Follow [`docs/quick-start-implementation.md`](docs/quick-start-implementation.md) - Step-by-step guide
   - Review [`docs/development-phases.md`](docs/development-phases.md) - Complete 6-week plan

3. **Want to customize?**
   - Copy [`config/user-preferences-template.yaml`](config/user-preferences-template.yaml) to `config/user-preferences.yaml`
   - Edit your topics, sources, and preferences
   - See [`docs/specs/intelligent-news-aggregator-spec-v2.md`](docs/specs/intelligent-news-aggregator-spec-v2.md) for configuration options

## 📖 Key Documentation

### Essential Reading

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [`intelligent-news-aggregator-spec-v2.md`](docs/specs/intelligent-news-aggregator-spec-v2.md) | **Latest project specification** | First - understand the vision |
| [`news-aggregator-architecture-v2.md`](docs/architecture/news-aggregator-architecture-v2.md) | **System architecture & design** | Second - see how it works |
| [`TODOS.md`](TODOS.md) | **Current development tasks** | Always - track progress |
| [`development-phases.md`](docs/development-phases.md) | **6-week implementation roadmap** | Planning - understand timeline |
| [`quick-start-implementation.md`](docs/quick-start-implementation.md) | **Hands-on implementation guide** | When coding - step-by-step |

### Supporting Documentation

| Document | Purpose |
|----------|---------|
| [`mcp-subagent-architecture.md`](docs/mcp-subagent-architecture.md) | MCP server details & agent communication |
| [`feedback-system.md`](docs/feedback-system.md) | User feedback & self-improvement design |

### Legacy Files (v1)

The `docs/specs/` and `docs/architecture/` folders contain v1 files for reference. Always prefer the `-v2.md` versions for current work.

## 🏗️ System Architecture

### High-Level Overview

```
User Preferences → Orchestrator Agent
                         ↓
    ┌──────────────────────────────────────┐
    │                                      │
    ↓                                      ↓
Search Agent                        Analysis Agents
    ↓                                      ↓
Fetch Agent                         Synthesis Agent
    ↓                                      ↓
Parser Agent  →  MCP Servers  ←   Daily Digest
```

### Agent Tiers

- **Tier 1 (Execution):** Search, Fetch, Parser agents - Fast, simple tasks
- **Tier 2 (Reasoning):** Content Analysis, Synthesis - Deep thinking, quality work

### Technology Stack

- **Agent Framework:** Anthropic Claude Agent SDK
- **Context Protocol:** Model Context Protocol (MCP)
- **Models:** Claude Haiku (Tier 1), Claude Sonnet (Tier 2)
- **Language:** Python 3.11+
- **Package Manager:** UV

See [`docs/architecture/news-aggregator-architecture-v2.md`](docs/architecture/news-aggregator-architecture-v2.md) for complete details.

## 📅 Development Timeline

### Current Phase: Phase 1 - Core Loop (Week 1)

**Goal:** Generate your first readable digest by end of week
**Scope:** 2 topics, 3 sources, 4 agents, basic synthesis

### Upcoming Phases

- **Phase 2 (Week 2):** Intelligence & quality filtering
- **Phase 3 (Week 3):** Multi-perspective analysis
- **Phase 4 (Week 4):** Scale + web UI
- **Phase 5 (Week 5):** Self-improvement & learning
- **Phase 6 (Week 6):** Polish & optimization

See [`TODOS.md`](TODOS.md) for detailed current tasks and [`docs/development-phases.md`](docs/development-phases.md) for complete roadmap.

## 🎨 Features (Planned)

### Core Features (Phase 1-2)
- ✅ Multi-topic news search
- ✅ Intelligent article fetching & parsing
- ✅ Quality scoring & filtering
- ✅ Hacker News-style synthesis
- ✅ Daily digest generation

### Advanced Features (Phase 3-5)
- ⏳ Bias detection & multi-perspective analysis
- ⏳ Fact verification
- ⏳ Cross-story connection finding
- ⏳ Web UI for browsing
- ⏳ Self-improvement from reading patterns

### Polish Features (Phase 6)
- ⏳ Historical trend analysis
- ⏳ On-demand refresh
- ⏳ Advanced caching
- ⏳ Comprehensive testing

## 🔧 Configuration

### User Preferences

Copy `config/user-preferences-template.yaml` to `config/user-preferences.yaml` and customize:

- **Topics:** AI/ML, Science, Climate, Politics, etc.
- **Sources:** Hacker News, Ars Technica, The Verge, etc.
- **Style:** Technical depth, skepticism level, summary length
- **Filters:** Quality thresholds, recency, source diversity

### API Keys

Create `secrets.json` in the project root:

```json
{
  "anthropic_api_key": "sk-ant-api03-...",
  "tavily_api_key": "tvly-...",
  "comment": "Add your API keys here. Never commit this file!"
}
```

**Note:** `secrets.json` is already in `.gitignore`

## 📊 Cost Expectations

- **Phase 1:** ~$0.30/day (Haiku + Sonnet, ~20 articles)
- **Phase 2-3:** ~$0.50/day (increased volume + analysis)
- **Phase 4-6:** ~$1.00/day (full feature set)

See [`docs/architecture/news-aggregator-architecture-v2.md`](docs/architecture/news-aggregator-architecture-v2.md) for cost breakdown.

## 🤝 Contributing

This is currently a personal project. Development tracking happens in:
- [`TODOS.md`](TODOS.md) - Current sprint tasks
- GitHub Issues - Bug reports & feature requests

## 📝 License

MIT License (to be added)

## 🔗 Useful Links

- [Anthropic Claude Agent SDK Documentation](https://docs.anthropic.com/en/docs/agents)
- [Model Context Protocol (MCP) Specification](https://modelcontextprotocol.io/)
- [Project Specifications (v2)](docs/specs/intelligent-news-aggregator-spec-v2.md)
- [Architecture Design (v2)](docs/architecture/news-aggregator-architecture-v2.md)

---

**Last Updated:** October 23, 2025
**Version:** 0.1.0 (Pre-Alpha)
**Status:** Planning → Implementation

*Built with Claude Agent SDK + Model Context Protocol*
