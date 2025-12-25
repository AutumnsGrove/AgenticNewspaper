"""
Tests for User model.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Any
import json
import hashlib
import hmac
import secrets


class UserPreferences:
    """User preferences model."""

    def __init__(
        self,
        topics: list[str] | None = None,
        delivery_frequency: str = "daily_am",
        delivery_time_utc: str = "06:00",
        channels: list[str] | None = None,
        timezone: str = "UTC",
        tone: str = "hn-style",
        skepticism_level: int = 3,
        technical_depth: int = 3,
        include_bias_analysis: bool = True,
        include_connections: bool = True,
        max_articles_per_topic: int = 5,
    ):
        self.topics = topics or []
        self.delivery_frequency = delivery_frequency
        self.delivery_time_utc = delivery_time_utc
        self.channels = channels or ["web"]
        self.timezone = timezone
        self.tone = tone
        self.skepticism_level = skepticism_level
        self.technical_depth = technical_depth
        self.include_bias_analysis = include_bias_analysis
        self.include_connections = include_connections
        self.max_articles_per_topic = max_articles_per_topic

    def to_dict(self) -> dict:
        return {
            "topics": self.topics,
            "delivery_frequency": self.delivery_frequency,
            "delivery_time_utc": self.delivery_time_utc,
            "channels": self.channels,
            "timezone": self.timezone,
            "tone": self.tone,
            "skepticism_level": self.skepticism_level,
            "technical_depth": self.technical_depth,
            "include_bias_analysis": self.include_bias_analysis,
            "include_connections": self.include_connections,
            "max_articles_per_topic": self.max_articles_per_topic,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserPreferences":
        return cls(**{k: v for k, v in data.items() if k in cls.__init__.__code__.co_varnames})


class User:
    """User model."""

    def __init__(
        self,
        id: str,
        email: str,
        name: str = "",
        subscription_tier: str = "free",
        preferences: UserPreferences | None = None,
        created_at: datetime | None = None,
        last_login: datetime | None = None,
        email_verified: bool = False,
        api_key: str | None = None,
    ):
        self.id = id
        self.email = email
        self.name = name
        self.subscription_tier = subscription_tier
        self.preferences = preferences or UserPreferences()
        self.created_at = created_at or datetime.now(timezone.utc)
        self.last_login = last_login
        self.email_verified = email_verified
        self.api_key = api_key

    @property
    def is_premium(self) -> bool:
        return self.subscription_tier in ["basic", "pro"]

    @property
    def max_topics(self) -> int:
        limits = {"free": 3, "basic": 10, "pro": 50}
        return limits.get(self.subscription_tier, 3)

    @property
    def max_digests_per_day(self) -> int:
        limits = {"free": 1, "basic": 3, "pro": 10}
        return limits.get(self.subscription_tier, 1)

    def can_add_topic(self) -> bool:
        return len(self.preferences.topics) < self.max_topics

    def update_last_login(self) -> None:
        self.last_login = datetime.now(timezone.utc)

    def verify_email(self) -> None:
        self.email_verified = True

    def generate_api_key(self) -> str:
        self.api_key = secrets.token_urlsafe(32)
        return self.api_key

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "subscription_tier": self.subscription_tier,
            "preferences": self.preferences.to_dict(),
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "email_verified": self.email_verified,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        prefs = UserPreferences.from_dict(data.get("preferences", {}))
        return cls(
            id=data["id"],
            email=data["email"],
            name=data.get("name", ""),
            subscription_tier=data.get("subscription_tier", "free"),
            preferences=prefs,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            last_login=datetime.fromisoformat(data["last_login"]) if data.get("last_login") else None,
            email_verified=data.get("email_verified", False),
        )


@pytest.fixture
def sample_preferences():
    """Create sample preferences."""
    return UserPreferences(
        topics=["AI", "Technology"],
        delivery_frequency="daily_am",
        channels=["web", "email"],
        timezone="America/New_York",
        tone="hn-style",
        skepticism_level=4,
    )


@pytest.fixture
def sample_user(sample_preferences):
    """Create sample user."""
    return User(
        id="user-1",
        email="test@example.com",
        name="Test User",
        subscription_tier="basic",
        preferences=sample_preferences,
        email_verified=True,
    )


class TestUserPreferencesCreation:
    """Test UserPreferences creation."""

    def test_create_default_preferences(self):
        """Should create preferences with defaults."""
        prefs = UserPreferences()
        assert prefs.topics == []
        assert prefs.delivery_frequency == "daily_am"
        assert prefs.channels == ["web"]

    def test_create_custom_preferences(self, sample_preferences):
        """Should create preferences with custom values."""
        assert sample_preferences.topics == ["AI", "Technology"]
        assert sample_preferences.skepticism_level == 4

    def test_preferences_to_dict(self, sample_preferences):
        """Should convert preferences to dict."""
        data = sample_preferences.to_dict()
        assert data["topics"] == ["AI", "Technology"]
        assert data["skepticism_level"] == 4

    def test_preferences_from_dict(self):
        """Should create preferences from dict."""
        data = {
            "topics": ["Science"],
            "delivery_frequency": "weekly",
            "tone": "formal",
        }
        prefs = UserPreferences.from_dict(data)
        assert prefs.topics == ["Science"]
        assert prefs.delivery_frequency == "weekly"


class TestUserCreation:
    """Test User creation."""

    def test_create_user_minimal(self):
        """Should create user with minimal fields."""
        user = User(id="1", email="test@example.com")
        assert user.id == "1"
        assert user.email == "test@example.com"

    def test_create_user_full(self, sample_user):
        """Should create user with all fields."""
        assert sample_user.name == "Test User"
        assert sample_user.subscription_tier == "basic"

    def test_default_values(self):
        """Should use default values."""
        user = User(id="1", email="test@example.com")
        assert user.subscription_tier == "free"
        assert user.email_verified is False
        assert user.name == ""

    def test_auto_created_at(self):
        """Should set created_at automatically."""
        user = User(id="1", email="test@example.com")
        assert user.created_at is not None


class TestUserProperties:
    """Test User properties."""

    def test_is_premium_free(self):
        """Free tier should not be premium."""
        user = User(id="1", email="test@example.com", subscription_tier="free")
        assert user.is_premium is False

    def test_is_premium_basic(self):
        """Basic tier should be premium."""
        user = User(id="1", email="test@example.com", subscription_tier="basic")
        assert user.is_premium is True

    def test_is_premium_pro(self):
        """Pro tier should be premium."""
        user = User(id="1", email="test@example.com", subscription_tier="pro")
        assert user.is_premium is True

    def test_max_topics_free(self):
        """Free tier should have 3 max topics."""
        user = User(id="1", email="test@example.com", subscription_tier="free")
        assert user.max_topics == 3

    def test_max_topics_basic(self):
        """Basic tier should have 10 max topics."""
        user = User(id="1", email="test@example.com", subscription_tier="basic")
        assert user.max_topics == 10

    def test_max_topics_pro(self):
        """Pro tier should have 50 max topics."""
        user = User(id="1", email="test@example.com", subscription_tier="pro")
        assert user.max_topics == 50

    def test_max_digests_per_day_free(self):
        """Free tier should have 1 max digest per day."""
        user = User(id="1", email="test@example.com", subscription_tier="free")
        assert user.max_digests_per_day == 1

    def test_max_digests_per_day_pro(self):
        """Pro tier should have 10 max digests per day."""
        user = User(id="1", email="test@example.com", subscription_tier="pro")
        assert user.max_digests_per_day == 10


class TestUserTopicManagement:
    """Test topic management."""

    def test_can_add_topic_under_limit(self):
        """Should allow adding topic under limit."""
        user = User(id="1", email="test@example.com", subscription_tier="free")
        user.preferences.topics = ["AI"]
        assert user.can_add_topic() is True

    def test_cannot_add_topic_at_limit(self):
        """Should not allow adding topic at limit."""
        user = User(id="1", email="test@example.com", subscription_tier="free")
        user.preferences.topics = ["AI", "Science", "Tech"]
        assert user.can_add_topic() is False

    def test_premium_has_more_topics(self):
        """Premium users should have higher topic limits."""
        free_user = User(id="1", email="test@example.com", subscription_tier="free")
        premium_user = User(id="2", email="test2@example.com", subscription_tier="pro")

        assert premium_user.max_topics > free_user.max_topics


class TestUserMethods:
    """Test User methods."""

    def test_update_last_login(self, sample_user):
        """Should update last login timestamp."""
        sample_user.update_last_login()
        assert sample_user.last_login is not None

    def test_verify_email(self, sample_user):
        """Should verify email."""
        sample_user.email_verified = False
        sample_user.verify_email()
        assert sample_user.email_verified is True

    def test_generate_api_key(self, sample_user):
        """Should generate API key."""
        key = sample_user.generate_api_key()
        assert key is not None
        assert len(key) > 20
        assert sample_user.api_key == key


class TestUserSerialization:
    """Test User serialization."""

    def test_user_to_dict(self, sample_user):
        """Should convert user to dict."""
        data = sample_user.to_dict()
        assert data["id"] == "user-1"
        assert data["email"] == "test@example.com"
        assert "preferences" in data

    def test_user_to_dict_no_api_key(self, sample_user):
        """Should not include API key in dict."""
        sample_user.generate_api_key()
        data = sample_user.to_dict()
        assert "api_key" not in data

    def test_user_from_dict(self):
        """Should create user from dict."""
        data = {
            "id": "1",
            "email": "test@example.com",
            "name": "Test",
            "subscription_tier": "pro",
            "preferences": {"topics": ["AI"]},
            "created_at": "2025-01-15T10:00:00+00:00",
            "email_verified": True,
        }
        user = User.from_dict(data)
        assert user.id == "1"
        assert user.subscription_tier == "pro"

    def test_roundtrip_serialization(self, sample_user):
        """Should survive roundtrip serialization."""
        data = sample_user.to_dict()
        restored = User.from_dict(data)
        assert restored.id == sample_user.id
        assert restored.email == sample_user.email


class TestPreferencesValidation:
    """Test preferences validation."""

    def test_valid_frequencies(self):
        """Should accept valid frequencies."""
        valid = ["hourly", "daily_am", "daily_pm", "weekly", "biweekly", "monthly"]
        for freq in valid:
            prefs = UserPreferences(delivery_frequency=freq)
            assert prefs.delivery_frequency == freq

    def test_valid_tones(self):
        """Should accept valid tones."""
        valid = ["hn-style", "formal", "casual"]
        for tone in valid:
            prefs = UserPreferences(tone=tone)
            assert prefs.tone == tone

    def test_skepticism_level_range(self):
        """Skepticism level should be 1-5."""
        for level in [1, 2, 3, 4, 5]:
            prefs = UserPreferences(skepticism_level=level)
            assert 1 <= prefs.skepticism_level <= 5

    def test_technical_depth_range(self):
        """Technical depth should be 1-5."""
        for depth in [1, 2, 3, 4, 5]:
            prefs = UserPreferences(technical_depth=depth)
            assert 1 <= prefs.technical_depth <= 5


class TestSubscriptionTiers:
    """Test subscription tier features."""

    def test_free_tier_limits(self):
        """Free tier should have proper limits."""
        user = User(id="1", email="test@example.com", subscription_tier="free")
        assert user.max_topics == 3
        assert user.max_digests_per_day == 1

    def test_basic_tier_limits(self):
        """Basic tier should have proper limits."""
        user = User(id="1", email="test@example.com", subscription_tier="basic")
        assert user.max_topics == 10
        assert user.max_digests_per_day == 3

    def test_pro_tier_limits(self):
        """Pro tier should have proper limits."""
        user = User(id="1", email="test@example.com", subscription_tier="pro")
        assert user.max_topics == 50
        assert user.max_digests_per_day == 10


class TestTimezoneHandling:
    """Test timezone handling."""

    def test_default_timezone(self):
        """Default timezone should be UTC."""
        prefs = UserPreferences()
        assert prefs.timezone == "UTC"

    def test_custom_timezone(self):
        """Should accept custom timezone."""
        prefs = UserPreferences(timezone="America/New_York")
        assert prefs.timezone == "America/New_York"

    def test_common_timezones(self):
        """Should accept common timezones."""
        timezones = [
            "America/New_York",
            "America/Los_Angeles",
            "Europe/London",
            "Asia/Tokyo",
            "Pacific/Auckland",
        ]
        for tz in timezones:
            prefs = UserPreferences(timezone=tz)
            assert prefs.timezone == tz


class TestDeliverySettings:
    """Test delivery settings."""

    def test_default_delivery_time(self):
        """Default delivery time should be 06:00."""
        prefs = UserPreferences()
        assert prefs.delivery_time_utc == "06:00"

    def test_custom_delivery_time(self):
        """Should accept custom delivery time."""
        prefs = UserPreferences(delivery_time_utc="18:00")
        assert prefs.delivery_time_utc == "18:00"

    def test_default_channels(self):
        """Default channels should be web only."""
        prefs = UserPreferences()
        assert prefs.channels == ["web"]

    def test_multiple_channels(self):
        """Should accept multiple channels."""
        prefs = UserPreferences(channels=["web", "email", "rss"])
        assert len(prefs.channels) == 3


class TestEmailValidation:
    """Test email handling."""

    def test_simple_email(self):
        """Should store simple email."""
        user = User(id="1", email="test@example.com")
        assert user.email == "test@example.com"

    def test_email_with_plus(self):
        """Should store email with plus."""
        user = User(id="1", email="test+tag@example.com")
        assert user.email == "test+tag@example.com"

    def test_email_case_preservation(self):
        """Should preserve email case."""
        user = User(id="1", email="Test@Example.COM")
        assert user.email == "Test@Example.COM"


class TestAccountAge:
    """Test account age calculations."""

    def test_new_account(self):
        """New account should have age near zero."""
        user = User(id="1", email="test@example.com")
        age = datetime.now(timezone.utc) - user.created_at
        assert age.total_seconds() < 60

    def test_old_account(self):
        """Should calculate old account age."""
        old_time = datetime.now(timezone.utc) - timedelta(days=30)
        user = User(id="1", email="test@example.com", created_at=old_time)
        age = datetime.now(timezone.utc) - user.created_at
        assert age.days >= 30


class TestAPIKeyManagement:
    """Test API key management."""

    def test_api_key_generation_length(self):
        """API key should have sufficient length."""
        user = User(id="1", email="test@example.com")
        key = user.generate_api_key()
        assert len(key) >= 32

    def test_api_key_uniqueness(self):
        """Each generated key should be unique."""
        user = User(id="1", email="test@example.com")
        keys = [user.generate_api_key() for _ in range(10)]
        assert len(set(keys)) == 10

    def test_api_key_format(self):
        """API key should be URL-safe."""
        user = User(id="1", email="test@example.com")
        key = user.generate_api_key()
        # URL-safe characters only
        assert all(c.isalnum() or c in "-_" for c in key)


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_name(self):
        """Should handle empty name."""
        user = User(id="1", email="test@example.com", name="")
        assert user.name == ""

    def test_unicode_name(self):
        """Should handle unicode name."""
        user = User(id="1", email="test@example.com", name="日本太郎")
        assert user.name == "日本太郎"

    def test_empty_topics(self):
        """Should handle empty topics."""
        prefs = UserPreferences(topics=[])
        assert prefs.topics == []

    def test_many_topics(self):
        """Should handle many topics."""
        topics = [f"Topic{i}" for i in range(100)]
        prefs = UserPreferences(topics=topics)
        assert len(prefs.topics) == 100


class TestPreferencesFeatureFlags:
    """Test preference feature flags."""

    def test_bias_analysis_default(self):
        """Bias analysis should be enabled by default."""
        prefs = UserPreferences()
        assert prefs.include_bias_analysis is True

    def test_connections_default(self):
        """Connections should be enabled by default."""
        prefs = UserPreferences()
        assert prefs.include_connections is True

    def test_disable_bias_analysis(self):
        """Should allow disabling bias analysis."""
        prefs = UserPreferences(include_bias_analysis=False)
        assert prefs.include_bias_analysis is False

    def test_disable_connections(self):
        """Should allow disabling connections."""
        prefs = UserPreferences(include_connections=False)
        assert prefs.include_connections is False


class TestMaxArticlesPerTopic:
    """Test max articles per topic setting."""

    def test_default_max_articles(self):
        """Default should be 5 articles per topic."""
        prefs = UserPreferences()
        assert prefs.max_articles_per_topic == 5

    def test_custom_max_articles(self):
        """Should accept custom max articles."""
        prefs = UserPreferences(max_articles_per_topic=10)
        assert prefs.max_articles_per_topic == 10
