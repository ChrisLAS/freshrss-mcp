"""Tests for client.py — FreshRSS API client with mocked HTTP."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from freshrss_mcp.client import AuthenticationError, FreshRSSClient
from freshrss_mcp.config import Config


@pytest.fixture
def config():
    return Config(
        FRESHRSS_URL="https://test.freshrss.com",
        FRESHRSS_USERNAME="testuser",
        FRESHRSS_PASSWORD="testpass",
    )


@pytest.fixture
def client(config):
    return FreshRSSClient(config)


# --- Authentication ---


@pytest.mark.asyncio
async def test_authenticate_success(client):
    mock_response = MagicMock()
    mock_response.text = "SID=abc123\nLSID=def456\nAuth=ghi789"
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_response):
        token = await client.authenticate()

    assert token == "abc123"
    assert client._auth_token == "abc123"


@pytest.mark.asyncio
async def test_authenticate_no_sid(client):
    """Response without SID raises AuthenticationError."""
    mock_response = MagicMock()
    mock_response.text = "Auth=ghi789\nLSID=def456"
    mock_response.raise_for_status = MagicMock()

    with (
        patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_response),
        pytest.raises(AuthenticationError, match="No SID found"),
    ):
        await client.authenticate()


@pytest.mark.asyncio
async def test_authenticate_http_error(client):
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("Forbidden", request=MagicMock(), response=mock_response)
    )

    with (
        patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_response),
        pytest.raises(AuthenticationError, match="403"),
    ):
        await client.authenticate()


@pytest.mark.asyncio
async def test_get_auth_headers_unauthenticated(client):
    """Calling _get_auth_headers before authenticate raises."""
    with pytest.raises(AuthenticationError, match="Not authenticated"):
        client._get_auth_headers()


# --- Feed Operations ---


@pytest.mark.asyncio
async def test_list_feeds(client):
    client._auth_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "subscriptions": [
            {"id": "feed/123", "title": "Feed A", "url": "https://a.com/rss"},
            {"id": "feed/456", "title": "Feed B", "url": "https://b.com/rss"},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "get", new_callable=AsyncMock, return_value=mock_response):
        feeds = await client.list_feeds()

    assert len(feeds) == 2
    assert feeds[0].name == "Feed A"
    assert feeds[0].id == 123
    assert feeds[1].url == "https://b.com/rss"


@pytest.mark.asyncio
async def test_list_feeds_empty(client):
    client._auth_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {"subscriptions": []}
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "get", new_callable=AsyncMock, return_value=mock_response):
        feeds = await client.list_feeds()

    assert feeds == []


@pytest.mark.asyncio
async def test_get_unread_counts(client):
    client._auth_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "unreadcounts": [
            {"id": "feed/123", "count": 5},
            {"id": "feed/456", "count": 3},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "get", new_callable=AsyncMock, return_value=mock_response):
        counts = await client.get_unread_counts()

    assert counts[123] == 5
    assert counts[456] == 3


# --- Article Operations ---

SAMPLE_ITEM = {
    "id": "tag:google.com,2005:reader/item/1234567890",
    "title": "Test Article",
    "published": 1700000000,
    "alternate": [{"href": "https://example.com/article"}],
    "summary": {"content": "Article summary text"},
    "origin": {"title": "Source Feed"},
    "categories": ["user/-/state/com.google/read"],
}


@pytest.mark.asyncio
async def test_get_articles(client):
    client._auth_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {"items": [SAMPLE_ITEM]}
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "get", new_callable=AsyncMock, return_value=mock_response):
        articles = await client.get_articles(limit=10)

    assert len(articles) == 1
    assert articles[0].title == "Test Article"
    assert articles[0].is_read is True
    assert articles[0].is_starred is False
    assert articles[0].id == 1234567890


@pytest.mark.asyncio
async def test_get_articles_with_feed_filter(client):
    client._auth_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {"items": [SAMPLE_ITEM]}
    mock_response.raise_for_status = MagicMock()

    mock_get = AsyncMock(return_value=mock_response)
    with patch.object(client._client, "get", mock_get):
        await client.get_articles(feed_id=42, limit=5)

    call_url = mock_get.call_args[0][0]
    assert "feed/42" in call_url


@pytest.mark.asyncio
async def test_get_articles_empty_response(client):
    client._auth_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {"items": []}
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "get", new_callable=AsyncMock, return_value=mock_response):
        articles = await client.get_articles()

    assert articles == []


# --- Tag Operations ---


@pytest.mark.asyncio
async def test_mark_as_read(client):
    client._auth_token = "tok"
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_post = AsyncMock(return_value=mock_response)
    with patch.object(client._client, "post", mock_post):
        result = await client.mark_as_read([100, 200])

    assert result is True
    call_data = mock_post.call_args[1]["data"]
    assert "user/-/state/com.google/read" in call_data["a"]


@pytest.mark.asyncio
async def test_mark_as_unread(client):
    client._auth_token = "tok"
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_post = AsyncMock(return_value=mock_response)
    with patch.object(client._client, "post", mock_post):
        result = await client.mark_as_unread([100])

    assert result is True
    call_data = mock_post.call_args[1]["data"]
    assert "user/-/state/com.google/read" in call_data["r"]


@pytest.mark.asyncio
async def test_star_article(client):
    client._auth_token = "tok"
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_post = AsyncMock(return_value=mock_response)
    with patch.object(client._client, "post", mock_post):
        result = await client.star_article(999)

    assert result is True


@pytest.mark.asyncio
async def test_unstar_article(client):
    client._auth_token = "tok"
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_post = AsyncMock(return_value=mock_response)
    with patch.object(client._client, "post", mock_post):
        result = await client.unstar_article(999)

    assert result is True


# --- ID Extraction ---


class TestExtractFeedId:
    def test_numeric_with_prefix(self):
        assert FreshRSSClient._extract_feed_id("feed/123") == 123

    def test_numeric_without_prefix(self):
        assert FreshRSSClient._extract_feed_id("456") == 456

    def test_url_string_falls_back_to_hash(self):
        result = FreshRSSClient._extract_feed_id("feed/https://example.com/rss")
        assert isinstance(result, int)
        assert 0 <= result < 1_000_000

    def test_empty_string(self):
        result = FreshRSSClient._extract_feed_id("")
        assert isinstance(result, int)


class TestExtractArticleId:
    def test_decimal_id(self):
        assert (
            FreshRSSClient._extract_article_id("tag:google.com,2005:reader/item/1234567890")
            == 1234567890
        )

    def test_hex_id(self):
        result = FreshRSSClient._extract_article_id(
            "tag:google.com,2005:reader/item/00000186a7b3c4d5"
        )
        assert result == 0x00000186A7B3C4D5

    def test_non_numeric_falls_back_to_hash(self):
        result = FreshRSSClient._extract_article_id("some-random-string")
        assert isinstance(result, int)

    def test_empty_string(self):
        result = FreshRSSClient._extract_article_id("")
        assert isinstance(result, int)


# --- Parse Article Edge Cases ---


class TestParseArticle:
    def test_missing_summary(self, client):
        item = {
            "id": "tag:google.com,2005:reader/item/1",
            "title": "No Summary",
            "published": 0,
            "alternate": [{"href": "https://x.com"}],
            "origin": {"title": "Feed"},
            "categories": [],
        }
        article = client._parse_article(item)
        assert article is not None
        assert article.summary == ""

    def test_missing_alternate(self, client):
        item = {
            "id": "tag:google.com,2005:reader/item/1",
            "title": "No URL",
            "published": 0,
            "alternate": [],
            "summary": {"content": "text"},
            "origin": {"title": "Feed"},
            "categories": [],
        }
        article = client._parse_article(item)
        assert article is not None
        assert article.url == ""

    def test_starred_article(self, client):
        item = {
            "id": "tag:google.com,2005:reader/item/1",
            "title": "Starred",
            "published": 0,
            "alternate": [{"href": ""}],
            "summary": {"content": ""},
            "origin": {"title": "Feed"},
            "categories": ["user/-/state/com.google/starred"],
        }
        article = client._parse_article(item)
        assert article is not None
        assert article.is_starred is True
        assert article.is_read is False

    def test_malformed_item_still_parses(self, client):
        """Minimal/garbage data produces an Article with safe defaults."""
        article = client._parse_article({"garbage": True})
        assert article is not None
        assert article.title == "Untitled"
        assert article.summary == ""
        assert article.url == ""


# --- Lifecycle ---


@pytest.mark.asyncio
async def test_aclose(client):
    await client.aclose()
    assert client._client.is_closed
