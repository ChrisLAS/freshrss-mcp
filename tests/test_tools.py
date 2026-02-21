"""Tests for tools.py — tool registration and error boundaries.

These tests verify that:
1. Tools catch all exceptions and return 'Error: ...' strings
2. Tools produce correct output for happy paths
3. The _truncate_summary helper works at boundaries
"""

from unittest.mock import AsyncMock

import pytest

from freshrss_mcp.client import FreshRSSClient
from freshrss_mcp.config import Config
from freshrss_mcp.models import Article, Feed
from freshrss_mcp.tools import _truncate_summary, register_tools

# We don't need a real FastMCP server — we just need to capture the
# registered tool functions so we can call them directly.


class FakeMCP:
    """Minimal stand-in that captures tool registrations."""

    def __init__(self):
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


@pytest.fixture
def config():
    return Config(
        FRESHRSS_URL="https://test.freshrss.com",
        FRESHRSS_USERNAME="testuser",
        FRESHRSS_PASSWORD="testpass",
    )


@pytest.fixture
def mock_client(config):
    client = FreshRSSClient(config)
    client._auth_token = "test-token"
    return client


@pytest.fixture
def tools(mock_client):
    """Register tools on a fake MCP and return them as a dict."""
    fake_mcp = FakeMCP()
    register_tools(fake_mcp, mock_client)
    return fake_mcp.tools


# --- _truncate_summary ---


class TestTruncateSummary:
    def test_short_text_unchanged(self):
        assert _truncate_summary("hello", 100) == "hello"

    def test_exact_length_unchanged(self):
        text = "a" * 50
        assert _truncate_summary(text, 50) == text

    def test_truncates_at_word_boundary(self):
        text = "hello world this is a test"
        result = _truncate_summary(text, 15)
        assert result.endswith("...")
        assert len(result) <= 18  # 15 + "..."

    def test_empty_string(self):
        assert _truncate_summary("", 100) == ""

    def test_zero_max_length(self):
        result = _truncate_summary("hello world", 0)
        assert result.endswith("...")


# --- Tool Error Boundaries ---


SAMPLE_ARTICLES = [
    Article(
        id=1,
        title="Art 1",
        summary="Summary one",
        url="https://a.com",
        published=1000,
        feed_name="Feed A",
        is_read=False,
        is_starred=False,
    ),
    Article(
        id=2,
        title="Art 2",
        summary="Summary two",
        url="https://b.com",
        published=2000,
        feed_name="Feed B",
        is_read=True,
        is_starred=True,
    ),
]

SAMPLE_FEEDS = [
    Feed(id=10, name="Feed A", url="https://a.com/rss"),
    Feed(id=20, name="Feed B", url="https://b.com/rss"),
]


@pytest.mark.asyncio
async def test_get_unread_articles_happy_path(tools, mock_client):
    mock_client.get_articles = AsyncMock(return_value=SAMPLE_ARTICLES)

    result = await tools["get_unread_articles"]()
    assert "Art 1" in result
    assert "Art 2" in result


@pytest.mark.asyncio
async def test_get_unread_articles_error_returns_string(tools, mock_client):
    mock_client.get_articles = AsyncMock(side_effect=RuntimeError("connection lost"))

    result = await tools["get_unread_articles"]()
    assert result.startswith("Error:")
    assert "connection lost" in result


@pytest.mark.asyncio
async def test_list_feeds_happy_path(tools, mock_client):
    mock_client.list_feeds = AsyncMock(return_value=SAMPLE_FEEDS)
    mock_client.get_unread_counts = AsyncMock(return_value={10: 5, 20: 0})

    result = await tools["list_feeds"]()
    assert "Feed A" in result
    assert "Feed B" in result


@pytest.mark.asyncio
async def test_list_feeds_error_returns_string(tools, mock_client):
    mock_client.list_feeds = AsyncMock(side_effect=RuntimeError("timeout"))

    result = await tools["list_feeds"]()
    assert result.startswith("Error:")


@pytest.mark.asyncio
async def test_get_feed_info_found(tools, mock_client):
    mock_client.list_feeds = AsyncMock(return_value=SAMPLE_FEEDS)
    mock_client.get_unread_counts = AsyncMock(return_value={10: 3})

    result = await tools["get_feed_info"](feed_id=10)
    assert "Feed A" in result


@pytest.mark.asyncio
async def test_get_feed_info_not_found(tools, mock_client):
    mock_client.list_feeds = AsyncMock(return_value=SAMPLE_FEEDS)
    mock_client.get_unread_counts = AsyncMock(return_value={})

    result = await tools["get_feed_info"](feed_id=999)
    assert "Error:" in result
    assert "999" in result


@pytest.mark.asyncio
async def test_search_articles_matches(tools, mock_client):
    mock_client.get_articles = AsyncMock(return_value=SAMPLE_ARTICLES)

    result = await tools["search_articles"](query="Art 1")
    assert "Art 1" in result
    assert "Art 2" not in result


@pytest.mark.asyncio
async def test_search_articles_no_match(tools, mock_client):
    mock_client.get_articles = AsyncMock(return_value=SAMPLE_ARTICLES)

    result = await tools["search_articles"](query="nonexistent")
    assert result == "[]"


@pytest.mark.asyncio
async def test_search_articles_error(tools, mock_client):
    mock_client.get_articles = AsyncMock(side_effect=RuntimeError("fail"))

    result = await tools["search_articles"](query="test")
    assert result.startswith("Error:")


@pytest.mark.asyncio
async def test_mark_as_read_empty_list(tools, mock_client):
    result = await tools["mark_as_read"](article_ids=[])
    assert result == "OK"


@pytest.mark.asyncio
async def test_mark_as_read_success(tools, mock_client):
    mock_client.mark_as_read = AsyncMock(return_value=True)

    result = await tools["mark_as_read"](article_ids=[1, 2, 3])
    assert result == "OK"


@pytest.mark.asyncio
async def test_mark_as_read_error(tools, mock_client):
    mock_client.mark_as_read = AsyncMock(side_effect=RuntimeError("server error"))

    result = await tools["mark_as_read"](article_ids=[1])
    assert result.startswith("Error:")


@pytest.mark.asyncio
async def test_mark_as_unread_success(tools, mock_client):
    mock_client.mark_as_unread = AsyncMock(return_value=True)

    result = await tools["mark_as_unread"](article_ids=[1])
    assert result == "OK"


@pytest.mark.asyncio
async def test_star_article_success(tools, mock_client):
    mock_client.star_article = AsyncMock(return_value=True)

    result = await tools["star_article"](article_id=42)
    assert result == "OK"


@pytest.mark.asyncio
async def test_star_article_error(tools, mock_client):
    mock_client.star_article = AsyncMock(side_effect=RuntimeError("denied"))

    result = await tools["star_article"](article_id=42)
    assert result.startswith("Error:")


@pytest.mark.asyncio
async def test_unstar_article_success(tools, mock_client):
    mock_client.unstar_article = AsyncMock(return_value=True)

    result = await tools["unstar_article"](article_id=42)
    assert result == "OK"


@pytest.mark.asyncio
async def test_get_feed_stats_happy(tools, mock_client):
    mock_client.list_feeds = AsyncMock(return_value=SAMPLE_FEEDS)
    mock_client.get_unread_counts = AsyncMock(return_value={10: 7, 20: 2})

    result = await tools["get_feed_stats"]()
    assert "Feed A" in result
    assert "7" in result


@pytest.mark.asyncio
async def test_get_articles_by_feed_success(tools, mock_client):
    mock_client.get_articles = AsyncMock(return_value=[SAMPLE_ARTICLES[0]])

    result = await tools["get_articles_by_feed"](feed_id=10)
    assert "Art 1" in result


@pytest.mark.asyncio
async def test_get_articles_by_feed_error(tools, mock_client):
    mock_client.get_articles = AsyncMock(side_effect=RuntimeError("boom"))

    result = await tools["get_articles_by_feed"](feed_id=10)
    assert result.startswith("Error:")
