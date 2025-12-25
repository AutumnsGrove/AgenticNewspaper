"""Parser service for content extraction.

Uses newspaper3k and readability-lxml for deterministic content extraction.
NO LLM CALLS - this is fast, free, and reliable.

Usage:
    from src.services import ParserService

    parser = ParserService()
    content = await parser.parse_url("https://example.com/article")
    print(content.title, content.text, content.author)
"""

import asyncio
import hashlib
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

# Optional imports with fallbacks
try:
    from newspaper import Article as NewspaperArticle
    from newspaper import Config as NewspaperConfig
    HAS_NEWSPAPER = True
except ImportError:
    HAS_NEWSPAPER = False

try:
    from readability import Document as ReadabilityDocument
    HAS_READABILITY = True
except ImportError:
    HAS_READABILITY = False

try:
    import html2text
    HAS_HTML2TEXT = True
except ImportError:
    HAS_HTML2TEXT = False


class ContentFormat(Enum):
    """Content format types."""

    HTML = "html"
    PDF = "pdf"
    PLAINTEXT = "plaintext"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


class ParseError(Exception):
    """Base exception for parsing errors."""

    def __init__(self, message: str, url: str = "", details: dict | None = None):
        super().__init__(message)
        self.url = url
        self.details = details or {}


class FetchError(ParseError):
    """Error fetching content from URL."""

    pass


class ExtractionError(ParseError):
    """Error extracting content from HTML."""

    pass


@dataclass
class ParserConfig:
    """Configuration for parser service."""

    timeout: float = 30.0
    max_retries: int = 2
    min_content_length: int = 100
    max_content_length: int = 100000
    follow_redirects: bool = True
    verify_ssl: bool = True
    user_agent: str = (
        "Mozilla/5.0 (compatible; TheDailyClearing/1.0; +https://clearing.autumnsgrove.com)"
    )
    accept_language: str = "en-US,en;q=0.9"

    # Extraction preferences
    prefer_newspaper: bool = True  # Use newspaper3k first, fall back to readability
    extract_images: bool = True
    extract_videos: bool = False
    clean_html: bool = True


@dataclass
class ParsedContent:
    """Parsed article content."""

    url: str
    title: str
    text: str
    html: str = ""
    author: str | None = None
    authors: list[str] = field(default_factory=list)
    published_date: datetime | None = None
    source: str = ""
    word_count: int = 0
    reading_time_minutes: int = 0
    format: ContentFormat = ContentFormat.HTML

    # Metadata
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    top_image: str = ""
    videos: list[str] = field(default_factory=list)
    language: str = "en"

    # Extraction quality
    extraction_method: str = ""
    parse_quality: float = 0.0  # 0-1 confidence score
    extracted_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Calculate derived fields."""
        if self.word_count == 0 and self.text:
            self.word_count = len(self.text.split())

        if self.reading_time_minutes == 0 and self.word_count > 0:
            # Average reading speed: 200-250 words per minute
            self.reading_time_minutes = max(1, self.word_count // 225)

        if not self.source and self.url:
            try:
                parsed = urlparse(self.url)
                self.source = parsed.netloc.replace("www.", "")
            except Exception:
                pass

    @property
    def content_hash(self) -> str:
        """Generate hash of content for deduplication."""
        return hashlib.md5(self.text.encode()).hexdigest()[:12]

    @property
    def is_valid(self) -> bool:
        """Check if parsed content is valid."""
        return (
            bool(self.title) and
            bool(self.text) and
            len(self.text) >= 100
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "text": self.text[:500] + "..." if len(self.text) > 500 else self.text,
            "author": self.author,
            "authors": self.authors,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "source": self.source,
            "word_count": self.word_count,
            "reading_time_minutes": self.reading_time_minutes,
            "format": self.format.value,
            "description": self.description,
            "keywords": self.keywords,
            "top_image": self.top_image,
            "language": self.language,
            "extraction_method": self.extraction_method,
            "parse_quality": self.parse_quality,
            "is_valid": self.is_valid,
            "content_hash": self.content_hash,
        }


@dataclass
class ParserStats:
    """Statistics for parsing operations."""

    total_parsed: int = 0
    successful: int = 0
    failed: int = 0
    total_time: float = 0.0
    total_words: int = 0

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        total = self.successful + self.failed
        return (self.successful / total * 100) if total > 0 else 0.0

    @property
    def average_time(self) -> float:
        """Average parse time in seconds."""
        return self.total_time / self.total_parsed if self.total_parsed > 0 else 0.0


class ParserService:
    """
    Content extraction service using newspaper3k and readability.

    Features:
    - Automatic format detection (HTML, PDF, plaintext)
    - Multiple extraction methods with fallback
    - Content cleaning and normalization
    - Metadata extraction (author, date, keywords)
    - No LLM calls - fully deterministic
    """

    def __init__(self, config: ParserConfig | None = None):
        """
        Initialize parser service.

        Args:
            config: Parser configuration
        """
        self.config = config or ParserConfig()
        self._stats = ParserStats()
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._client: httpx.AsyncClient | None = None

        # Initialize newspaper config if available
        if HAS_NEWSPAPER:
            self._newspaper_config = NewspaperConfig()
            self._newspaper_config.browser_user_agent = self.config.user_agent
            self._newspaper_config.request_timeout = self.config.timeout
            self._newspaper_config.fetch_images = self.config.extract_images
            self._newspaper_config.memoize_articles = False

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                follow_redirects=self.config.follow_redirects,
                verify=self.config.verify_ssl,
                headers={
                    "User-Agent": self.config.user_agent,
                    "Accept-Language": self.config.accept_language,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close resources."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._executor.shutdown(wait=False)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def parse_url(self, url: str) -> ParsedContent:
        """
        Parse content from a URL.

        Args:
            url: URL to fetch and parse

        Returns:
            ParsedContent with extracted text and metadata

        Raises:
            FetchError: If URL cannot be fetched
            ExtractionError: If content cannot be extracted
        """
        start_time = time.time()

        try:
            # Fetch HTML content
            html = await self._fetch_url(url)

            # Detect format
            content_format = self._detect_format(url, html)

            if content_format == ContentFormat.PDF:
                # PDF parsing would require additional libraries
                raise ExtractionError("PDF parsing not yet implemented", url=url)

            # Extract content using multiple methods
            content = await self._extract_content(url, html)

            # Update stats
            elapsed = time.time() - start_time
            self._stats.total_parsed += 1
            self._stats.successful += 1
            self._stats.total_time += elapsed
            self._stats.total_words += content.word_count

            return content

        except Exception as e:
            self._stats.total_parsed += 1
            self._stats.failed += 1
            if isinstance(e, (FetchError, ExtractionError)):
                raise
            raise ExtractionError(f"Failed to parse: {str(e)}", url=url)

    async def _fetch_url(self, url: str) -> str:
        """Fetch HTML content from URL."""
        client = await self._get_client()

        try:
            response = await client.get(url)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                if "application/pdf" in content_type:
                    raise FetchError("PDF content not supported", url=url)
                # Still try to parse as text
                pass

            return response.text

        except httpx.HTTPStatusError as e:
            raise FetchError(
                f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
                url=url,
            )
        except httpx.TimeoutException:
            raise FetchError(f"Timeout after {self.config.timeout}s", url=url)
        except httpx.RequestError as e:
            raise FetchError(f"Request failed: {str(e)}", url=url)

    def _detect_format(self, url: str, content: str) -> ContentFormat:
        """Detect content format from URL and content."""
        url_lower = url.lower()

        if url_lower.endswith(".pdf"):
            return ContentFormat.PDF
        elif url_lower.endswith(".md"):
            return ContentFormat.MARKDOWN
        elif url_lower.endswith(".txt"):
            return ContentFormat.PLAINTEXT

        # Check content
        content_start = content[:500].lower()
        if "<!doctype html" in content_start or "<html" in content_start:
            return ContentFormat.HTML
        elif content.startswith("%PDF"):
            return ContentFormat.PDF
        elif content.startswith("# ") or "\n## " in content[:1000]:
            return ContentFormat.MARKDOWN

        return ContentFormat.HTML

    async def _extract_content(self, url: str, html: str) -> ParsedContent:
        """
        Extract content using multiple methods with fallback.

        Priority:
        1. newspaper3k (best for news articles)
        2. readability-lxml (good for general articles)
        3. BeautifulSoup fallback (basic extraction)
        """
        errors = []

        # Try newspaper3k first
        if HAS_NEWSPAPER and self.config.prefer_newspaper:
            try:
                content = await self._extract_with_newspaper(url, html)
                if content.is_valid:
                    content.extraction_method = "newspaper3k"
                    content.parse_quality = self._calculate_quality(content)
                    return content
            except Exception as e:
                errors.append(f"newspaper3k: {str(e)}")

        # Try readability
        if HAS_READABILITY:
            try:
                content = await self._extract_with_readability(url, html)
                if content.is_valid:
                    content.extraction_method = "readability"
                    content.parse_quality = self._calculate_quality(content)
                    return content
            except Exception as e:
                errors.append(f"readability: {str(e)}")

        # Fallback to BeautifulSoup
        try:
            content = self._extract_with_beautifulsoup(url, html)
            if content.is_valid:
                content.extraction_method = "beautifulsoup"
                content.parse_quality = self._calculate_quality(content)
                return content
        except Exception as e:
            errors.append(f"beautifulsoup: {str(e)}")

        raise ExtractionError(
            f"All extraction methods failed: {'; '.join(errors)}",
            url=url,
        )

    async def _extract_with_newspaper(self, url: str, html: str) -> ParsedContent:
        """Extract using newspaper3k."""
        loop = asyncio.get_event_loop()

        def _extract():
            article = NewspaperArticle(url, config=self._newspaper_config)
            article.set_html(html)
            article.parse()

            # Get metadata
            authors = article.authors if article.authors else []
            author = authors[0] if authors else None

            return ParsedContent(
                url=url,
                title=article.title or "",
                text=article.text or "",
                html=html,
                author=author,
                authors=authors,
                published_date=article.publish_date,
                description=article.meta_description or "",
                keywords=list(article.keywords) if article.keywords else [],
                images=list(article.images) if article.images else [],
                top_image=article.top_image or "",
                videos=list(article.movies) if article.movies else [],
                language=article.meta_lang or "en",
                format=ContentFormat.HTML,
            )

        return await loop.run_in_executor(self._executor, _extract)

    async def _extract_with_readability(self, url: str, html: str) -> ParsedContent:
        """Extract using readability-lxml."""
        loop = asyncio.get_event_loop()

        def _extract():
            doc = ReadabilityDocument(html)

            # Convert HTML to plain text
            content_html = doc.summary()
            soup = BeautifulSoup(content_html, "lxml")
            text = soup.get_text(separator="\n", strip=True)

            # Clean up excessive whitespace
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r" +", " ", text)

            # Extract metadata from original HTML
            original_soup = BeautifulSoup(html, "lxml")
            meta = self._extract_metadata(original_soup)

            return ParsedContent(
                url=url,
                title=doc.short_title() or doc.title() or meta.get("title", ""),
                text=text,
                html=content_html,
                author=meta.get("author"),
                published_date=meta.get("published_date"),
                description=meta.get("description", ""),
                keywords=meta.get("keywords", []),
                images=meta.get("images", []),
                top_image=meta.get("top_image", ""),
                language=meta.get("language", "en"),
                format=ContentFormat.HTML,
            )

        return await loop.run_in_executor(self._executor, _extract)

    def _extract_with_beautifulsoup(self, url: str, html: str) -> ParsedContent:
        """Basic extraction using BeautifulSoup."""
        soup = BeautifulSoup(html, "lxml")

        # Remove script, style, and navigation elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()

        # Try to find main content
        main_content = (
            soup.find("article") or
            soup.find("main") or
            soup.find(class_=re.compile(r"article|content|post|entry", re.I)) or
            soup.find(id=re.compile(r"article|content|post|entry", re.I)) or
            soup.body
        )

        if main_content:
            text = main_content.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Clean up
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" +", " ", text)

        # Extract metadata
        meta = self._extract_metadata(soup)

        return ParsedContent(
            url=url,
            title=meta.get("title", ""),
            text=text,
            html=str(main_content) if main_content else "",
            author=meta.get("author"),
            published_date=meta.get("published_date"),
            description=meta.get("description", ""),
            keywords=meta.get("keywords", []),
            images=meta.get("images", []),
            top_image=meta.get("top_image", ""),
            language=meta.get("language", "en"),
            format=ContentFormat.HTML,
        )

    def _extract_metadata(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract metadata from HTML using meta tags and schema."""
        meta: dict[str, Any] = {}

        # Title
        title_tag = soup.find("title")
        og_title = soup.find("meta", property="og:title")
        meta["title"] = (
            og_title.get("content") if og_title else
            title_tag.string if title_tag else ""
        )

        # Description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        og_desc = soup.find("meta", property="og:description")
        meta["description"] = (
            og_desc.get("content") if og_desc else
            desc_tag.get("content") if desc_tag else ""
        )

        # Author
        author_tag = soup.find("meta", attrs={"name": "author"})
        meta["author"] = author_tag.get("content") if author_tag else None

        # Published date
        date_tags = [
            soup.find("meta", property="article:published_time"),
            soup.find("meta", attrs={"name": "date"}),
            soup.find("time", attrs={"datetime": True}),
        ]
        for tag in date_tags:
            if tag:
                date_str = tag.get("content") or tag.get("datetime")
                if date_str:
                    try:
                        meta["published_date"] = datetime.fromisoformat(
                            date_str.replace("Z", "+00:00")
                        )
                        break
                    except ValueError:
                        pass

        # Keywords
        keywords_tag = soup.find("meta", attrs={"name": "keywords"})
        if keywords_tag and keywords_tag.get("content"):
            meta["keywords"] = [k.strip() for k in keywords_tag["content"].split(",")]
        else:
            meta["keywords"] = []

        # Images
        og_image = soup.find("meta", property="og:image")
        meta["top_image"] = og_image.get("content") if og_image else ""

        img_tags = soup.find_all("img", src=True)
        meta["images"] = [img["src"] for img in img_tags[:10]]

        # Language
        html_tag = soup.find("html")
        meta["language"] = html_tag.get("lang", "en") if html_tag else "en"

        return meta

    def _calculate_quality(self, content: ParsedContent) -> float:
        """Calculate parse quality score (0-1)."""
        score = 0.0

        # Has title
        if content.title:
            score += 0.2

        # Has reasonable content length
        if content.word_count >= 100:
            score += 0.2
        if content.word_count >= 300:
            score += 0.1

        # Has author
        if content.author:
            score += 0.1

        # Has published date
        if content.published_date:
            score += 0.1

        # Has description
        if content.description:
            score += 0.1

        # Has images
        if content.images:
            score += 0.1

        # Content doesn't look like error page
        error_indicators = ["404", "not found", "error", "access denied"]
        if not any(ind in content.title.lower() for ind in error_indicators):
            score += 0.1

        return min(1.0, score)

    async def parse_urls(
        self,
        urls: list[str],
        max_concurrent: int = 5,
    ) -> list[ParsedContent | ParseError]:
        """
        Parse multiple URLs concurrently.

        Args:
            urls: List of URLs to parse
            max_concurrent: Maximum concurrent parsing tasks

        Returns:
            List of ParsedContent or ParseError for each URL
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def parse_with_limit(url: str):
            async with semaphore:
                try:
                    return await self.parse_url(url)
                except (FetchError, ExtractionError) as e:
                    return e

        tasks = [parse_with_limit(url) for url in urls]
        return await asyncio.gather(*tasks)

    def parse_html(self, html: str, url: str = "") -> ParsedContent:
        """
        Parse pre-fetched HTML content.

        Args:
            html: HTML content string
            url: Original URL (for metadata)

        Returns:
            ParsedContent with extracted text
        """
        # Use synchronous extraction
        if HAS_NEWSPAPER and self.config.prefer_newspaper:
            try:
                article = NewspaperArticle(url, config=self._newspaper_config)
                article.set_html(html)
                article.parse()

                authors = article.authors if article.authors else []
                author = authors[0] if authors else None

                content = ParsedContent(
                    url=url,
                    title=article.title or "",
                    text=article.text or "",
                    html=html,
                    author=author,
                    authors=authors,
                    published_date=article.publish_date,
                    description=article.meta_description or "",
                    keywords=list(article.keywords) if article.keywords else [],
                    images=list(article.images) if article.images else [],
                    top_image=article.top_image or "",
                    language=article.meta_lang or "en",
                    format=ContentFormat.HTML,
                    extraction_method="newspaper3k",
                )
                content.parse_quality = self._calculate_quality(content)
                return content
            except Exception:
                pass

        # Fallback to BeautifulSoup
        content = self._extract_with_beautifulsoup(url, html)
        content.parse_quality = self._calculate_quality(content)
        return content

    def get_stats(self) -> dict[str, Any]:
        """Get parser statistics."""
        return {
            "total_parsed": self._stats.total_parsed,
            "successful": self._stats.successful,
            "failed": self._stats.failed,
            "success_rate": self._stats.success_rate,
            "total_time": self._stats.total_time,
            "average_time": self._stats.average_time,
            "total_words": self._stats.total_words,
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = ParserStats()
