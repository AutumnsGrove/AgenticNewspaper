"""Parser Agent - Tier 1 execution agent for fetching and parsing articles."""

from typing import Optional
import asyncio
import hashlib
from datetime import datetime
from ...models.article import ArticleURL, ParsedArticle, ArticleFormat
from ...mcp_servers import get_tier1_server


class ParserAgent:
    """
    Tier 1 Parser Agent - Fetches and extracts clean content from URLs.

    Handles HTML parsing, content extraction, and metadata processing.
    """

    def __init__(self):
        """Initialize Parser Agent with Tier 1 MCP server."""
        self.server = get_tier1_server()
        self.parse_count = 0
        self.success_count = 0
        self.failure_count = 0

    async def parse_article(
        self,
        article_url: ArticleURL,
        timeout_seconds: int = 30
    ) -> Optional[ParsedArticle]:
        """
        Fetch and parse an article from URL.

        Args:
            article_url: ArticleURL object with URL and metadata
            timeout_seconds: Timeout for fetching (default: 30)

        Returns:
            ParsedArticle if successful, None if failed
        """
        self.parse_count += 1

        try:
            # Fetch content
            raw_content = await self._fetch_url(
                article_url.url,
                timeout_seconds
            )

            if not raw_content:
                self.failure_count += 1
                return None

            # Detect format
            content_format = await self._detect_format(
                raw_content,
                article_url.url
            )

            # Extract article content
            parsed_content = await self._extract_content(
                raw_content,
                content_format,
                article_url
            )

            if not parsed_content:
                self.failure_count += 1
                return None

            # Create ParsedArticle
            article = ParsedArticle(
                article_id=self._generate_article_id(article_url.url),
                url=article_url.url,
                title=parsed_content.get("title", article_url.title),
                content=parsed_content["content"],
                author=parsed_content.get("author"),
                published_date=parsed_content.get("published_date", article_url.published_date),
                source=article_url.source,
                format=content_format,
                meta_description=parsed_content.get("description"),
                meta_keywords=parsed_content.get("keywords", []),
                parse_quality=parsed_content.get("quality", 0.7)
            )

            self.success_count += 1
            return article

        except Exception as e:
            print(f"  ⚠ Parser error for {article_url.url}: {e}")
            self.failure_count += 1
            return None

    async def _fetch_url(
        self,
        url: str,
        timeout_seconds: int
    ) -> Optional[str]:
        """
        Fetch content from URL.

        Args:
            url: URL to fetch
            timeout_seconds: Request timeout

        Returns:
            Raw content string or None if failed
        """
        # Phase 1: Return mock content
        # In Phase 2+, use requests or httpx to fetch real content

        await asyncio.sleep(0.1)  # Simulate network delay

        # Generate mock content based on URL
        mock_content = f"""
        <html>
        <head>
            <title>Article from {url}</title>
            <meta name="description" content="Detailed analysis and insights">
            <meta name="author" content="Tech Reporter">
        </head>
        <body>
            <article>
                <h1>Breaking News: Important Developments in AI</h1>
                <p class="byline">By Tech Reporter | Published: {datetime.now().strftime('%Y-%m-%d')}</p>

                <p>This is a mock article with substantive content about recent developments
                in artificial intelligence and machine learning.</p>

                <p>The research team has made significant progress in understanding how
                large language models process information. Key findings include improved
                efficiency in token processing and better context retention.</p>

                <h2>Technical Details</h2>

                <p>The new approach uses a novel architecture that reduces computational
                overhead while maintaining high accuracy. Preliminary benchmarks show
                a 40% improvement in inference speed.</p>

                <p>Implementation details suggest that the technique could be applied to
                a wide range of natural language processing tasks beyond the initial
                use case demonstrated.</p>

                <h2>Implications</h2>

                <p>These developments could have far-reaching consequences for the deployment
                of AI systems in production environments. Cost reduction and improved
                performance make the technology more accessible.</p>

                <p>Industry experts predict widespread adoption within the next 12-18 months,
                particularly in applications requiring real-time processing.</p>
            </article>
        </body>
        </html>
        """

        return mock_content

    async def _detect_format(
        self,
        content: str,
        url: str
    ) -> ArticleFormat:
        """
        Detect content format.

        Args:
            content: Raw content
            url: Source URL

        Returns:
            ArticleFormat enum
        """
        # Simple format detection
        if url.endswith('.pdf'):
            return ArticleFormat.PDF
        elif url.endswith('.md'):
            return ArticleFormat.MARKDOWN
        elif '<html' in content.lower() or '<body' in content.lower():
            return ArticleFormat.HTML
        else:
            return ArticleFormat.PLAINTEXT

    async def _extract_content(
        self,
        raw_content: str,
        content_format: ArticleFormat,
        article_url: ArticleURL
    ) -> Optional[dict]:
        """
        Extract clean article content using LLM.

        Args:
            raw_content: Raw HTML/text content
            content_format: Detected format
            article_url: Original article URL info

        Returns:
            Dict with extracted content and metadata
        """
        # For HTML content, use LLM to extract main article
        if content_format == ArticleFormat.HTML:
            return await self._extract_html_content(raw_content, article_url)
        else:
            # For other formats, return as-is (Phase 1 simplification)
            return {
                "title": article_url.title,
                "content": raw_content[:5000],  # Limit length
                "quality": 0.6
            }

    async def _extract_html_content(
        self,
        html_content: str,
        article_url: ArticleURL
    ) -> dict:
        """
        Extract article content from HTML using LLM.

        Args:
            html_content: Raw HTML
            article_url: Article URL info

        Returns:
            Dict with extracted content
        """
        # Truncate HTML to avoid token limits
        html_preview = html_content[:4000]

        prompt = f"""Extract the main article content from this HTML:

URL: {article_url.url}
Expected title: {article_url.title}

HTML:
{html_preview}

Extract and return in this format:
TITLE: [article title]
AUTHOR: [author name or "Unknown"]
CONTENT: [main article text, no HTML tags, preserve paragraphs with double newlines]

Focus on the main article content, ignore navigation, ads, and sidebars."""

        response = await self.server.complete(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.1  # Very low for factual extraction
        )

        # Parse LLM response
        content_data = self._parse_extraction_response(response.content)

        # Add default quality score
        content_data["quality"] = 0.8 if content_data.get("content") else 0.3

        return content_data

    def _parse_extraction_response(self, response: str) -> dict:
        """
        Parse LLM extraction response into structured data.

        Args:
            response: LLM response text

        Returns:
            Dict with title, author, content
        """
        data = {
            "title": "",
            "author": None,
            "content": "",
            "description": None,
            "keywords": []
        }

        # Simple parsing of structured response
        lines = response.split('\n')
        current_field = None

        for line in lines:
            line = line.strip()

            if line.startswith("TITLE:"):
                data["title"] = line[6:].strip()
                current_field = None
            elif line.startswith("AUTHOR:"):
                author = line[7:].strip()
                data["author"] = author if author.lower() != "unknown" else None
                current_field = None
            elif line.startswith("CONTENT:"):
                data["content"] = line[8:].strip()
                current_field = "content"
            elif current_field == "content" and line:
                # Continue content on new lines
                data["content"] += "\n\n" + line

        # Clean up content
        if data["content"]:
            data["content"] = data["content"].strip()

        return data

    def _generate_article_id(self, url: str) -> str:
        """
        Generate unique article ID from URL.

        Args:
            url: Article URL

        Returns:
            Article ID (hash-based)
        """
        return hashlib.md5(url.encode()).hexdigest()[:16]

    def get_stats(self) -> dict:
        """
        Get parser agent statistics.

        Returns:
            Dict with parser stats
        """
        success_rate = (
            self.success_count / self.parse_count
            if self.parse_count > 0 else 0.0
        )

        return {
            "agent": "ParserAgent",
            "tier": "1",
            "parse_count": self.parse_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(success_rate, 2),
            "mcp_stats": self.server.get_stats()
        }
