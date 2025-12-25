"""Data models for articles and news content."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
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


class BiasDirection(Enum):
    """Detected bias direction."""

    LEFT = "left"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    RIGHT = "right"
    UNKNOWN = "unknown"


class ContentType(Enum):
    """Type of article content."""

    NEWS = "news"
    OPINION = "opinion"
    ANALYSIS = "analysis"
    RESEARCH = "research"
    PRESS_RELEASE = "press_release"
    BLOG = "blog"
    SOCIAL = "social"
    UNKNOWN = "unknown"


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
    published_date: datetime | None = None
    initial_relevance_score: float = 0.0
    topic: str | None = None
    search_rank: int = 0
    discovered_at: datetime = field(default_factory=datetime.now)

    @property
    def url_hash(self) -> str:
        """Generate a unique hash for this URL."""
        return hashlib.md5(self.url.encode()).hexdigest()[:12]

    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse

        try:
            parsed = urlparse(self.url)
            return parsed.netloc.replace("www.", "")
        except Exception:
            return self.source

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "source": self.source,
            "domain": self.domain,
            "snippet": self.snippet,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "initial_relevance_score": self.initial_relevance_score,
            "topic": self.topic,
            "search_rank": self.search_rank,
            "discovered_at": self.discovered_at.isoformat(),
            "url_hash": self.url_hash,
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
    author: str | None = None
    authors: list[str] = field(default_factory=list)
    published_date: datetime | None = None
    source: str = ""
    word_count: int = 0
    reading_time_minutes: int = 0
    format: ArticleFormat = ArticleFormat.HTML
    extracted_at: datetime = field(default_factory=datetime.now)

    # Metadata
    meta_description: str | None = None
    meta_keywords: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    top_image: str = ""
    language: str = "en"

    # Topic assignment
    topic: str | None = None

    # Processing info
    parse_quality: float = 0.0  # 0-1 score of parse quality
    extraction_method: str = ""

    def __post_init__(self):
        """Calculate derived fields after initialization."""
        if self.word_count == 0 and self.content:
            self.word_count = len(self.content.split())

        if self.reading_time_minutes == 0 and self.word_count > 0:
            # Average reading speed: 225 words per minute
            self.reading_time_minutes = max(1, self.word_count // 225)

        if not self.authors and self.author:
            self.authors = [self.author]

    @property
    def content_preview(self) -> str:
        """Get first 200 characters of content."""
        if not self.content:
            return ""
        return self.content[:200] + ("..." if len(self.content) > 200 else "")

    @property
    def content_hash(self) -> str:
        """Generate hash of content for deduplication."""
        return hashlib.md5(self.content.encode()).hexdigest()[:12]

    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse

        try:
            parsed = urlparse(self.url)
            return parsed.netloc.replace("www.", "")
        except Exception:
            return self.source

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "article_id": self.article_id,
            "url": self.url,
            "title": self.title,
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "author": self.author,
            "authors": self.authors,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "source": self.source,
            "domain": self.domain,
            "word_count": self.word_count,
            "reading_time_minutes": self.reading_time_minutes,
            "format": self.format.value,
            "extracted_at": self.extracted_at.isoformat(),
            "meta_description": self.meta_description,
            "meta_keywords": self.meta_keywords,
            "images": self.images[:3],
            "top_image": self.top_image,
            "language": self.language,
            "topic": self.topic,
            "parse_quality": self.parse_quality,
            "content_hash": self.content_hash,
        }


@dataclass
class QualityAnalysis:
    """Quality analysis results for an article."""

    # Scores (0-1)
    relevance_score: float = 0.0
    quality_score: float = 0.0
    novelty_score: float = 0.0
    depth_score: float = 0.0
    credibility_score: float = 0.0

    # Content analysis
    content_type: ContentType = ContentType.UNKNOWN
    key_points: list[str] = field(default_factory=list)
    technical_level: int = 1  # 1-5 (1=general audience, 5=expert)
    originality_indicators: list[str] = field(default_factory=list)

    # Why it matters
    why_matters: str = ""
    implications: list[str] = field(default_factory=list)

    # Skip reasons
    skip_reason: str | None = None
    should_include: bool = True

    @property
    def combined_score(self) -> float:
        """Weighted combined score."""
        weights = {
            "relevance": 0.3,
            "quality": 0.25,
            "novelty": 0.2,
            "depth": 0.15,
            "credibility": 0.1,
        }
        return (
            self.relevance_score * weights["relevance"]
            + self.quality_score * weights["quality"]
            + self.novelty_score * weights["novelty"]
            + self.depth_score * weights["depth"]
            + self.credibility_score * weights["credibility"]
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "relevance_score": self.relevance_score,
            "quality_score": self.quality_score,
            "novelty_score": self.novelty_score,
            "depth_score": self.depth_score,
            "credibility_score": self.credibility_score,
            "combined_score": self.combined_score,
            "content_type": self.content_type.value,
            "key_points": self.key_points,
            "technical_level": self.technical_level,
            "why_matters": self.why_matters,
            "implications": self.implications,
            "skip_reason": self.skip_reason,
            "should_include": self.should_include,
        }


@dataclass
class BiasAnalysis:
    """Bias analysis results for an article."""

    # Bias metrics (0-1, where 0.5 is neutral)
    bias_score: float = 0.5
    bias_direction: BiasDirection = BiasDirection.UNKNOWN
    bias_confidence: float = 0.0

    # Specific bias indicators
    loaded_language: list[str] = field(default_factory=list)
    framing_issues: list[str] = field(default_factory=list)
    missing_context: list[str] = field(default_factory=list)
    one_sided_sources: bool = False

    # Alternative perspectives
    missing_perspectives: list[str] = field(default_factory=list)
    suggested_counterpoints: list[str] = field(default_factory=list)

    # Fact checking
    verifiable_claims: list[str] = field(default_factory=list)
    unverified_claims: list[str] = field(default_factory=list)
    potentially_misleading: list[str] = field(default_factory=list)

    # Skeptic's notes
    skeptics_corner: str = ""
    red_flags: list[str] = field(default_factory=list)

    @property
    def is_highly_biased(self) -> bool:
        """Check if article is highly biased."""
        return abs(self.bias_score - 0.5) > 0.3

    @property
    def bias_label(self) -> str:
        """Get human-readable bias label."""
        if self.bias_confidence < 0.3:
            return "Unknown"
        score = self.bias_score
        if score < 0.2:
            return "Strong Left"
        elif score < 0.4:
            return "Left-Leaning"
        elif score < 0.6:
            return "Neutral/Balanced"
        elif score < 0.8:
            return "Right-Leaning"
        else:
            return "Strong Right"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "bias_score": self.bias_score,
            "bias_direction": self.bias_direction.value,
            "bias_confidence": self.bias_confidence,
            "bias_label": self.bias_label,
            "is_highly_biased": self.is_highly_biased,
            "loaded_language": self.loaded_language,
            "framing_issues": self.framing_issues,
            "missing_context": self.missing_context,
            "one_sided_sources": self.one_sided_sources,
            "missing_perspectives": self.missing_perspectives,
            "suggested_counterpoints": self.suggested_counterpoints,
            "verifiable_claims": self.verifiable_claims,
            "unverified_claims": self.unverified_claims,
            "potentially_misleading": self.potentially_misleading,
            "skeptics_corner": self.skeptics_corner,
            "red_flags": self.red_flags,
        }


@dataclass
class CrossConnection:
    """Connection between articles for cross-story analysis."""

    related_article_id: str
    connection_type: str  # "supports", "contradicts", "extends", "provides_context"
    connection_strength: float  # 0-1
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "related_article_id": self.related_article_id,
            "connection_type": self.connection_type,
            "connection_strength": self.connection_strength,
            "summary": self.summary,
        }


@dataclass
class AnalyzedArticle:
    """
    Article with complete analysis results.

    Represents an article after quality and bias analysis.
    """

    parsed_article: ParsedArticle
    quality_analysis: QualityAnalysis = field(default_factory=QualityAnalysis)
    bias_analysis: BiasAnalysis = field(default_factory=BiasAnalysis)

    # HN-style content
    hn_style_summary: str = ""
    technical_insights: list[str] = field(default_factory=list)

    # Cross-story connections
    connections: list[CrossConnection] = field(default_factory=list)

    # Processing metadata
    analyzed_at: datetime = field(default_factory=datetime.now)
    analysis_cost_usd: float = 0.0
    analysis_tokens: int = 0

    @property
    def combined_score(self) -> float:
        """Get overall article score."""
        quality_weight = 0.7
        bias_penalty = 0.3

        quality = self.quality_analysis.combined_score
        bias_penalty_value = abs(self.bias_analysis.bias_score - 0.5) * 2  # 0-1

        return quality * quality_weight - bias_penalty_value * bias_penalty

    @property
    def should_include(self) -> bool:
        """Check if article should be included in digest."""
        return (
            self.quality_analysis.should_include
            and self.combined_score >= 0.4
            and not self.bias_analysis.is_highly_biased
        )

    # Legacy compatibility
    @property
    def relevance_score(self) -> float:
        """Legacy: get relevance score."""
        return self.quality_analysis.relevance_score

    @property
    def quality_score(self) -> float:
        """Legacy: get quality score."""
        return self.quality_analysis.quality_score

    @property
    def bias_score(self) -> float:
        """Legacy: get bias score."""
        return self.bias_analysis.bias_score

    @property
    def key_points(self) -> list[str]:
        """Legacy: get key points."""
        return self.quality_analysis.key_points

    @property
    def why_matters(self) -> str:
        """Legacy: get why it matters."""
        return self.quality_analysis.why_matters

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "parsed_article": self.parsed_article.to_dict(),
            "quality_analysis": self.quality_analysis.to_dict(),
            "bias_analysis": self.bias_analysis.to_dict(),
            "hn_style_summary": self.hn_style_summary,
            "technical_insights": self.technical_insights,
            "connections": [c.to_dict() for c in self.connections],
            "combined_score": self.combined_score,
            "should_include": self.should_include,
            "analyzed_at": self.analyzed_at.isoformat(),
            "analysis_cost_usd": self.analysis_cost_usd,
            "analysis_tokens": self.analysis_tokens,
        }


@dataclass
class DigestSection:
    """A section of the digest covering one topic."""

    topic: str
    articles: list[AnalyzedArticle] = field(default_factory=list)
    section_summary: str = ""
    cross_story_insights: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "topic": self.topic,
            "article_count": len(self.articles),
            "section_summary": self.section_summary,
            "cross_story_insights": self.cross_story_insights,
        }


@dataclass
class DigestMetadata:
    """Metadata for a complete digest."""

    digest_id: str
    generated_at: datetime
    topics_covered: list[str]
    total_articles_found: int
    total_articles_parsed: int
    total_articles_analyzed: int
    total_articles_included: int

    # Cost tracking
    total_tokens_used: int
    total_cost_usd: float

    # Model usage breakdown
    model_usage: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Processing time
    processing_time_seconds: float = 0.0
    search_time_seconds: float = 0.0
    parse_time_seconds: float = 0.0
    analysis_time_seconds: float = 0.0
    synthesis_time_seconds: float = 0.0

    # Quality metrics
    average_quality_score: float = 0.0
    average_relevance_score: float = 0.0
    articles_filtered_by_quality: int = 0
    articles_filtered_by_bias: int = 0

    # User preferences snapshot
    preferences_version: str = "1.0.0"
    user_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "digest_id": self.digest_id,
            "generated_at": self.generated_at.isoformat(),
            "topics_covered": self.topics_covered,
            "total_articles_found": self.total_articles_found,
            "total_articles_parsed": self.total_articles_parsed,
            "total_articles_analyzed": self.total_articles_analyzed,
            "total_articles_included": self.total_articles_included,
            "total_tokens_used": self.total_tokens_used,
            "total_cost_usd": self.total_cost_usd,
            "model_usage": self.model_usage,
            "processing_time_seconds": self.processing_time_seconds,
            "search_time_seconds": self.search_time_seconds,
            "parse_time_seconds": self.parse_time_seconds,
            "analysis_time_seconds": self.analysis_time_seconds,
            "synthesis_time_seconds": self.synthesis_time_seconds,
            "average_quality_score": self.average_quality_score,
            "average_relevance_score": self.average_relevance_score,
            "articles_filtered_by_quality": self.articles_filtered_by_quality,
            "articles_filtered_by_bias": self.articles_filtered_by_bias,
            "preferences_version": self.preferences_version,
            "user_id": self.user_id,
        }


@dataclass
class Digest:
    """Complete digest with all sections and metadata."""

    metadata: DigestMetadata
    sections: list[DigestSection] = field(default_factory=list)
    cross_story_connections: str = ""
    skeptics_summary: str = ""
    markdown: str = ""

    @property
    def article_count(self) -> int:
        """Total number of articles in digest."""
        return sum(len(section.articles) for section in self.sections)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metadata": self.metadata.to_dict(),
            "sections": [s.to_dict() for s in self.sections],
            "article_count": self.article_count,
            "cross_story_connections": self.cross_story_connections,
            "skeptics_summary": self.skeptics_summary,
            "markdown_preview": self.markdown[:1000] + "..." if len(self.markdown) > 1000 else self.markdown,
        }
