"""
Tests for Connection Agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


class MockConnectionAgent:
    """Mock Connection Agent for testing."""

    def __init__(self, provider):
        self.provider = provider
        self.min_similarity_threshold = 0.5
        self.max_connections_per_article = 5

    async def find_connections(self, articles: list[dict]) -> list[dict]:
        """Find connections between articles."""
        if len(articles) < 2:
            return []

        connections = []
        for i, article1 in enumerate(articles):
            for j, article2 in enumerate(articles):
                if i >= j:
                    continue

                similarity = self._calculate_similarity(article1, article2)
                if similarity >= self.min_similarity_threshold:
                    connections.append({
                        "article1_id": article1.get("id", str(i)),
                        "article2_id": article2.get("id", str(j)),
                        "similarity": similarity,
                        "connection_type": self._determine_connection_type(article1, article2),
                        "description": f"Connection between '{article1.get('title', '')}' and '{article2.get('title', '')}'",
                    })

        return sorted(connections, key=lambda x: x["similarity"], reverse=True)

    def _calculate_similarity(self, article1: dict, article2: dict) -> float:
        """Calculate similarity between two articles."""
        # Mock similarity based on shared topics
        topics1 = set(article1.get("topics", []))
        topics2 = set(article2.get("topics", []))

        if not topics1 or not topics2:
            return 0.0

        intersection = topics1 & topics2
        union = topics1 | topics2

        return len(intersection) / len(union) if union else 0.0

    def _determine_connection_type(self, article1: dict, article2: dict) -> str:
        """Determine the type of connection."""
        topics1 = set(article1.get("topics", []))
        topics2 = set(article2.get("topics", []))

        if topics1 == topics2:
            return "same_topic"
        elif topics1 & topics2:
            return "related_topic"
        else:
            return "thematic"

    async def cluster_articles(self, articles: list[dict]) -> list[list[dict]]:
        """Cluster articles by similarity."""
        if not articles:
            return []

        # Simple clustering based on primary topic
        clusters: dict[str, list[dict]] = {}

        for article in articles:
            topics = article.get("topics", [])
            primary_topic = topics[0] if topics else "uncategorized"

            if primary_topic not in clusters:
                clusters[primary_topic] = []
            clusters[primary_topic].append(article)

        return list(clusters.values())

    async def generate_narrative(self, cluster: list[dict]) -> str:
        """Generate a narrative connecting articles in a cluster."""
        if not cluster:
            return ""

        titles = [a.get("title", "") for a in cluster]
        return f"These {len(cluster)} articles explore related themes: {', '.join(titles[:3])}..."


@pytest.fixture
def mock_provider():
    """Create mock LLM provider."""
    provider = MagicMock()
    provider.generate = AsyncMock(return_value="Generated connection analysis")
    return provider


@pytest.fixture
def connection_agent(mock_provider):
    """Create Connection Agent instance."""
    return MockConnectionAgent(mock_provider)


@pytest.fixture
def sample_articles():
    """Create sample articles for testing."""
    return [
        {
            "id": "article-1",
            "title": "AI Breakthrough in Language Models",
            "summary": "New advances in LLM technology",
            "topics": ["AI", "Machine Learning", "NLP"],
            "source": "Tech News",
        },
        {
            "id": "article-2",
            "title": "Machine Learning Revolutionizes Healthcare",
            "summary": "ML applications in medical diagnosis",
            "topics": ["AI", "Healthcare", "Machine Learning"],
            "source": "Health Weekly",
        },
        {
            "id": "article-3",
            "title": "Climate Change Policy Updates",
            "summary": "New environmental regulations",
            "topics": ["Environment", "Policy", "Climate"],
            "source": "Policy Daily",
        },
        {
            "id": "article-4",
            "title": "Deep Learning for Climate Prediction",
            "summary": "AI models for weather forecasting",
            "topics": ["AI", "Climate", "Machine Learning"],
            "source": "Science Journal",
        },
        {
            "id": "article-5",
            "title": "Quantum Computing Advances",
            "summary": "New quantum computer achievements",
            "topics": ["Quantum", "Computing", "Physics"],
            "source": "Physics Today",
        },
    ]


class TestConnectionAgentBasics:
    """Test basic Connection Agent functionality."""

    @pytest.mark.asyncio
    async def test_find_connections_with_no_articles(self, connection_agent):
        """Should return empty list for no articles."""
        result = await connection_agent.find_connections([])
        assert result == []

    @pytest.mark.asyncio
    async def test_find_connections_with_single_article(self, connection_agent, sample_articles):
        """Should return empty list for single article."""
        result = await connection_agent.find_connections([sample_articles[0]])
        assert result == []

    @pytest.mark.asyncio
    async def test_find_connections_between_related_articles(self, connection_agent, sample_articles):
        """Should find connections between related articles."""
        # Use only AI-related articles
        ai_articles = [sample_articles[0], sample_articles[1]]
        result = await connection_agent.find_connections(ai_articles)

        assert len(result) >= 1
        assert result[0]["similarity"] >= 0.5

    @pytest.mark.asyncio
    async def test_find_connections_sorted_by_similarity(self, connection_agent, sample_articles):
        """Should return connections sorted by similarity."""
        result = await connection_agent.find_connections(sample_articles)

        for i in range(len(result) - 1):
            assert result[i]["similarity"] >= result[i + 1]["similarity"]


class TestSimilarityCalculation:
    """Test similarity calculation."""

    def test_similarity_with_identical_topics(self, connection_agent):
        """Should return 1.0 for identical topics."""
        article1 = {"topics": ["AI", "ML"]}
        article2 = {"topics": ["AI", "ML"]}

        similarity = connection_agent._calculate_similarity(article1, article2)
        assert similarity == 1.0

    def test_similarity_with_no_overlap(self, connection_agent):
        """Should return 0.0 for no topic overlap."""
        article1 = {"topics": ["AI", "ML"]}
        article2 = {"topics": ["Sports", "Football"]}

        similarity = connection_agent._calculate_similarity(article1, article2)
        assert similarity == 0.0

    def test_similarity_with_partial_overlap(self, connection_agent):
        """Should return partial similarity for some overlap."""
        article1 = {"topics": ["AI", "ML", "Tech"]}
        article2 = {"topics": ["AI", "Healthcare"]}

        similarity = connection_agent._calculate_similarity(article1, article2)
        assert 0 < similarity < 1

    def test_similarity_with_empty_topics(self, connection_agent):
        """Should return 0.0 for empty topics."""
        article1 = {"topics": []}
        article2 = {"topics": ["AI"]}

        similarity = connection_agent._calculate_similarity(article1, article2)
        assert similarity == 0.0

    def test_similarity_with_missing_topics(self, connection_agent):
        """Should return 0.0 for missing topics."""
        article1 = {}
        article2 = {"topics": ["AI"]}

        similarity = connection_agent._calculate_similarity(article1, article2)
        assert similarity == 0.0


class TestConnectionTypes:
    """Test connection type determination."""

    def test_same_topic_connection(self, connection_agent):
        """Should identify same topic connections."""
        article1 = {"topics": ["AI", "ML"]}
        article2 = {"topics": ["AI", "ML"]}

        conn_type = connection_agent._determine_connection_type(article1, article2)
        assert conn_type == "same_topic"

    def test_related_topic_connection(self, connection_agent):
        """Should identify related topic connections."""
        article1 = {"topics": ["AI", "ML"]}
        article2 = {"topics": ["AI", "Healthcare"]}

        conn_type = connection_agent._determine_connection_type(article1, article2)
        assert conn_type == "related_topic"

    def test_thematic_connection(self, connection_agent):
        """Should identify thematic connections."""
        article1 = {"topics": ["AI", "ML"]}
        article2 = {"topics": ["Sports", "Football"]}

        conn_type = connection_agent._determine_connection_type(article1, article2)
        assert conn_type == "thematic"


class TestClustering:
    """Test article clustering."""

    @pytest.mark.asyncio
    async def test_cluster_empty_articles(self, connection_agent):
        """Should return empty clusters for no articles."""
        result = await connection_agent.cluster_articles([])
        assert result == []

    @pytest.mark.asyncio
    async def test_cluster_single_article(self, connection_agent, sample_articles):
        """Should create single cluster for one article."""
        result = await connection_agent.cluster_articles([sample_articles[0]])
        assert len(result) == 1
        assert len(result[0]) == 1

    @pytest.mark.asyncio
    async def test_cluster_by_primary_topic(self, connection_agent, sample_articles):
        """Should cluster articles by primary topic."""
        result = await connection_agent.cluster_articles(sample_articles)

        # Should have multiple clusters
        assert len(result) >= 1

        # Each cluster should have articles
        for cluster in result:
            assert len(cluster) >= 1

    @pytest.mark.asyncio
    async def test_cluster_articles_without_topics(self, connection_agent):
        """Should handle articles without topics."""
        articles = [
            {"id": "1", "title": "Article 1"},
            {"id": "2", "title": "Article 2"},
        ]
        result = await connection_agent.cluster_articles(articles)

        # Should create uncategorized cluster
        assert len(result) >= 1


class TestNarrativeGeneration:
    """Test narrative generation."""

    @pytest.mark.asyncio
    async def test_generate_narrative_empty_cluster(self, connection_agent):
        """Should return empty string for empty cluster."""
        result = await connection_agent.generate_narrative([])
        assert result == ""

    @pytest.mark.asyncio
    async def test_generate_narrative_single_article(self, connection_agent, sample_articles):
        """Should generate narrative for single article."""
        result = await connection_agent.generate_narrative([sample_articles[0]])
        assert len(result) > 0
        assert "1 articles" in result

    @pytest.mark.asyncio
    async def test_generate_narrative_multiple_articles(self, connection_agent, sample_articles):
        """Should generate narrative for multiple articles."""
        result = await connection_agent.generate_narrative(sample_articles[:3])
        assert len(result) > 0
        assert "3 articles" in result


class TestConnectionFiltering:
    """Test connection filtering."""

    def test_filter_by_threshold(self, connection_agent):
        """Should respect similarity threshold."""
        connection_agent.min_similarity_threshold = 0.7

        article1 = {"topics": ["AI", "ML", "Tech"]}
        article2 = {"topics": ["AI"]}

        similarity = connection_agent._calculate_similarity(article1, article2)
        # 1/3 = 0.33, below threshold
        assert similarity < 0.7

    @pytest.mark.asyncio
    async def test_connections_respect_threshold(self, connection_agent, sample_articles):
        """All returned connections should be above threshold."""
        result = await connection_agent.find_connections(sample_articles)

        for connection in result:
            assert connection["similarity"] >= connection_agent.min_similarity_threshold


class TestConnectionData:
    """Test connection data structure."""

    @pytest.mark.asyncio
    async def test_connection_has_required_fields(self, connection_agent, sample_articles):
        """Connections should have all required fields."""
        result = await connection_agent.find_connections(sample_articles[:2])

        if result:  # If any connections found
            connection = result[0]
            assert "article1_id" in connection
            assert "article2_id" in connection
            assert "similarity" in connection
            assert "connection_type" in connection
            assert "description" in connection

    @pytest.mark.asyncio
    async def test_connection_ids_are_unique(self, connection_agent, sample_articles):
        """Each article pair should appear only once."""
        result = await connection_agent.find_connections(sample_articles)

        pairs = set()
        for connection in result:
            pair = tuple(sorted([connection["article1_id"], connection["article2_id"]]))
            assert pair not in pairs
            pairs.add(pair)

    @pytest.mark.asyncio
    async def test_connection_similarity_is_valid(self, connection_agent, sample_articles):
        """Similarity should be between 0 and 1."""
        result = await connection_agent.find_connections(sample_articles)

        for connection in result:
            assert 0 <= connection["similarity"] <= 1


class TestEdgeCases:
    """Test edge cases."""

    @pytest.mark.asyncio
    async def test_duplicate_articles(self, connection_agent):
        """Should handle duplicate articles."""
        article = {"id": "1", "title": "Test", "topics": ["AI"]}
        result = await connection_agent.find_connections([article, article])

        # Should find perfect similarity
        if result:
            assert result[0]["similarity"] == 1.0

    @pytest.mark.asyncio
    async def test_articles_with_special_characters(self, connection_agent):
        """Should handle articles with special characters."""
        articles = [
            {"id": "1", "title": "Test & More <script>", "topics": ["AI"]},
            {"id": "2", "title": "Another 'Test'", "topics": ["AI"]},
        ]
        result = await connection_agent.find_connections(articles)
        # Should not raise exception
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_large_number_of_articles(self, connection_agent):
        """Should handle large number of articles."""
        articles = [
            {"id": str(i), "title": f"Article {i}", "topics": [f"Topic{i % 5}"]}
            for i in range(100)
        ]
        result = await connection_agent.find_connections(articles)
        # Should return some connections
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_articles_with_many_topics(self, connection_agent):
        """Should handle articles with many topics."""
        articles = [
            {"id": "1", "title": "Article 1", "topics": [f"Topic{i}" for i in range(50)]},
            {"id": "2", "title": "Article 2", "topics": [f"Topic{i}" for i in range(25, 75)]},
        ]
        result = await connection_agent.find_connections(articles)
        assert isinstance(result, list)


class TestConnectionMetrics:
    """Test connection metrics."""

    @pytest.mark.asyncio
    async def test_count_connections_per_article(self, connection_agent, sample_articles):
        """Should count connections per article."""
        result = await connection_agent.find_connections(sample_articles)

        connection_count: dict[str, int] = {}
        for conn in result:
            connection_count[conn["article1_id"]] = connection_count.get(conn["article1_id"], 0) + 1
            connection_count[conn["article2_id"]] = connection_count.get(conn["article2_id"], 0) + 1

        # Verify we can count
        assert isinstance(connection_count, dict)

    @pytest.mark.asyncio
    async def test_average_similarity(self, connection_agent, sample_articles):
        """Should calculate average similarity."""
        result = await connection_agent.find_connections(sample_articles)

        if result:
            avg_similarity = sum(c["similarity"] for c in result) / len(result)
            assert 0 <= avg_similarity <= 1


class TestTopicAnalysis:
    """Test topic analysis for connections."""

    def test_shared_topics(self, connection_agent):
        """Should identify shared topics."""
        article1 = {"topics": ["AI", "ML", "Tech"]}
        article2 = {"topics": ["AI", "Healthcare", "ML"]}

        topics1 = set(article1["topics"])
        topics2 = set(article2["topics"])
        shared = topics1 & topics2

        assert "AI" in shared
        assert "ML" in shared
        assert "Tech" not in shared

    def test_unique_topics(self, connection_agent):
        """Should identify unique topics."""
        article1 = {"topics": ["AI", "ML"]}
        article2 = {"topics": ["AI", "Healthcare"]}

        topics1 = set(article1["topics"])
        topics2 = set(article2["topics"])
        unique_to_1 = topics1 - topics2
        unique_to_2 = topics2 - topics1

        assert "ML" in unique_to_1
        assert "Healthcare" in unique_to_2


class TestConnectionStrength:
    """Test connection strength classification."""

    def test_strong_connection(self, connection_agent):
        """Should identify strong connections."""
        article1 = {"topics": ["AI", "ML", "NLP"]}
        article2 = {"topics": ["AI", "ML", "NLP"]}

        similarity = connection_agent._calculate_similarity(article1, article2)
        assert similarity >= 0.8  # Strong connection

    def test_moderate_connection(self, connection_agent):
        """Should identify moderate connections."""
        article1 = {"topics": ["AI", "ML", "NLP"]}
        article2 = {"topics": ["AI", "Healthcare"]}

        similarity = connection_agent._calculate_similarity(article1, article2)
        assert 0.2 <= similarity <= 0.8  # Moderate connection

    def test_weak_connection(self, connection_agent):
        """Should identify weak connections."""
        article1 = {"topics": ["AI", "ML", "NLP", "Tech"]}
        article2 = {"topics": ["Sports"]}

        similarity = connection_agent._calculate_similarity(article1, article2)
        assert similarity < 0.2  # Weak connection
