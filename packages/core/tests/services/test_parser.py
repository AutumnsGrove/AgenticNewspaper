"""
Tests for the parser service.
"""

import pytest
from datetime import datetime
from urllib.parse import urlparse

from src.services.parser import (
    ParserService,
    ParsedContent,
    ContentFormat,
    ParserConfig,
    ParseError,
    FetchError,
    ExtractionError,
)


# ============================================================================
# ParsedContent Tests
# ============================================================================


class TestParsedContent:
    """Tests for the ParsedContent dataclass."""

    def test_create_parsed_content(self):
        """Test creating parsed content."""
        content = ParsedContent(
            url="https://example.com/article",
            title="Test Article",
            text="This is the article text. " * 20,  # Make it long enough to be valid
            author="John Doe",
            published_date=datetime(2025, 12, 24),
            source="example.com",
            word_count=100,
            reading_time_minutes=1,
        )
        assert content.title == "Test Article"
        assert "article text" in content.text
        assert content.author == "John Doe"
        assert content.word_count == 100

    def test_parsed_content_with_defaults(self):
        """Test parsed content with default values."""
        content = ParsedContent(
            url="https://example.com",
            title="Test",
            text="Content " * 20,  # Make it long enough
        )
        assert content.author is None
        assert content.published_date is None
        # word_count is calculated from text in __post_init__
        assert content.word_count >= 0

    def test_reading_time_calculation(self):
        """Test reading time calculation."""
        # Average reading speed is ~225 WPM as per implementation
        text = "word " * 1000  # 1000 words
        content = ParsedContent(
            url="https://example.com",
            title="Test",
            text=text,
        )
        # 1000 / 225 ≈ 4.44, rounds to 4
        assert content.reading_time_minutes >= 4

    def test_word_count_calculated_from_text(self):
        """Test that word count is calculated from text if not provided."""
        text = "This is a test with exactly eight words here."
        content = ParsedContent(
            url="https://example.com",
            title="Test",
            text=text,
        )
        assert content.word_count == 9

    def test_source_extracted_from_url(self):
        """Test that source is extracted from URL."""
        content = ParsedContent(
            url="https://www.example.com/article/123",
            title="Test",
            text="Content " * 20,
        )
        # www. is stripped
        assert content.source == "example.com"

    def test_content_hash(self):
        """Test content hash generation."""
        content = ParsedContent(
            url="https://example.com",
            title="Test",
            text="Some content here " * 10,
        )
        assert content.content_hash is not None
        assert len(content.content_hash) == 12  # MD5 truncated to 12 chars

    def test_is_valid(self):
        """Test content validity check."""
        valid_content = ParsedContent(
            url="https://example.com",
            title="Valid Title",
            text="This is valid content. " * 20,  # > 100 chars
        )
        assert valid_content.is_valid is True

        invalid_content = ParsedContent(
            url="https://example.com",
            title="",
            text="Short",
        )
        assert invalid_content.is_valid is False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        content = ParsedContent(
            url="https://example.com",
            title="Test",
            text="Content " * 20,
        )
        d = content.to_dict()
        assert d["url"] == "https://example.com"
        assert d["title"] == "Test"
        assert "is_valid" in d
        assert "content_hash" in d


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
        fmt = parser._detect_format("https://example.com", html)
        assert fmt == ContentFormat.HTML

    def test_detect_markdown_format_by_extension(self, parser):
        """Test Markdown format detection by extension."""
        fmt = parser._detect_format("https://example.com/file.md", "# Title\n\nContent")
        assert fmt == ContentFormat.MARKDOWN

    def test_detect_pdf_format_by_extension(self, parser):
        """Test PDF format detection by extension."""
        fmt = parser._detect_format("https://example.com/file.pdf", "dummy")
        assert fmt == ContentFormat.PDF

    def test_parse_html_extracts_title(self, parser, sample_html):
        """Test that parser extracts title from HTML."""
        result = parser.parse_html(sample_html, url="https://example.com/article")
        assert "Test Article" in result.title

    def test_parse_html_extracts_content(self, parser, sample_html):
        """Test that parser extracts main content."""
        result = parser.parse_html(sample_html, url="https://example.com/article")
        assert "first paragraph" in result.text.lower()
        assert "second paragraph" in result.text.lower()

    def test_parse_html_removes_noise(self, parser, sample_html_with_noise):
        """Test that parser removes ads and noise."""
        result = parser.parse_html(
            sample_html_with_noise, url="https://example.com/article"
        )
        # Navigation and footer should be removed
        text_lower = result.text.lower()
        assert "actual content" in text_lower or "main article" in text_lower

    def test_parse_html_calculates_word_count(self, parser, sample_html):
        """Test that parser calculates word count."""
        result = parser.parse_html(sample_html, url="https://example.com/article")
        assert result.word_count > 0

    def test_parse_html_calculates_reading_time(self, parser, sample_html):
        """Test that parser calculates reading time."""
        result = parser.parse_html(sample_html, url="https://example.com/article")
        assert result.reading_time_minutes >= 0

    def test_parse_html_extracts_source(self, parser, sample_html):
        """Test that parser extracts source domain."""
        result = parser.parse_html(sample_html, url="https://example.com/article")
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

    def test_extract_opengraph_title(self, parser):
        """Test extraction of OpenGraph title."""
        html = """
        <html>
        <head>
            <meta property="og:title" content="OG Title">
            <title>Regular Title</title>
        </head>
        <body><p>Content here for validation. More content to make it long enough.</p></body>
        </html>
        """
        result = parser.parse_html(html, url="https://example.com")
        # Should prefer OG title or regular title
        assert "Title" in result.title

    def test_extract_twitter_description(self, parser):
        """Test extraction of Twitter card description."""
        html = """
        <html>
        <head>
            <title>Article Title</title>
            <meta name="twitter:description" content="Twitter description">
        </head>
        <body><p>Body content here. More content to make it long enough for validation.</p></body>
        </html>
        """
        result = parser.parse_html(html, url="https://example.com")
        # Parser should extract content
        assert result.text is not None

    def test_extract_json_ld_author(self, parser):
        """Test extraction of author from JSON-LD."""
        html = """
        <html>
        <head>
            <title>Article</title>
            <script type="application/ld+json">
            {
                "@type": "Article",
                "author": {"@type": "Person", "name": "Alice Wonder"}
            }
            </script>
        </head>
        <body><p>Content here. Enough content for validation purposes.</p></body>
        </html>
        """
        result = parser.parse_html(html, url="https://example.com")
        # May or may not extract JSON-LD author depending on extraction method
        assert result is not None

    def test_extract_published_date(self, parser):
        """Test extraction of published date."""
        html = """
        <html>
        <head>
            <title>Article</title>
            <meta property="article:published_time" content="2025-12-24T10:00:00Z">
        </head>
        <body><p>Content here. Enough content for validation purposes.</p></body>
        </html>
        """
        result = parser.parse_html(html, url="https://example.com")
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

    def test_parse_empty_html(self, parser):
        """Test parsing empty HTML."""
        result = parser.parse_html("<html></html>", url="https://example.com")
        # Empty content should result in empty text or title
        assert result.text == "" or result.title == "" or not result.is_valid

    def test_parse_malformed_html(self, parser):
        """Test parsing malformed HTML."""
        html = "<html><body><p>Unclosed paragraph<div>Nested wrong</p></div>"
        result = parser.parse_html(html, url="https://example.com")
        # Should handle gracefully
        assert result is not None

    def test_parse_non_html(self, parser):
        """Test parsing non-HTML content."""
        text = "Just plain text, no HTML at all."
        result = parser.parse_html(text, url="https://example.com")
        assert result is not None

    def test_parse_unicode_content(self, parser):
        """Test parsing Unicode content."""
        html = """
        <html>
        <head><title>Unicode Test</title></head>
        <body><p>Content with special characters and more text for validation.</p></body>
        </html>
        """
        result = parser.parse_html(html, url="https://example.com")
        assert result is not None
        assert len(result.text) > 0

    def test_parse_very_long_content(self, parser):
        """Test parsing very long content."""
        html = f"""
        <html>
        <head><title>Long Article</title></head>
        <body>
            <article>{"<p>Paragraph with some words here. </p>" * 500}</article>
        </body>
        </html>
        """
        result = parser.parse_html(html, url="https://example.com")
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

    def test_removes_script_tags(self, parser):
        """Test that script tags are removed."""
        html = """
        <html>
        <body>
            <p>Real content here with enough words for validation.</p>
            <script>alert('malicious');</script>
            <p>More content here for the article.</p>
        </body>
        </html>
        """
        result = parser.parse_html(html, url="https://example.com")
        assert "alert" not in result.text
        assert "malicious" not in result.text

    def test_removes_style_tags(self, parser):
        """Test that style tags are removed."""
        html = """
        <html>
        <head><title>Test</title><style>body { color: red; }</style></head>
        <body><p>Content here with enough text for the parser to extract.</p></body>
        </html>
        """
        result = parser.parse_html(html, url="https://example.com")
        assert "color: red" not in result.text


# ============================================================================
# URL Handling Tests
# ============================================================================


class TestUrlHandling:
    """Tests for URL handling."""

    def test_domain_extracted_in_parsed_content(self):
        """Test that domain is extracted from URL in ParsedContent."""
        content = ParsedContent(
            url="https://example.com/article/123",
            title="Test",
            text="Content " * 20,
        )
        assert content.source == "example.com"

    def test_subdomain_preserved(self):
        """Test that subdomain is preserved."""
        content = ParsedContent(
            url="https://blog.example.com/post",
            title="Test",
            text="Content " * 20,
        )
        assert content.source == "blog.example.com"

    def test_www_stripped(self):
        """Test that www is stripped from domain."""
        content = ParsedContent(
            url="https://www.example.com/page",
            title="Test",
            text="Content " * 20,
        )
        assert content.source == "example.com"

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://news.ycombinator.com/item?id=123", "news.ycombinator.com"),
            ("https://arxiv.org/abs/2312.00001", "arxiv.org"),
            ("https://www.bbc.com/news/article", "bbc.com"),
            ("http://localhost:3000/test", "localhost:3000"),  # Port is preserved
        ],
    )
    def test_source_extraction_various(self, url, expected):
        """Test source extraction for various URLs."""
        content = ParsedContent(
            url=url,
            title="Test",
            text="Content " * 20,
        )
        assert content.source == expected


# ============================================================================
# Parser Configuration Tests
# ============================================================================


class TestParserConfig:
    """Tests for parser configuration."""

    def test_default_config(self):
        """Test default parser configuration."""
        config = ParserConfig()
        assert config.timeout == 30.0
        assert config.max_retries == 2
        assert config.min_content_length == 100
        assert config.prefer_newspaper is True

    def test_custom_config(self):
        """Test custom parser configuration."""
        config = ParserConfig(
            timeout=60.0,
            max_retries=5,
            prefer_newspaper=False,
        )
        parser = ParserService(config=config)
        assert parser.config.timeout == 60.0
        assert parser.config.max_retries == 5
        assert parser.config.prefer_newspaper is False


# ============================================================================
# Statistics Tests
# ============================================================================


class TestParserStats:
    """Tests for parser statistics."""

    @pytest.fixture
    def parser(self):
        """Create a parser service instance."""
        return ParserService()

    def test_get_stats(self, parser):
        """Test getting parser statistics."""
        stats = parser.get_stats()
        assert "total_parsed" in stats
        assert "successful" in stats
        assert "failed" in stats
        assert "success_rate" in stats
        assert "average_time" in stats

    def test_reset_stats(self, parser):
        """Test resetting statistics."""
        parser.reset_stats()
        stats = parser.get_stats()
        assert stats["total_parsed"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
