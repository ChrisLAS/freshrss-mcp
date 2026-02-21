"""FreshRSS API client using Google Reader API."""

import logging

import httpx

from .config import Config
from .models import Article, Feed

logger = logging.getLogger(__name__)


class FreshRSSClient:
    """Async client for FreshRSS Google Reader API.

    Designed for single-instance lifecycle: create once at startup,
    authenticate, then reuse for all tool calls.
    """

    def __init__(self, config: Config):
        self._config = config
        base_url = config.freshrss_url.rstrip("/")
        api_path = config.freshrss_api_path.rstrip("/")
        self.api_url = f"{base_url}{api_path}"
        self._auth_token: str | None = None
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=30.0,
            follow_redirects=True,
        )

    async def authenticate(self) -> str:
        """Authenticate with FreshRSS and obtain auth token.

        Returns:
            Authentication token (SID)

        Raises:
            AuthenticationError: If authentication fails
        """
        auth_url = f"{self.api_url}/accounts/ClientLogin"
        logger.debug("Authenticating to %s", auth_url)

        try:
            response = await self._client.post(
                auth_url,
                data={
                    "Email": self._config.freshrss_username,
                    "Passwd": self._config.freshrss_password.get_secret_value(),
                },
            )
            response.raise_for_status()

            for line in response.text.split("\n"):
                if line.startswith("SID="):
                    self._auth_token = line[4:]
                    logger.info("Authentication successful")
                    return self._auth_token

            raise AuthenticationError("No SID found in authentication response")

        except httpx.HTTPStatusError as e:
            raise AuthenticationError(f"Authentication failed: {e.response.status_code}") from e
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Authentication error: {e}") from e

    def _get_auth_headers(self) -> dict[str, str]:
        """Get headers with authentication token."""
        if not self._auth_token:
            raise AuthenticationError("Not authenticated. Call authenticate() first.")
        return {"Authorization": f"GoogleLogin auth={self._auth_token}"}

    async def list_feeds(self) -> list[Feed]:
        """List all subscribed feeds."""
        headers = self._get_auth_headers()
        url = f"{self.api_url}/reader/api/0/subscription/list"

        response = await self._client.get(url, headers=headers, params={"output": "json"})
        response.raise_for_status()

        data = response.json()
        feeds = []
        for sub in data.get("subscriptions", []):
            feed = Feed(
                id=self._extract_feed_id(sub.get("id", "")),
                name=sub.get("title", "Unknown"),
                url=sub.get("url", ""),
            )
            feeds.append(feed)

        logger.info("Retrieved %d feeds", len(feeds))
        return feeds

    async def get_unread_counts(self) -> dict[int, int]:
        """Get unread article counts per feed.

        Returns:
            Dictionary mapping feed_id to unread count
        """
        headers = self._get_auth_headers()
        url = f"{self.api_url}/reader/api/0/unread-count"

        response = await self._client.get(url, headers=headers, params={"output": "json"})
        response.raise_for_status()

        data = response.json()
        unread_counts: dict[int, int] = {}
        for item in data.get("unreadcounts", []):
            feed_id = self._extract_feed_id(item.get("id", ""))
            count = item.get("count", 0)
            if feed_id:
                unread_counts[feed_id] = count

        return unread_counts

    async def get_articles(
        self,
        feed_id: int | None = None,
        limit: int = 20,
        include_read: bool = False,
        since_timestamp: int | None = None,
    ) -> list[Article]:
        """Get articles from FreshRSS.

        Args:
            feed_id: Optional feed ID to filter by
            limit: Maximum number of articles to return
            include_read: Whether to include read articles
            since_timestamp: Only return articles published after this timestamp
        """
        headers = self._get_auth_headers()
        stream_id = f"feed/{feed_id}" if feed_id else "user/-/state/com.google/reading-list"
        url = f"{self.api_url}/reader/api/0/stream/contents/{stream_id}"

        params: dict[str, str | int] = {"output": "json", "n": limit}
        if not include_read:
            params["xt"] = "user/-/state/com.google/read"
        if since_timestamp:
            params["ot"] = since_timestamp

        response = await self._client.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        articles = []
        for item in data.get("items", []):
            article = self._parse_article(item)
            if article:
                articles.append(article)

        logger.info("Retrieved %d articles", len(articles))
        return articles

    async def mark_as_read(self, article_ids: list[int]) -> bool:
        """Mark articles as read."""
        return await self._edit_tags(article_ids, add_tags=["user/-/state/com.google/read"])

    async def mark_as_unread(self, article_ids: list[int]) -> bool:
        """Mark articles as unread."""
        return await self._edit_tags(article_ids, remove_tags=["user/-/state/com.google/read"])

    async def star_article(self, article_id: int) -> bool:
        """Star an article."""
        return await self._edit_tags([article_id], add_tags=["user/-/state/com.google/starred"])

    async def unstar_article(self, article_id: int) -> bool:
        """Unstar an article."""
        return await self._edit_tags([article_id], remove_tags=["user/-/state/com.google/starred"])

    async def _edit_tags(
        self,
        article_ids: list[int],
        add_tags: list[str] | None = None,
        remove_tags: list[str] | None = None,
    ) -> bool:
        """Edit tags on articles."""
        headers = self._get_auth_headers()
        url = f"{self.api_url}/reader/api/0/edit-tag"

        item_ids = [f"tag:google.com,2005:reader/item/{aid}" for aid in article_ids]
        data: dict[str, list[str]] = {"i": item_ids}
        if add_tags:
            data["a"] = add_tags
        if remove_tags:
            data["r"] = remove_tags

        response = await self._client.post(url, headers=headers, data=data)
        response.raise_for_status()

        logger.info("Updated tags for %d articles", len(article_ids))
        return True

    def _parse_article(self, item: dict) -> Article | None:
        """Parse a FreshRSS article item into an Article model."""
        try:
            article_id = self._extract_article_id(item.get("id", ""))
            origin = item.get("origin", {})
            feed_name = origin.get("title", "Unknown Feed")

            summary = ""
            content = item.get("summary", {})
            if content:
                summary = content.get("content", "")

            categories = item.get("categories", [])
            is_read = "user/-/state/com.google/read" in categories
            is_starred = "user/-/state/com.google/starred" in categories

            alternates = item.get("alternate", [])
            url = alternates[0].get("href", "") if alternates else ""

            return Article(
                id=article_id,
                title=item.get("title", "Untitled"),
                summary=summary,
                url=url,
                published=item.get("published", 0),
                feed_name=feed_name,
                is_read=is_read,
                is_starred=is_starred,
            )
        except Exception as e:
            logger.warning("Failed to parse article: %s", e)
            return None

    @staticmethod
    def _extract_feed_id(feed_id_str: str) -> int:
        """Extract numeric feed ID from Google Reader feed ID format.

        Handles formats like "feed/123" or plain "123".
        Falls back to hash for non-numeric string IDs.
        """
        if feed_id_str.startswith("feed/"):
            feed_id_str = feed_id_str[5:]
        try:
            return int(feed_id_str)
        except ValueError:
            return hash(feed_id_str) % 1_000_000

    @staticmethod
    def _extract_article_id(article_id_str: str) -> int:
        """Extract numeric article ID from Google Reader format.

        Handles "tag:google.com,2005:reader/item/<id>" where <id>
        may be decimal or hex.
        """
        if "reader/item/" in article_id_str:
            raw = article_id_str.split("/")[-1]
            try:
                return int(raw)
            except ValueError:
                try:
                    return int(raw, 16)
                except ValueError:
                    pass
        return hash(article_id_str) % 1_000_000_000

    async def aclose(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class AuthenticationError(Exception):
    """Raised when authentication fails."""
