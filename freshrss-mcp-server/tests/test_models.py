"""Tests for FreshRSS MCP Server."""

import pytest
from freshrss_mcp_server.models import Article, Feed, FeedStats
from freshrss_mcp_server.config import Config


def test_article_model():
    """Test Article dataclass."""
    article = Article(
        id=123,
        title="Test Article",
        summary="This is a test summary",
        url="https://example.com/article",
        published=1234567890,
        feed_name="Test Feed",
        is_read=False,
        is_starred=True,
    )
    
    assert article.id == 123
    assert article.title == "Test Article"
    assert article.is_starred is True
    
    # Test to_dict
    d = article.to_dict()
    assert d["id"] == 123
    assert d["title"] == "Test Article"


def test_feed_model():
    """Test Feed dataclass."""
    feed = Feed(
        id=456,
        name="Test Feed",
        url="https://example.com/feed",
        unread_count=5,
    )
    
    assert feed.id == 456
    assert feed.unread_count == 5
    
    d = feed.to_dict()
    assert d["name"] == "Test Feed"


def test_feed_stats_model():
    """Test FeedStats dataclass."""
    stats = FeedStats(
        feed_id=456,
        feed_name="Test Feed",
        unread_count=5,
        total_count=100,
        last_updated=1234567890,
    )
    
    assert stats.unread_count == 5
    assert stats.total_count == 100


def test_config_from_env_missing_vars():
    """Test Config raises error for missing env vars."""
    import os
    
    # Clear required env vars
    for var in ["FRESHRSS_URL", "FRESHRSS_USERNAME", "FRESHRSS_PASSWORD"]:
        if var in os.environ:
            del os.environ[var]
    
    with pytest.raises(ValueError, match="Missing required environment variables"):
        Config.from_env()


def test_config_from_env_complete():
    """Test Config loads from environment."""
    import os
    
    os.environ["FRESHRSS_URL"] = "https://test.com"
    os.environ["FRESHRSS_USERNAME"] = "testuser"
    os.environ["FRESHRSS_PASSWORD"] = "testpass"
    
    config = Config.from_env()
    
    assert config.freshrss_url == "https://test.com"
    assert config.freshrss_username == "testuser"
    assert config.freshrss_password == "testpass"
    assert config.mcp_server_port == 3004  # Default
