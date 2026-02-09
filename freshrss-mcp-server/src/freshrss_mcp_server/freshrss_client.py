"""FreshRSS API client using Google Reader API."""

import logging
from typing import Optional
import httpx
from .models import Article, Feed, FeedStats

logger = logging.getLogger(__name__)


class FreshRSSClient:
    """Client for FreshRSS Google Reader API."""
    
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        api_path: str = "/api/greader.php",
    ):
        """Initialize FreshRSS client.
        
        Args:
            base_url: Base URL of FreshRSS instance (e.g., https://freshrss.example.com)
            username: FreshRSS username
            password: FreshRSS password
            api_path: API endpoint path (default: /api/greader.php)
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.api_path = api_path.rstrip("/")
        self.api_url = f"{self.base_url}{self.api_path}"
        
        self._auth_token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client
    
    async def authenticate(self) -> str:
        """Authenticate with FreshRSS and obtain auth token.
        
        Returns:
            Authentication token (SID)
            
        Raises:
            AuthenticationError: If authentication fails
        """
        client = await self._get_client()
        
        auth_url = f"{self.api_url}/accounts/ClientLogin"
        logger.debug(f"Authenticating to {auth_url}")
        
        try:
            response = await client.post(
                auth_url,
                data={
                    "Email": self.username,
                    "Passwd": self.password,
                },
            )
            response.raise_for_status()
            
            # Parse response to extract SID
            content = response.text
            for line in content.split("\n"):
                if line.startswith("SID="):
                    self._auth_token = line[4:]
                    logger.info("Authentication successful")
                    return self._auth_token
            
            raise AuthenticationError("No SID found in authentication response")
            
        except httpx.HTTPStatusError as e:
            raise AuthenticationError(f"Authentication failed: {e.response.status_code}") from e
        except Exception as e:
            raise AuthenticationError(f"Authentication error: {e}") from e
    
    def _get_auth_headers(self) -> dict:
        """Get headers with authentication token."""
        if not self._auth_token:
            raise AuthenticationError("Not authenticated. Call authenticate() first.")
        
        return {
            "Authorization": f"GoogleLogin auth={self._auth_token}",
        }
    
    async def list_feeds(self) -> list[Feed]:
        """List all subscribed feeds.
        
        Returns:
            List of Feed objects
        """
        client = await self._get_client()
        headers = self._get_auth_headers()
        
        url = f"{self.api_url}/reader/api/0/subscription/list"
        logger.debug(f"Fetching feed list from {url}")
        
        response = await client.get(url, headers=headers, params={"output": "json"})
        response.raise_for_status()
        
        data = response.json()
        subscriptions = data.get("subscriptions", [])
        
        feeds = []
        for sub in subscriptions:
            feed = Feed(
                id=self._extract_feed_id(sub.get("id", "")),
                name=sub.get("title", "Unknown"),
                url=sub.get("url", ""),
            )
            feeds.append(feed)
        
        logger.info(f"Retrieved {len(feeds)} feeds")
        return feeds
    
    async def get_unread_counts(self) -> dict[int, int]:
        """Get unread article counts per feed.
        
        Returns:
            Dictionary mapping feed_id to unread count
        """
        client = await self._get_client()
        headers = self._get_auth_headers()
        
        url = f"{self.api_url}/reader/api/0/unread-count"
        logger.debug(f"Fetching unread counts from {url}")
        
        response = await client.get(url, headers=headers, params={"output": "json"})
        response.raise_for_status()
        
        data = response.json()
        unread_counts = {}
        
        for item in data.get("unreadcounts", []):
            feed_id = self._extract_feed_id(item.get("id", ""))
            count = item.get("count", 0)
            if feed_id:
                unread_counts[feed_id] = count
        
        return unread_counts
    
    async def get_articles(
        self,
        feed_id: Optional[int] = None,
        limit: int = 20,
        include_read: bool = False,
        since_timestamp: Optional[int] = None,
    ) -> list[Article]:
        """Get articles from FreshRSS.
        
        Args:
            feed_id: Optional feed ID to filter by
            limit: Maximum number of articles to return
            include_read: Whether to include read articles
            since_timestamp: Only return articles published after this timestamp
            
        Returns:
            List of Article objects
        """
        client = await self._get_client()
        headers = self._get_auth_headers()
        
        # Build stream ID
        if feed_id:
            stream_id = f"feed/{feed_id}"
        else:
            stream_id = "user/-/state/com.google/reading-list"
        
        url = f"{self.api_url}/reader/api/0/stream/contents/{stream_id}"
        
        params = {
            "output": "json",
            "n": limit,
            "xt": "user/-/state/com.google/read" if not include_read else "",
        }
        
        if since_timestamp:
            params["ot"] = since_timestamp
        
        # Remove empty params
        params = {k: v for k, v in params.items() if v}
        
        logger.debug(f"Fetching articles from {url} with params {params}")
        
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        items = data.get("items", [])
        
        articles = []
        for item in items:
            article = self._parse_article(item)
            if article:
                articles.append(article)
        
        logger.info(f"Retrieved {len(articles)} articles")
        return articles
    
    async def mark_as_read(self, article_ids: list[int]) -> bool:
        """Mark articles as read.
        
        Args:
            article_ids: List of article IDs to mark as read
            
        Returns:
            True if successful
        """
        return await self._edit_tags(
            article_ids,
            add_tags=["user/-/state/com.google/read"],
        )
    
    async def mark_as_unread(self, article_ids: list[int]) -> bool:
        """Mark articles as unread.
        
        Args:
            article_ids: List of article IDs to mark as unread
            
        Returns:
            True if successful
        """
        return await self._edit_tags(
            article_ids,
            remove_tags=["user/-/state/com.google/read"],
        )
    
    async def star_article(self, article_id: int) -> bool:
        """Star an article.
        
        Args:
            article_id: Article ID to star
            
        Returns:
            True if successful
        """
        return await self._edit_tags(
            [article_id],
            add_tags=["user/-/state/com.google/starred"],
        )
    
    async def unstar_article(self, article_id: int) -> bool:
        """Unstar an article.
        
        Args:
            article_id: Article ID to unstar
            
        Returns:
            True if successful
        """
        return await self._edit_tags(
            [article_id],
            remove_tags=["user/-/state/com.google/starred"],
        )
    
    async def _edit_tags(
        self,
        article_ids: list[int],
        add_tags: Optional[list[str]] = None,
        remove_tags: Optional[list[str]] = None,
    ) -> bool:
        """Edit tags on articles.
        
        Args:
            article_ids: List of article IDs
            add_tags: Tags to add
            remove_tags: Tags to remove
            
        Returns:
            True if successful
        """
        client = await self._get_client()
        headers = self._get_auth_headers()
        
        url = f"{self.api_url}/reader/api/0/edit-tag"
        
        # Convert article IDs to Google Reader format
        item_ids = [f"tag:google.com,2005:reader/item/{aid}" for aid in article_ids]
        
        data = {
            "i": item_ids,
        }
        
        if add_tags:
            data["a"] = add_tags
        if remove_tags:
            data["r"] = remove_tags
        
        logger.debug(f"Editing tags for {len(article_ids)} articles")
        
        response = await client.post(url, headers=headers, data=data)
        response.raise_for_status()
        
        logger.info(f"Successfully updated tags for {len(article_ids)} articles")
        return True
    
    def _parse_article(self, item: dict) -> Optional[Article]:
        """Parse a FreshRSS article item into an Article model.
        
        Args:
            item: Raw article data from API
            
        Returns:
            Article object or None if parsing fails
        """
        try:
            # Extract article ID from Google Reader format
            article_id = self._extract_article_id(item.get("id", ""))
            
            # Get feed name from origin
            origin = item.get("origin", {})
            feed_name = origin.get("title", "Unknown Feed")
            
            # Get summary/content
            summary = ""
            content = item.get("summary", {})
            if content:
                summary = content.get("content", "")
            
            # Check read/starred status from categories
            categories = item.get("categories", [])
            is_read = "user/-/state/com.google/read" in categories
            is_starred = "user/-/state/com.google/starred" in categories
            
            return Article(
                id=article_id,
                title=item.get("title", "Untitled"),
                summary=summary,
                url=item.get("alternate", [{}])[0].get("href", ""),
                published=item.get("published", 0),
                feed_name=feed_name,
                is_read=is_read,
                is_starred=is_starred,
            )
        except Exception as e:
            logger.warning(f"Failed to parse article: {e}")
            return None
    
    @staticmethod
    def _extract_feed_id(feed_id_str: str) -> int:
        """Extract numeric feed ID from Google Reader feed ID format."""
        # Format: feed/http://example.com or feed/123
        if feed_id_str.startswith("feed/"):
            feed_id_str = feed_id_str[5:]
        
        # Try to extract numeric ID
        try:
            return int(feed_id_str)
        except ValueError:
            # If not numeric, use hash of string
            return hash(feed_id_str) % 1000000
    
    @staticmethod
    def _extract_article_id(article_id_str: str) -> int:
        """Extract numeric article ID from Google Reader format."""
        # Format: tag:google.com,2005:reader/item/1234567890
        if "reader/item/" in article_id_str:
            try:
                return int(article_id_str.split("/")[-1])
            except (ValueError, IndexError):
                pass
        
        # Fallback to hash
        return hash(article_id_str) % 1000000000
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass
