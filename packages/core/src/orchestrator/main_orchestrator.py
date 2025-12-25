"""Main Orchestrator - Coordinates all agents to generate daily digest."""

import asyncio
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path
import time

from ..models.article import ArticleURL, ParsedArticle, DigestMetadata
from ..agents.tier1_execution.search_agent import SearchAgent
from ..agents.tier1_execution.parser_agent import ParserAgent
from ..agents.tier2_reasoning.synthesis_agent import SynthesisAgent
from ..utils.config_loader import load_user_preferences


class MainOrchestrator:
    """
    Main Orchestrator - Coordinates the multi-agent system.

    Workflow:
    1. Load user preferences
    2. Search for articles (SearchAgent)
    3. Fetch and parse articles (ParserAgent)
    4. Synthesize digest (SynthesisAgent)
    5. Save to file
    """

    def __init__(self, user_preferences: Dict[str, Any] = None):
        """
        Initialize orchestrator with agents.

        Args:
            user_preferences: User preferences dict (loads from config if None)
        """
        # Load preferences
        self.preferences = user_preferences or load_user_preferences()

        # Initialize agents
        self.search_agent = SearchAgent()
        self.parser_agent = ParserAgent()
        self.synthesis_agent = SynthesisAgent()

        # Stats
        self.start_time = None
        self.end_time = None

    async def generate_digest(self) -> str:
        """
        Generate complete daily digest.

        Returns:
            Path to generated digest file
        """
        print("=" * 70)
        print("INTELLIGENT NEWS AGGREGATOR - Generating Digest")
        print("=" * 70)

        self.start_time = time.time()

        # Step 1: Search for articles
        print("\n[1/4] Searching for articles...")
        articles_by_topic = await self._search_all_topics()

        # Step 2: Parse articles
        print("\n[2/4] Fetching and parsing articles...")
        parsed_articles_by_topic = await self._parse_all_articles(articles_by_topic)

        # Step 3: Synthesize digest
        print("\n[3/4] Synthesizing HN-style digest...")
        metadata = self._create_metadata(parsed_articles_by_topic)
        digest_content = await self.synthesis_agent.create_digest(
            parsed_articles_by_topic,
            self.preferences,
            metadata
        )

        # Step 4: Save digest
        print("\n[4/4] Saving digest...")
        digest_path = await self._save_digest(digest_content)

        self.end_time = time.time()

        # Print summary
        self._print_summary(digest_path, metadata)

        return str(digest_path)

    async def _search_all_topics(self) -> Dict[str, List[ArticleURL]]:
        """
        Search for articles across all configured topics.

        Returns:
            Dict mapping topic name to list of ArticleURLs
        """
        articles_by_topic = {}

        topics = self.preferences.get("topics", [])
        sources = self.preferences.get("sources", {}).get("tier1_premium", [])

        for topic in topics:
            topic_name = topic["name"]
            keywords = topic.get("keywords", [])
            exclude_keywords = topic.get("exclude_keywords", [])
            max_articles = topic.get("max_articles", 5)

            print(f"  Searching: {topic_name} (max {max_articles} articles)")

            articles = await self.search_agent.search_topic(
                topic_name=topic_name,
                keywords=keywords,
                exclude_keywords=exclude_keywords,
                max_results=max_articles * 2,  # Get extra for filtering
                sources=sources
            )

            articles_by_topic[topic_name] = articles[:max_articles]
            print(f"    Found: {len(articles_by_topic[topic_name])} articles")

        return articles_by_topic

    async def _parse_all_articles(
        self,
        articles_by_topic: Dict[str, List[ArticleURL]]
    ) -> Dict[str, List[ParsedArticle]]:
        """
        Parse all discovered articles.

        Args:
            articles_by_topic: Dict of ArticleURLs by topic

        Returns:
            Dict of ParsedArticles by topic
        """
        parsed_by_topic = {}

        for topic_name, article_urls in articles_by_topic.items():
            print(f"  Parsing {len(article_urls)} articles for: {topic_name}")

            # Parse articles in parallel (limited concurrency)
            max_concurrent = self.preferences.get("advanced", {}).get(
                "max_parallel_parsers", 5
            )

            parsed_articles = await self._parse_articles_parallel(
                article_urls,
                max_concurrent
            )

            # Filter out failed parses
            parsed_articles = [a for a in parsed_articles if a is not None]

            parsed_by_topic[topic_name] = parsed_articles
            print(f"    Successfully parsed: {len(parsed_articles)}/{len(article_urls)}")

        return parsed_by_topic

    async def _parse_articles_parallel(
        self,
        article_urls: List[ArticleURL],
        max_concurrent: int
    ) -> List[ParsedArticle]:
        """
        Parse articles in parallel with concurrency limit.

        Args:
            article_urls: List of ArticleURLs to parse
            max_concurrent: Maximum concurrent parsing tasks

        Returns:
            List of ParsedArticles (may include None for failures)
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def parse_with_limit(article_url):
            async with semaphore:
                return await self.parser_agent.parse_article(article_url)

        tasks = [parse_with_limit(url) for url in article_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        parsed = []
        for result in results:
            if isinstance(result, ParsedArticle):
                parsed.append(result)
            elif isinstance(result, Exception):
                print(f"    ⚠ Parse exception: {result}")

        return parsed

    def _create_metadata(
        self,
        parsed_articles_by_topic: Dict[str, List[ParsedArticle]]
    ) -> DigestMetadata:
        """
        Create digest metadata.

        Args:
            parsed_articles_by_topic: Parsed articles by topic

        Returns:
            DigestMetadata object
        """
        # Count articles
        total_parsed = sum(len(articles) for articles in parsed_articles_by_topic.values())

        # Collect stats from all agents
        search_stats = self.search_agent.get_stats()
        parser_stats = self.parser_agent.get_stats()
        synthesis_stats = self.synthesis_agent.get_stats()

        # Calculate totals
        total_tokens = (
            search_stats["mcp_stats"]["total_tokens"] +
            parser_stats["mcp_stats"]["total_tokens"] +
            synthesis_stats["mcp_stats"]["total_tokens"]
        )

        total_cost = (
            search_stats["mcp_stats"]["total_cost_usd"] +
            parser_stats["mcp_stats"]["total_cost_usd"] +
            synthesis_stats["mcp_stats"]["total_cost_usd"]
        )

        # Create metadata
        digest_id = datetime.now().strftime("%Y-%m-%d")

        metadata = DigestMetadata(
            digest_id=digest_id,
            generated_at=datetime.now(),
            topics_covered=list(parsed_articles_by_topic.keys()),
            total_articles_found=search_stats["search_count"] * 5,  # Estimate
            total_articles_parsed=total_parsed,
            total_articles_analyzed=total_parsed,  # Phase 1: no quality filtering yet
            total_articles_included=total_parsed,  # Phase 1: include all parsed
            total_tokens_used=total_tokens,
            total_cost_usd=total_cost,
            model_usage={
                "tier1": search_stats["mcp_stats"],
                "tier2": synthesis_stats["mcp_stats"]
            }
        )

        return metadata

    async def _save_digest(self, digest_content: str) -> Path:
        """
        Save digest to file.

        Args:
            digest_content: Markdown digest content

        Returns:
            Path to saved file
        """
        # Create outputs directory if needed
        output_dir = Path("outputs/daily_digests")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}.md"
        filepath = output_dir / filename

        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(digest_content)

        return filepath

    def _print_summary(self, digest_path: Path, metadata: DigestMetadata):
        """
        Print generation summary.

        Args:
            digest_path: Path to saved digest
            metadata: Digest metadata
        """
        processing_time = self.end_time - self.start_time

        print("\n" + "=" * 70)
        print("DIGEST GENERATION COMPLETE")
        print("=" * 70)
        print(f"\n📄 Saved to: {digest_path}")
        print(f"\n📊 Statistics:")
        print(f"  Topics: {len(metadata.topics_covered)}")
        print(f"  Articles parsed: {metadata.total_articles_parsed}")
        print(f"  Articles included: {metadata.total_articles_included}")
        print(f"  Processing time: {processing_time:.1f}s")
        print(f"\n💰 Cost Breakdown:")
        print(f"  Total tokens: {metadata.total_tokens_used:,}")
        print(f"  Total cost: ${metadata.total_cost_usd:.4f}")
        print(f"  Target: ${self.preferences.get('budget', {}).get('daily_target_usd', 0.30):.2f}")

        # Budget warning
        daily_target = self.preferences.get("budget", {}).get("daily_target_usd", 0.30)
        if metadata.total_cost_usd > daily_target:
            print(f"  ⚠️  OVER BUDGET by ${metadata.total_cost_usd - daily_target:.4f}")
        else:
            print(f"  ✓ Under budget by ${daily_target - metadata.total_cost_usd:.4f}")

        print("\n" + "=" * 70)
