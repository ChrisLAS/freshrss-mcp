"""Integration tests for FreshRSS client with mocked API."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from freshrss_mcp_server.freshrss_client import AuthenticationError, FreshRSSClient


@pytest.fixture
def client():
    """Create a FreshRSS client for testing."""
    return FreshRSSClient(
        base_url="https://test.freshrss.com",
        username="testuser",
        password="testpass",
    )


@pytest.mark.asyncio
async def test_authenticate_success(client):
    """Test successful authentication."""
    mock_response = MagicMock()
    mock_response.text = "SID=abc123\nLSID=def456\nAuth=ghi789"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False

    with patch.object(client, "_get_client", return_value=mock_client):
        token = await client.authenticate()

    assert token == "abc123"
    assert client._auth_token == "abc123"


@pytest.mark.asyncio
async def test_authenticate_failure(client):
    """Test authentication failure."""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("Forbidden", request=MagicMock(), response=mock_response)
    )

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False

    with patch.object(client, "_get_client", return_value=mock_client), pytest.raises(AuthenticationError):
        await client.authenticate()


@pytest.mark.asyncio
async def test_list_feeds(client):
    """Test listing feeds."""
    client._auth_token = "test_token"

    mock_response = MagicMock()
    mock_response.json = MagicMock(
        return_value={
            "subscriptions": [
                {"id": "feed/123", "title": "Test Feed 1", "url": "https://example.com/feed1"},
                {"id": "feed/456", "title": "Test Feed 2", "url": "https://example.com/feed2"},
            ]
        }
    )
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False

    with patch.object(client, "_get_client", return_value=mock_client):
        feeds = await client.list_feeds()

    assert len(feeds) == 2
    assert feeds[0].name == "Test Feed 1"
    assert feeds[0].url == "https://example.com/feed1"


@pytest.mark.asyncio
async def test_get_unread_counts(client):
    """Test getting unread counts."""
    client._auth_token = "test_token"

    mock_response = MagicMock()
    mock_response.json = MagicMock(
        return_value={
            "unreadcounts": [
                {"id": "feed/123", "count": 5},
                {"id": "feed/456", "count": 3},
            ]
        }
    )
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False

    with patch.object(client, "_get_client", return_value=mock_client):
        counts = await client.get_unread_counts()

    assert counts[123] == 5
    assert counts[456] == 3


@pytest.mark.asyncio
async def test_get_articles(client):
    """Test getting articles."""
    client._auth_token = "test_token"

    mock_response = MagicMock()
    mock_response.json = MagicMock(
        return_value={
            "items": [
                {
                    "id": "tag:google.com,2005:reader/item/1234567890",
                    "title": "Test Article",
                    "published": 1234567890,
                    "alternate": [{"href": "https://example.com/article"}],
                    "summary": {"content": "Test summary"},
                    "origin": {"title": "Test Feed"},
                    "categories": ["user/-/state/com.google/read"],
                }
            ]
        }
    )
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False

    with patch.object(client, "_get_client", return_value=mock_client):
        articles = await client.get_articles(limit=10)

    assert len(articles) == 1
    assert articles[0].title == "Test Article"
    assert articles[0].is_read is True


@pytest.mark.asyncio
async def test_mark_as_read(client):
    """Test marking articles as read."""
    client._auth_token = "test_token"

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False

    with patch.object(client, "_get_client", return_value=mock_client):
        result = await client.mark_as_read([123, 456])

    assert result is True


@pytest.mark.asyncio
async def test_star_article(client):
    """Test starring an article."""
    client._auth_token = "test_token"

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False

    with patch.object(client, "_get_client", return_value=mock_client):
        result = await client.star_article(123)

    assert result is True


def test_extract_feed_id_numeric():
    """Test extracting numeric feed ID."""
    client = FreshRSSClient("https://test.com", "user", "pass")
    assert client._extract_feed_id("feed/123") == 123
    assert client._extract_feed_id("456") == 456


def test_extract_feed_id_string():
    """Test extracting feed ID from string URL."""
    client = FreshRSSClient("https://test.com", "user", "pass")
    # Should return hash for non-numeric IDs
    result = client._extract_feed_id("feed/https://example.com/rss")
    assert isinstance(result, int)


def test_extract_article_id():
    """Test extracting article ID."""
    client = FreshRSSClient("https://test.com", "user", "pass")
    assert client._extract_article_id("tag:google.com,2005:reader/item/1234567890") == 1234567890
