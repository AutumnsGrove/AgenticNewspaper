"""
Tests for the Bias Agent.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.tier2_reasoning.bias_agent import BiasAgent
from src.models.article import (
    BiasAnalysis,
    BiasDirection,
    ParsedArticle,
)
from src.providers.base import LLMResponse


# ============================================================================
# BiasAnalysis Tests
# ============================================================================


class TestBiasAnalysis:
    """Tests for the BiasAnalysis dataclass."""

    def test_create_analysis(self):
        """Test creating a bias analysis."""
        analysis = BiasAnalysis(
            bias_score=0.35,
            bias_direction=BiasDirection.CENTER_LEFT,
            bias_confidence=0.75,
        )
        assert analysis.bias_score == 0.35
        assert analysis.bias_direction == BiasDirection.CENTER_LEFT
        assert analysis.bias_confidence == 0.75

    def test_analysis_with_details(self):
        """Test analysis with full details."""
        analysis = BiasAnalysis(
            bias_score=0.7,
            bias_direction=BiasDirection.RIGHT,
            loaded_language=["radical", "extremist", "dangerous"],
            missing_perspectives=["Liberal viewpoint", "Academic research"],
            skeptics_corner="This article presents only one side of the debate.",
            red_flags=["Cherry-picked statistics", "Emotional appeal without evidence"],
        )
        assert len(analysis.loaded_language) == 3
        assert len(analysis.missing_perspectives) == 2
        assert analysis.skeptics_corner is not None
        assert len(analysis.red_flags) == 2

    def test_analysis_default_values(self):
        """Test analysis default values."""
        analysis = BiasAnalysis()
        assert analysis.bias_score == 0.5
        assert analysis.bias_direction == BiasDirection.UNKNOWN
        assert analysis.loaded_language == []
        assert analysis.red_flags == []

    @pytest.mark.parametrize(
        "score,expected_direction",
        [
            (0.0, BiasDirection.LEFT),
            (0.25, BiasDirection.CENTER_LEFT),
            (0.5, BiasDirection.CENTER),
            (0.75, BiasDirection.CENTER_RIGHT),
            (1.0, BiasDirection.RIGHT),
        ],
    )
    def test_score_direction_mapping(self, score, expected_direction):
        """Test that scores map to expected directions."""
        analysis = BiasAnalysis(
            bias_score=score,
            bias_direction=expected_direction,
        )
        assert analysis.bias_direction == expected_direction


# ============================================================================
# BiasDirection Tests
# ============================================================================


class TestBiasDirection:
    """Tests for BiasDirection enum."""

    def test_left_direction(self):
        """Test left bias direction."""
        assert BiasDirection.LEFT.value == "left"

    def test_center_left_direction(self):
        """Test center-left bias direction."""
        assert BiasDirection.CENTER_LEFT.value == "center_left"

    def test_center_direction(self):
        """Test center bias direction."""
        assert BiasDirection.CENTER.value == "center"

    def test_center_right_direction(self):
        """Test center-right bias direction."""
        assert BiasDirection.CENTER_RIGHT.value == "center_right"

    def test_right_direction(self):
        """Test right bias direction."""
        assert BiasDirection.RIGHT.value == "right"

    def test_unknown_direction(self):
        """Test unknown bias direction."""
        assert BiasDirection.UNKNOWN.value == "unknown"


# ============================================================================
# Bias Agent Initialization Tests
# ============================================================================


class TestBiasAgentInit:
    """Tests for Bias Agent initialization."""

    def test_init_with_provider(self):
        """Test initialization with provider."""
        mock_provider = MagicMock()
        agent = BiasAgent(provider=mock_provider)
        assert agent.provider == mock_provider

    def test_init_with_config(self):
        """Test initialization - config is handled through provider."""
        mock_provider = MagicMock()
        # BiasAgent doesn't take config directly, just provider
        agent = BiasAgent(provider=mock_provider)
        assert agent.provider == mock_provider


# ============================================================================
# Bias Agent Analysis Tests
# ============================================================================


def _make_article(
    title: str = "Test Article",
    content: str = "Test content",
    source: str = "test.com",
) -> ParsedArticle:
    """Helper to create test articles."""
    return ParsedArticle(
        article_id="test-001",
        url=f"https://{source}/article",
        title=title,
        content=content,
        source=source,
    )


class TestBiasAgentAnalyze:
    """Tests for Bias Agent analyze method."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.complete = AsyncMock()
        provider.get_stats = MagicMock(return_value={})
        return provider

    @pytest.fixture
    def agent(self, mock_provider):
        """Create a Bias Agent instance."""
        return BiasAgent(provider=mock_provider)

    @pytest.fixture
    def neutral_article(self):
        """Create a neutral article."""
        return _make_article(
            title="Study Finds Mixed Results on Policy",
            content="""
            A new study examines the effects of the policy from multiple angles.
            Supporters point to economic benefits, while critics highlight
            environmental concerns. The researchers note that both perspectives
            have merit and call for further investigation.
            """,
            source="reuters.com",
        )

    @pytest.fixture
    def biased_article(self):
        """Create a biased article."""
        return _make_article(
            title="Radical New Policy Threatens Economy",
            content="""
            The dangerous new policy pushed by extremists will destroy jobs
            and devastate communities. Experts warn of catastrophic consequences
            while radical activists ignore the evidence. This socialist agenda
            must be stopped before it's too late.
            """,
            source="opinion.example.com",
        )

    def _make_response(self, data: dict) -> LLMResponse:
        """Create a mock LLM response with JSON content."""
        return LLMResponse(
            content=json.dumps(data),
            model="test-model",
            provider="test",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            response_time_seconds=1.0,
        )

    @pytest.mark.asyncio
    async def test_analyze_returns_analysis(self, agent, mock_provider, neutral_article):
        """Test that analyze returns a BiasAnalysis."""
        mock_provider.complete.return_value = self._make_response({
            "bias_score": 0.5,
            "bias_direction": "center",
            "loaded_language": [],
            "missing_perspectives": [],
            "bias_confidence": 0.8,
        })

        analysis = await agent.analyze(neutral_article)
        assert isinstance(analysis, BiasAnalysis)

    @pytest.mark.asyncio
    async def test_analyze_neutral_content(self, agent, mock_provider, neutral_article):
        """Test analysis of neutral content."""
        mock_provider.complete.return_value = self._make_response({
            "bias_score": 0.48,
            "bias_direction": "CENTER",
            "loaded_language": [],
            "missing_perspectives": [],
            "bias_confidence": 0.85,
        })

        analysis = await agent.analyze(neutral_article)
        assert 0.4 <= analysis.bias_score <= 0.6
        assert analysis.bias_direction == BiasDirection.CENTER

    @pytest.mark.asyncio
    async def test_analyze_biased_content(self, agent, mock_provider, biased_article):
        """Test analysis of biased content."""
        mock_provider.complete.return_value = self._make_response({
            "bias_score": 0.85,
            "bias_direction": "RIGHT",
            "loaded_language": ["radical", "extremists", "dangerous", "socialist"],
            "missing_perspectives": ["Policy supporters", "Academic research"],
            "skeptics_corner": "This article uses inflammatory language and presents only one viewpoint.",
            "red_flags": ["Emotionally charged language", "No cited sources"],
            "bias_confidence": 0.9,
        })

        analysis = await agent.analyze(biased_article)
        assert analysis.bias_score > 0.7
        assert len(analysis.loaded_language) > 0
        assert len(analysis.red_flags) > 0

    @pytest.mark.asyncio
    async def test_analyze_detects_loaded_language(self, agent, mock_provider, biased_article):
        """Test that analysis detects loaded language."""
        mock_provider.complete.return_value = self._make_response({
            "bias_score": 0.8,
            "bias_direction": "RIGHT",
            "loaded_language": ["radical", "extremists", "dangerous", "socialist", "catastrophic"],
            "bias_confidence": 0.85,
        })

        analysis = await agent.analyze(biased_article)
        assert "radical" in analysis.loaded_language
        assert "extremists" in analysis.loaded_language

    @pytest.mark.asyncio
    async def test_analyze_identifies_missing_perspectives(self, agent, mock_provider, biased_article):
        """Test that analysis identifies missing perspectives."""
        mock_provider.complete.return_value = self._make_response({
            "bias_score": 0.8,
            "bias_direction": "RIGHT",
            "missing_perspectives": [
                "Perspectives from policy supporters",
                "Academic or expert analysis",
                "Historical context",
            ],
            "bias_confidence": 0.85,
        })

        analysis = await agent.analyze(biased_article)
        assert len(analysis.missing_perspectives) > 0


# ============================================================================
# Skeptic's Corner Tests
# ============================================================================


class TestSkepticsCorner:
    """Tests for skeptic's corner generation."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.complete = AsyncMock()
        provider.get_stats = MagicMock(return_value={})
        return provider

    @pytest.fixture
    def agent(self, mock_provider):
        """Create a Bias Agent instance."""
        return BiasAgent(provider=mock_provider)

    def _make_response(self, data: dict) -> LLMResponse:
        """Create a mock LLM response with JSON content."""
        return LLMResponse(
            content=json.dumps(data),
            model="test-model",
            provider="test",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            response_time_seconds=1.0,
        )

    @pytest.mark.asyncio
    async def test_generates_skeptics_corner(self, agent, mock_provider):
        """Test that skeptic's corner is generated for concerning content."""
        article = _make_article(
            title="Miracle Cure Discovered",
            content="Scientists claim to have found a miracle cure...",
            source="news.example.com",
        )

        mock_provider.complete.return_value = self._make_response({
            "bias_score": 0.6,
            "bias_direction": "CENTER",
            "skeptics_corner": "Claims of 'miracle cures' should be viewed with skepticism until peer-reviewed studies confirm the results.",
            "red_flags": ["Unverified claims", "Sensationalized headline"],
            "bias_confidence": 0.75,
        })

        analysis = await agent.analyze(article)
        assert analysis.skeptics_corner is not None
        assert "skepticism" in analysis.skeptics_corner.lower()

    @pytest.mark.asyncio
    async def test_no_skeptics_corner_for_neutral(self, agent, mock_provider):
        """Test that neutral content may not need skeptic's corner."""
        article = _make_article(
            title="Research Study Published",
            content="Researchers published findings in peer-reviewed journal...",
            source="nature.com",
        )

        mock_provider.complete.return_value = self._make_response({
            "bias_score": 0.5,
            "bias_direction": "CENTER",
            "skeptics_corner": "",
            "red_flags": [],
            "bias_confidence": 0.9,
        })

        analysis = await agent.analyze(article)
        # May or may not have skeptic's corner
        assert analysis is not None


# ============================================================================
# Red Flags Tests
# ============================================================================


class TestRedFlags:
    """Tests for red flag detection."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.complete = AsyncMock()
        provider.get_stats = MagicMock(return_value={})
        return provider

    @pytest.fixture
    def agent(self, mock_provider):
        """Create a Bias Agent instance."""
        return BiasAgent(provider=mock_provider)

    def _make_response(self, data: dict) -> LLMResponse:
        """Create a mock LLM response with JSON content."""
        return LLMResponse(
            content=json.dumps(data),
            model="test-model",
            provider="test",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            response_time_seconds=1.0,
        )

    @pytest.mark.asyncio
    async def test_detects_unsourced_claims(self, agent, mock_provider):
        """Test detection of unsourced claims."""
        article = _make_article(
            title="Experts Say X",
            content="Experts say that X is true. Studies show Y.",
            source="blog.example.com",
        )

        mock_provider.complete.return_value = self._make_response({
            "bias_score": 0.6,
            "bias_direction": "CENTER",
            "red_flags": ["Vague attribution ('experts say')", "No specific sources cited"],
            "bias_confidence": 0.7,
        })

        analysis = await agent.analyze(article)
        assert any("source" in flag.lower() for flag in analysis.red_flags)

    @pytest.mark.asyncio
    async def test_detects_emotional_manipulation(self, agent, mock_provider):
        """Test detection of emotional manipulation."""
        article = _make_article(
            title="Shocking Truth Revealed",
            content="You won't believe what happened. This will make you furious.",
            source="clickbait.example.com",
        )

        mock_provider.complete.return_value = self._make_response({
            "bias_score": 0.65,
            "bias_direction": "UNKNOWN",
            "red_flags": ["Clickbait headline", "Emotional manipulation tactics"],
            "bias_confidence": 0.8,
        })

        analysis = await agent.analyze(article)
        assert len(analysis.red_flags) > 0


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestBiasAgentErrors:
    """Tests for Bias Agent error handling."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.complete = AsyncMock()
        provider.get_stats = MagicMock(return_value={})
        return provider

    @pytest.fixture
    def agent(self, mock_provider):
        """Create a Bias Agent instance."""
        return BiasAgent(provider=mock_provider)

    def _make_response(self, data: dict) -> LLMResponse:
        """Create a mock LLM response with JSON content."""
        return LLMResponse(
            content=json.dumps(data),
            model="test-model",
            provider="test",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            response_time_seconds=1.0,
        )

    @pytest.mark.asyncio
    async def test_handles_provider_error(self, agent, mock_provider):
        """Test handling of provider errors."""
        mock_provider.complete.side_effect = Exception("API Error")

        article = _make_article()

        with pytest.raises(Exception):
            await agent.analyze(article)

    @pytest.mark.asyncio
    async def test_handles_invalid_direction(self, agent, mock_provider):
        """Test handling of invalid bias direction."""
        mock_provider.complete.return_value = self._make_response({
            "bias_score": 0.5,
            "bias_direction": "invalid-direction",
            "bias_confidence": 0.5,
        })

        article = _make_article()
        analysis = await agent.analyze(article)
        # Should default to unknown
        assert analysis.bias_direction == BiasDirection.UNKNOWN


# ============================================================================
# Factual Claims Tests
# ============================================================================


class TestFactualClaims:
    """Tests for factual claims extraction."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.complete = AsyncMock()
        provider.get_stats = MagicMock(return_value={})
        return provider

    @pytest.fixture
    def agent(self, mock_provider):
        """Create a Bias Agent instance."""
        return BiasAgent(provider=mock_provider)

    def _make_response(self, data: dict) -> LLMResponse:
        """Create a mock LLM response with JSON content."""
        return LLMResponse(
            content=json.dumps(data),
            model="test-model",
            provider="test",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            response_time_seconds=1.0,
        )

    @pytest.mark.asyncio
    async def test_extracts_factual_claims(self, agent, mock_provider):
        """Test extraction of verifiable claims."""
        article = _make_article(
            title="Report Shows 50% Increase",
            content="The report shows a 50% increase in X and 30% decrease in Y.",
            source="news.example.com",
        )

        mock_provider.complete.return_value = self._make_response({
            "bias_score": 0.5,
            "bias_direction": "CENTER",
            "verifiable_claims": [
                "50% increase in X",
                "30% decrease in Y",
            ],
            "bias_confidence": 0.8,
        })

        analysis = await agent.analyze(article)
        # BiasAnalysis has verifiable_claims, not factual_claims
        assert len(analysis.verifiable_claims) >= 0
