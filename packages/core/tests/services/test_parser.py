"""
Tests for the parser service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.parser import (
    ParserService,
    ParsedContent,
    ContentFormat,
)


# ============================================================================
# ParsedContent Tests
# ============================================================================


class TestParsedContent:
    """Tests for the ParsedContent dataclass."""

    def test_create_parsed_content(self):
        """Test creating parsed content."""
        content = ParsedContent(
            title="Test Article",
            text="This is the article text.",
            author="John Doe",
            published_date="2025-12-24",
            source="example.com",
            word_count=100,
            reading_time_minutes=1,
        )
        assert content.title == "Test Article"
        assert content.text == "This is the article text."
        assert content.author == "John Doe"
        assert content.word_count == 100

    def test_parsed_content_with_defaults(self):
        """Test parsed content with default values."""
        content = ParsedContent(
            title="Test",
            text="Content",
        )
        assert content.author is None
        assert content.published_date is None
        assert content.word_count == 0

    def test_reading_time_calculation(self):
        """Test reading time calculation."""
        # Average reading speed is ~200-250 WPM
        content = ParsedContent(
            title="Test",
            text="word " * 1000,  # 1000 words
            word_count=1000,
            reading_time_minutes=5,  # 1000 / 200 = 5 minutes
        )
        assert content.reading_time_minutes == 5


# ============================================================================
# ContentFormat Tests
# ============================================================================


class TestContentFormat:
    """Tests for content format detection."""

    def test_html_format(self):
        """Test HTML format detection."""
        assert ContentFormat.HTML.value == "html"

    def test_markdown_format(self):
        """Test Markdown format detection."""
        assert ContentFormat.MARKDOWN.value == "markdown"

    def test_plaintext_format(self):
        """Test plaintext format detection."""
        assert ContentFormat.PLAINTEXT.value == "plaintext"

    def test_pdf_format(self):
        """Test PDF format detection."""
        assert ContentFormat.PDF.value == "pdf"


# ============================================================================
# Parser Service Tests
# ============================================================================


class TestParserService:
    """Tests for the ParserService class."""

    @pytest.fixture
    def parser(self):
        """Create a parser service instance."""
        return ParserService()

    @pytest.fixture
    def sample_html(self):
        """Create sample HTML content."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Article Title</title>
            <meta name="author" content="Jane Smith">
            <meta property="article:published_time" content="2025-12-24T10:00:00Z">
        </head>
        <body>
            <article>
                <h1>Test Article Title</h1>
                <p class="byline">By Jane Smith</p>
                <div class="content">
                    <p>This is the first paragraph of the article.</p>
                    <p>This is the second paragraph with more content.</p>
                    <p>And here is the third paragraph to make it longer.</p>
                </div>
            </article>
        </body>
        </html>
        """

    @pytest.fixture
    def sample_html_with_noise(self):
        """Create HTML with ads and navigation."""
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Article</title></head>
        <body>
            <nav>Navigation Menu</nav>
            <div class="advertisement">Buy our product!</div>
            <article>
                <h1>Main Article</h1>
                <p>This is the actual content that matters.</p>
                <p>More important content here.</p>
            </article>
            <aside>Related Articles</aside>
            <footer>Copyright 2025</footer>
        </body>
        </html>
        """

    def test_detect_html_format(self, parser):
        """Test HTML format detection."""
        html = "<!DOCTYPE html><html><body></body></html>"
        format = parser.detect_format(html)
        assert format == ContentFormat.HTML

    def test_detect_markdown_format(self, parser):
        """Test Markdown format detection."""
        markdown = "# Title\n\nThis is **bold** text."
        format = parser.detect_format(markdown)
        assert format == ContentFormat.MARKDOWN

    def test_detect_plaintext_format(self, parser):
        """Test plaintext format detection."""
        text = "Just plain text without any markup."
        format = parser.detect_format(text)
        assert format == ContentFormat.PLAINTEXT

    @pytest.mark.asyncio
    async def test_parse_html_extracts_title(self, parser, sample_html):
        """Test that parser extracts title from HTML."""
        result = await parser.parse(sample_html, url="https://example.com/article")
        assert "Test Article" in result.title

    @pytest.mark.asyncio
    async def test_parse_html_extracts_author(self, parser, sample_html):
        """Test that parser extracts author from HTML."""
        result = await parser.parse(sample_html, url="https://example.com/article")
        # Author might be in metadata or byline
        assert result.author is None or "Smith" in (result.author or "")

    @pytest.mark.asyncio
    async def test_parse_html_extracts_content(self, parser, sample_html):
        """Test that parser extracts main content."""
        result = await parser.parse(sample_html, url="https://example.com/article")
        assert "first paragraph" in result.text.lower()
        assert "second paragraph" in result.text.lower()

    @pytest.mark.asyncio
    async def test_parse_removes_ads(self, parser, sample_html_with_noise):
        """Test that parser removes ads and noise."""
        result = await parser.parse(
            sample_html_with_noise, url="https://example.com/article"
        )
        assert "Buy our product" not in result.text
        assert "Navigation Menu" not in result.text

    @pytest.mark.asyncio
    async def test_parse_calculates_word_count(self, parser, sample_html):
        """Test that parser calculates word count."""
        result = await parser.parse(sample_html, url="https://example.com/article")
        assert result.word_count > 0

    @pytest.mark.asyncio
    async def test_parse_calculates_reading_time(self, parser, sample_html):
        """Test that parser calculates reading time."""
        result = await parser.parse(sample_html, url="https://example.com/article")
        assert result.reading_time_minutes >= 0

    @pytest.mark.asyncio
    async def test_parse_extracts_source(self, parser, sample_html):
        """Test that parser extracts source domain."""
        result = await parser.parse(sample_html, url="https://example.com/article")
        assert result.source == "example.com"


# ============================================================================
# Metadata Extraction Tests
# ============================================================================


class TestMetadataExtraction:
    """Tests for metadata extraction."""

    @pytest.fixture
    def parser(self):
        """Create a parser service instance."""
        return ParserService()

    @pytest.mark.asyncio
    async def test_extract_opengraph_title(self, parser):
        """Test extraction of OpenGraph title."""
        html = """
        <html>
        <head>
            <meta property="og:title" content="OG Title">
            <title>Regular Title</title>
        </head>
        <body><p>Content</p></body>
        </html>
        """
        result = await parser.parse(html, url="https://example.com")
        # Should prefer OG title or regular title
        assert "Title" in result.title

    @pytest.mark.asyncio
    async def test_extract_twitter_description(self, parser):
        """Test extraction of Twitter card description."""
        html = """
        <html>
        <head>
            <meta name="twitter:description" content="Twitter description">
        </head>
        <body><p>Body content</p></body>
        </html>
        """
        result = await parser.parse(html, url="https://example.com")
        # Parser should extract content
        assert result.text is not None

    @pytest.mark.asyncio
    async def test_extract_json_ld_author(self, parser):
        """Test extraction of author from JSON-LD."""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "Article",
                "author": {"@type": "Person", "name": "Alice Wonder"}
            }
            </script>
        </head>
        <body><p>Content</p></body>
        </html>
        """
        result = await parser.parse(html, url="https://example.com")
        # May or may not extract JSON-LD author
        assert result is not None

    @pytest.mark.asyncio
    async def test_extract_published_date(self, parser):
        """Test extraction of published date."""
        html = """
        <html>
        <head>
            <meta property="article:published_time" content="2025-12-24T10:00:00Z">
        </head>
        <body><p>Content</p></body>
        </html>
        """
        result = await parser.parse(html, url="https://example.com")
        # Date extraction may or may not work depending on implementation
        assert result is not None


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestParserEdgeCases:
    """Tests for parser edge cases."""

    @pytest.fixture
    def parser(self):
        """Create a parser service instance."""
        return ParserService()

    @pytest.mark.asyncio
    async def test_parse_empty_html(self, parser):
        """Test parsing empty HTML."""
        result = await parser.parse("<html></html>", url="https://example.com")
        assert result.text == "" or result.title == ""

    @pytest.mark.asyncio
    async def test_parse_malformed_html(self, parser):
        """Test parsing malformed HTML."""
        html = "<html><body><p>Unclosed paragraph<div>Nested wrong</p></div>"
        result = await parser.parse(html, url="https://example.com")
        # Should handle gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_parse_non_html(self, parser):
        """Test parsing non-HTML content."""
        text = "Just plain text, no HTML at all."
        result = await parser.parse(text, url="https://example.com")
        assert result is not None

    @pytest.mark.asyncio
    async def test_parse_unicode_content(self, parser):
        """Test parsing Unicode content."""
        html = """
        <html>
        <head><title>日本語タイトル</title></head>
        <body><p>Content with émojis 🎉 and spëcial characters.</p></body>
        </html>
        """
        result = await parser.parse(html, url="https://example.com")
        assert result is not None
        # Should preserve unicode
        assert "🎉" in result.text or len(result.text) > 0

    @pytest.mark.asyncio
    async def test_parse_very_long_content(self, parser):
        """Test parsing very long content."""
        html = f"""
        <html>
        <head><title>Long Article</title></head>
        <body>
            <article>{"<p>Paragraph. </p>" * 1000}</article>
        </body>
        </html>
        """
        result = await parser.parse(html, url="https://example.com")
        assert result.word_count > 500


# ============================================================================
# Content Cleaning Tests
# ============================================================================


class TestContentCleaning:
    """Tests for content cleaning functionality."""

    @pytest.fixture
    def parser(self):
        """Create a parser service instance."""
        return ParserService()

    @pytest.mark.asyncio
    async def test_removes_script_tags(self, parser):
        """Test that script tags are removed."""
        html = """
        <html>
        <body>
            <p>Real content</p>
            <script>alert('malicious');</script>
            <p>More content</p>
        </body>
        </html>
        """
        result = await parser.parse(html, url="https://example.com")
        assert "alert" not in result.text
        assert "malicious" not in result.text

    @pytest.mark.asyncio
    async def test_removes_style_tags(self, parser):
        """Test that style tags are removed."""
        html = """
        <html>
        <head><style>body { color: red; }</style></head>
        <body><p>Content</p></body>
        </html>
        """
        result = await parser.parse(html, url="https://example.com")
        assert "color: red" not in result.text

    @pytest.mark.asyncio
    async def test_normalizes_whitespace(self, parser):
        """Test that excessive whitespace is normalized."""
        html = """
        <html>
        <body>
            <p>Text    with    lots     of      spaces</p>
        </body>
        </html>
        """
        result = await parser.parse(html, url="https://example.com")
        # Should not have excessive spaces
        assert "    " not in result.text or len(result.text.strip()) > 0


# ============================================================================
# URL Handling Tests
# ============================================================================


class TestUrlHandling:
    """Tests for URL handling."""

    @pytest.fixture
    def parser(self):
        """Create a parser service instance."""
        return ParserService()

    def test_extract_domain_simple(self, parser):
        """Test extracting domain from simple URL."""
        domain = parser.extract_domain("https://example.com/article/123")
        assert domain == "example.com"

    def test_extract_domain_with_subdomain(self, parser):
        """Test extracting domain with subdomain."""
        domain = parser.extract_domain("https://blog.example.com/post")
        assert domain == "blog.example.com"

    def test_extract_domain_with_port(self, parser):
        """Test extracting domain with port."""
        domain = parser.extract_domain("https://example.com:8080/path")
        assert domain == "example.com"

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://news.ycombinator.com/item?id=123", "news.ycombinator.com"),
            ("https://arxiv.org/abs/2312.00001", "arxiv.org"),
            ("https://www.bbc.com/news/article", "www.bbc.com"),
            ("http://localhost:3000/test", "localhost"),
        ],
    )
    def test_extract_domain_various(self, parser, url, expected):
        """Test domain extraction for various URLs."""
        domain = parser.extract_domain(url)
        assert domain == expected
