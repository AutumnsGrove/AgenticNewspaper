"""Data models for articles and news content."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import hashlib


class ArticleFormat(Enum):
    """Article content format types."""
    HTML = "html"
    PDF = "pdf"
    PLAINTEXT = "plaintext"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


class ProcessingStatus(Enum):
    """Article processing status."""
    PENDING = "pending"
    FETCHING = "fetching"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ArticleURL:
    """
    Article URL with metadata from search results.

    Represents a discovered article before fetching/parsing.
    """
    url: str
    title: str
    source: str
    snippet: str
    published_date: Optional[datetime] = None
    initial_relevance_score: float = 0.0
    topic: Optional[str] = None
    search_rank: int = 0
    discovered_at: datetime = field(default_factory=datetime.now)

    @property
    def url_hash(self) -> str:
        """Generate a unique hash for this URL."""
        return hashlib.md5(self.url.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "source": self.source,
            "snippet": self.snippet,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "initial_relevance_score": self.initial_relevance_score,
            "topic": self.topic,
            "search_rank": self.search_rank,
            "discovered_at": self.discovered_at.isoformat(),
            "url_hash": self.url_hash
        }


@dataclass
class ParsedArticle:
    """
    Parsed article with full content and metadata.

    Represents an article after successful fetch and parse.
    """
    article_id: str
    url: str
    title: str
    content: str
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    source: str = ""
    word_count: int = 0
    reading_time_minutes: int = 0
    format: ArticleFormat = ArticleFormat.HTML
    extracted_at: datetime = field(default_factory=datetime.now)

    # Metadata
    meta_description: Optional[str] = None
    meta_keywords: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)

    # Processing info
    parse_quality: float = 0.0  # 0-1 score of parse quality

    def __post_init__(self):
        """Calculate derived fields after initialization."""
        if self.word_count == 0 and self.content:
            self.word_count = len(self.content.split())

        if self.reading_time_minutes == 0 and self.word_count > 0:
            # Average reading speed: 200 words per minute
            self.reading_time_minutes = max(1, self.word_count // 200)

    @property
    def content_preview(self) -> str:
        """Get first 200 characters of content."""
        if not self.content:
            return ""
        return self.content[:200] + ("..." if len(self.content) > 200 else "")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "article_id": self.article_id,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "source": self.source,
            "word_count": self.word_count,
            "reading_time_minutes": self.reading_time_minutes,
            "format": self.format.value,
            "extracted_at": self.extracted_at.isoformat(),
            "meta_description": self.meta_description,
            "meta_keywords": self.meta_keywords,
            "images": self.images,
            "parse_quality": self.parse_quality
        }


@dataclass
class AnalyzedArticle:
    """
    Article with analysis scores and insights.

    Represents an article after content analysis.
    """
    parsed_article: ParsedArticle

    # Scoring (0-1 scale)
    relevance_score: float = 0.0
    quality_score: float = 0.0
    bias_score: float = 0.0  # 0 = neutral, 1 = highly biased

    # Analysis results
    key_points: List[str] = field(default_factory=list)
    hn_style_summary: str = ""
    why_matters: str = ""
    technical_insights: List[str] = field(default_factory=list)

    # Verification
    claims_verified: int = 0
    claims_unverified: int = 0
    confidence_level: float = 0.0  # 0-1

    # Multi-perspective (Phase 3)
    alternative_perspectives: List[str] = field(default_factory=list)
    cross_references: List[str] = field(default_factory=list)

    analyzed_at: datetime = field(default_factory=datetime.now)

    @property
    def combined_score(self) -> float:
        """Get combined relevance + quality score."""
        return (self.relevance_score + self.quality_score) / 2

    @property
    def should_include(self) -> bool:
        """Check if article should be included in digest (Phase 1 simple logic)."""
        return self.relevance_score >= 0.5 and self.quality_score >= 0.5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "parsed_article": self.parsed_article.to_dict(),
            "relevance_score": self.relevance_score,
            "quality_score": self.quality_score,
            "bias_score": self.bias_score,
            "key_points": self.key_points,
            "hn_style_summary": self.hn_style_summary,
            "why_matters": self.why_matters,
            "technical_insights": self.technical_insights,
            "claims_verified": self.claims_verified,
            "claims_unverified": self.claims_unverified,
            "confidence_level": self.confidence_level,
            "alternative_perspectives": self.alternative_perspectives,
            "cross_references": self.cross_references,
            "analyzed_at": self.analyzed_at.isoformat(),
            "combined_score": self.combined_score,
            "should_include": self.should_include
        }


@dataclass
class DigestMetadata:
    """Metadata for a complete digest."""
    digest_id: str
    generated_at: datetime
    topics_covered: List[str]
    total_articles_found: int
    total_articles_parsed: int
    total_articles_included: int

    # Cost tracking
    total_tokens_used: int
    total_cost_usd: float

    # Model usage breakdown
    model_usage: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # Processing time
    processing_time_seconds: float = 0.0

    # User preferences snapshot
    preferences_version: str = "0.1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "digest_id": self.digest_id,
            "generated_at": self.generated_at.isoformat(),
            "topics_covered": self.topics_covered,
            "total_articles_found": self.total_articles_found,
            "total_articles_parsed": self.total_articles_parsed,
            "total_articles_included": self.total_articles_included,
            "total_tokens_used": self.total_tokens_used,
            "total_cost_usd": self.total_cost_usd,
            "model_usage": self.model_usage,
            "processing_time_seconds": self.processing_time_seconds,
            "preferences_version": self.preferences_version
        }
