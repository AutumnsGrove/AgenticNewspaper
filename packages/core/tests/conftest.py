"""
Pytest configuration and shared fixtures for The Daily Clearing tests.
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure we're using the test configuration
os.environ["TESTING"] = "1"
os.environ["OPENROUTER_API_KEY"] = "test-openrouter-key"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
os.environ["TAVILY_API_KEY"] = "test-tavily-key"


# ============================================================================
# Event Loop Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture
def temp_db_path(tmp_path: Path) -> str:
    """Create a temporary database path."""
    return str(tmp_path / "test.db")


@pytest.fixture
async def sqlite_db(temp_db_path: str):
    """Create a SQLite database instance for testing."""
    from src.database.sqlite import SQLiteDatabase

    db = SQLiteDatabase(temp_db_path)
    await db.initialize()
    yield db
    await db.close()


# ============================================================================
# Provider Fixtures
# ============================================================================


@pytest.fixture
def mock_openrouter_response():
    """Create a mock OpenRouter API response."""
    return {
        "id": "gen-test-123",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a test response from the mock LLM.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        },
        "model": "deepseek/deepseek-chat",
    }


@pytest.fixture
def mock_anthropic_response():
    """Create a mock Anthropic API response."""
    return {
        "id": "msg-test-123",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "This is a test response from Anthropic."}],
        "model": "claude-3-haiku-20240307",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
        },
    }


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = AsyncMock()
    return client


# ============================================================================
# Article Fixtures
# ============================================================================


@pytest.fixture
def sample_article_data():
    """Create sample article data for testing."""
    return {
        "id": "article-001",
        "url": "https://example.com/article-1",
        "title": "Test Article: AI Advances in 2025",
        "source": "example.com",
        "author": "John Doe",
        "published_date": "2025-12-24",
        "word_count": 1500,
        "reading_time_minutes": 7,
        "content": """
        Artificial intelligence continues to advance at a rapid pace in 2025.
        New developments in large language models have led to significant
        improvements in reasoning and coding capabilities. Researchers at
        leading labs have announced breakthroughs in efficient training
        methods that reduce costs by up to 90%.

        The implications for various industries are profound. Healthcare,
        finance, and education sectors are seeing rapid adoption of AI
        technologies. However, concerns about job displacement and ethical
        considerations remain topics of ongoing debate.

        Key developments this year include:
        - Improved reasoning capabilities in frontier models
        - More efficient training methodologies
        - Enhanced safety and alignment techniques
        - Broader adoption across industries

        Experts predict continued rapid progress in the coming years.
        """,
    }


@pytest.fixture
def sample_articles():
    """Create multiple sample articles for testing."""
    return [
        {
            "id": f"article-{i:03d}",
            "url": f"https://example{i}.com/article",
            "title": f"Test Article {i}",
            "source": f"example{i}.com",
            "author": f"Author {i}",
            "published_date": "2025-12-24",
            "word_count": 1000 + i * 100,
            "content": f"Content for article {i}. " * 50,
        }
        for i in range(1, 11)
    ]


@pytest.fixture
def sample_parsed_article(sample_article_data):
    """Create a sample parsed article."""
    from src.models.article import ParsedArticle

    return ParsedArticle(
        url=sample_article_data["url"],
        title=sample_article_data["title"],
        content=sample_article_data["content"],
        author=sample_article_data["author"],
        published_date=sample_article_data["published_date"],
        source=sample_article_data["source"],
        word_count=sample_article_data["word_count"],
    )


# ============================================================================
# User Preference Fixtures
# ============================================================================


@pytest.fixture
def sample_user_preferences():
    """Create sample user preferences."""
    return {
        "user_id": "user-001",
        "topics": [
            {
                "name": "AI & Machine Learning",
                "keywords": ["artificial intelligence", "machine learning", "LLM"],
                "priority": 5,
            },
            {
                "name": "Science",
                "keywords": ["research", "discovery", "study"],
                "priority": 4,
            },
        ],
        "delivery": {
            "frequency": "daily",
            "time": "06:00",
            "timezone": "UTC",
        },
        "style": {
            "tone": "hn-style",
            "skepticism_level": 3,
            "technical_depth": 4,
        },
        "thresholds": {
            "min_relevance": 0.6,
            "min_quality": 0.5,
            "max_bias": 0.8,
        },
    }


# ============================================================================
# Search Fixtures
# ============================================================================


@pytest.fixture
def mock_tavily_response():
    """Create a mock Tavily search response."""
    return {
        "results": [
            {
                "title": "AI Breakthrough Article",
                "url": "https://news.example.com/ai-breakthrough",
                "content": "Summary of the AI breakthrough article...",
                "score": 0.95,
                "published_date": "2025-12-24",
            },
            {
                "title": "Machine Learning Update",
                "url": "https://tech.example.com/ml-update",
                "content": "Summary of the ML update...",
                "score": 0.88,
                "published_date": "2025-12-23",
            },
            {
                "title": "New Research Paper",
                "url": "https://arxiv.example.com/paper-123",
                "content": "Summary of the research paper...",
                "score": 0.82,
                "published_date": "2025-12-22",
            },
        ],
        "query": "artificial intelligence news",
    }


# ============================================================================
# HTML Content Fixtures
# ============================================================================


@pytest.fixture
def sample_html_content():
    """Create sample HTML content for parser testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Article: AI Advances</title>
        <meta name="author" content="John Doe">
        <meta name="date" content="2025-12-24">
    </head>
    <body>
        <article>
            <h1>AI Advances in 2025</h1>
            <p class="author">By John Doe</p>
            <p class="date">December 24, 2025</p>
            <div class="content">
                <p>Artificial intelligence continues to advance at a rapid pace.</p>
                <p>New developments have led to significant improvements.</p>
                <p>The implications for various industries are profound.</p>
            </div>
        </article>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_with_ads():
    """Create sample HTML with ads and noise."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Article with Ads</title></head>
    <body>
        <div class="ad-banner">Advertisement Here</div>
        <nav>Navigation Menu</nav>
        <article>
            <h1>Main Article Title</h1>
            <p>This is the actual article content that should be extracted.</p>
            <p>More important content here.</p>
        </article>
        <aside class="sidebar">Related Articles</aside>
        <div class="ad-footer">More Ads</div>
        <footer>Copyright Notice</footer>
    </body>
    </html>
    """


# ============================================================================
# Digest Fixtures
# ============================================================================


@pytest.fixture
def sample_digest():
    """Create a sample digest for testing."""
    return {
        "digest_id": "2025-12-25",
        "user_id": "user-001",
        "generated_at": datetime.now().isoformat(),
        "sections": [
            {
                "topic": "AI & Machine Learning",
                "section_summary": "Major AI developments this week.",
                "articles": [
                    {
                        "id": "article-001",
                        "title": "AI Breakthrough",
                        "url": "https://example.com/ai",
                        "summary": "Summary of AI article.",
                        "relevance_score": 0.92,
                        "quality_score": 0.88,
                    }
                ],
                "cross_story_insights": ["Pattern detected across articles."],
            }
        ],
        "metadata": {
            "total_articles_found": 100,
            "total_articles_included": 5,
            "total_cost_usd": 0.035,
            "processing_time_seconds": 45.2,
        },
    }


# ============================================================================
# Quality Analysis Fixtures
# ============================================================================


@pytest.fixture
def sample_quality_analysis():
    """Create sample quality analysis data."""
    return {
        "relevance_score": 0.85,
        "quality_score": 0.78,
        "novelty_score": 0.72,
        "depth_score": 0.80,
        "credibility_score": 0.90,
        "key_points": [
            "First key point from the article",
            "Second key point with important details",
            "Third key point about implications",
        ],
        "why_matters": "This development could reshape the industry.",
        "technical_insights": ["Uses novel architecture", "Achieves SOTA results"],
        "content_type": "research",
        "skip_reason": None,
    }


@pytest.fixture
def sample_bias_analysis():
    """Create sample bias analysis data."""
    return {
        "bias_score": 0.35,
        "bias_direction": "center-left",
        "loaded_language": ["breakthrough", "revolutionary"],
        "missing_perspectives": ["Industry critics", "Regulatory concerns"],
        "factual_claims": [
            {"claim": "90% cost reduction", "verifiable": True},
            {"claim": "Best in class", "verifiable": False},
        ],
        "skeptics_corner": "Claims of 90% cost reduction should be verified.",
        "red_flags": [],
        "confidence": 0.75,
    }


# ============================================================================
# Utility Functions
# ============================================================================


def create_temp_secrets_file(tmp_path: Path) -> Path:
    """Create a temporary secrets file for testing."""
    secrets = {
        "openrouter_api_key": "test-openrouter-key",
        "anthropic_api_key": "test-anthropic-key",
        "tavily_api_key": "test-tavily-key",
    }
    secrets_path = tmp_path / "secrets.json"
    secrets_path.write_text(json.dumps(secrets))
    return secrets_path


@pytest.fixture
def temp_secrets_file(tmp_path: Path) -> Path:
    """Fixture for temporary secrets file."""
    return create_temp_secrets_file(tmp_path)
