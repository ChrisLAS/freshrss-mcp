"""MCP Server implementation for FreshRSS integration."""

import logging

from mcp.server import FastMCP

from .config import Config
from .freshrss_client import FreshRSSClient

logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("freshrss-mcp-server")


async def _get_client() -> FreshRSSClient:
    """Get authenticated FreshRSS client."""
    config = Config.from_env()
    client = FreshRSSClient(
        base_url=config.freshrss_url,
        username=config.freshrss_username,
        password=config.freshrss_password,
        api_path=config.freshrss_api_path,
    )
    await client.authenticate()
    return client


def _truncate_summary(summary: str, max_length: int) -> str:
    """Truncate summary to maximum length."""
    if len(summary) <= max_length:
        return summary
    return summary[:max_length].rsplit(" ", 1)[0] + "..."


@mcp.tool()
async def get_unread_articles(
    limit: int = 20,
    feed_ids: list[int] | None = None,
    since_timestamp: int | None = None,
    max_summary_length: int = 500,
) -> list[dict]:
    """Get unread articles from FreshRSS.

    Args:
        limit: Maximum number of articles to return (default: 20)
        feed_ids: Optional list of feed IDs to filter by
        since_timestamp: Only return articles published after this Unix timestamp
        max_summary_length: Maximum characters for article summaries (default: 500)

    Returns:
        List of article dictionaries with minimal fields for token efficiency
    """
    client = await _get_client()

    try:
        if feed_ids:
            # Fetch from specific feeds
            all_articles = []
            for feed_id in feed_ids:
                articles = await client.get_articles(
                    feed_id=feed_id,
                    limit=limit,
                    include_read=False,
                    since_timestamp=since_timestamp,
                )
                all_articles.extend(articles)

            # Sort by published date and limit
            all_articles.sort(key=lambda a: a.published, reverse=True)
            articles = all_articles[:limit]
        else:
            # Fetch from all feeds
            articles = await client.get_articles(
                limit=limit,
                include_read=False,
                since_timestamp=since_timestamp,
            )

        # Apply summary truncation
        result = []
        for article in articles:
            article_dict = article.to_dict()
            article_dict["summary"] = _truncate_summary(article_dict["summary"], max_summary_length)
            result.append(article_dict)

        return result

    finally:
        await client.close()


@mcp.tool()
async def get_articles_by_feed(
    feed_id: int,
    limit: int = 20,
    include_read: bool = False,
) -> list[dict]:
    """Get articles from a specific feed.

    Args:
        feed_id: ID of the feed to fetch articles from
        limit: Maximum number of articles to return (default: 20)
        include_read: Whether to include already read articles (default: False)

    Returns:
        List of article dictionaries
    """
    client = await _get_client()

    try:
        articles = await client.get_articles(
            feed_id=feed_id,
            limit=limit,
            include_read=include_read,
        )
        return [article.to_dict() for article in articles]

    finally:
        await client.close()


@mcp.tool()
async def search_articles(
    query: str,
    limit: int = 10,
    feed_ids: list[int] | None = None,
) -> list[dict]:
    """Search articles by keyword in title or summary.

    Note: FreshRSS API doesn't support server-side search, so this performs
    client-side filtering. For better performance, consider using get_unread_articles
    with specific feed filters.

    Args:
        query: Search query string
        limit: Maximum number of articles to return (default: 10)
        feed_ids: Optional list of feed IDs to search within

    Returns:
        List of matching article dictionaries
    """
    client = await _get_client()

    try:
        # Fetch articles (with higher limit to allow for filtering)
        fetch_limit = limit * 3  # Fetch more to allow for filtering

        if feed_ids:
            all_articles = []
            for feed_id in feed_ids:
                articles = await client.get_articles(
                    feed_id=feed_id,
                    limit=fetch_limit,
                    include_read=True,
                )
                all_articles.extend(articles)
            articles = all_articles
        else:
            articles = await client.get_articles(
                limit=fetch_limit,
                include_read=True,
            )

        # Client-side search (case-insensitive)
        query_lower = query.lower()
        matching = [
            article
            for article in articles
            if query_lower in article.title.lower() or query_lower in article.summary.lower()
        ]

        # Return limited results
        return [article.to_dict() for article in matching[:limit]]

    finally:
        await client.close()


@mcp.tool()
async def list_feeds() -> list[dict]:
    """List all subscribed feeds with unread counts.

    Returns:
        List of feed dictionaries including unread counts
    """
    client = await _get_client()

    try:
        # Get feeds and unread counts in parallel
        feeds = await client.list_feeds()
        unread_counts = await client.get_unread_counts()

        # Merge unread counts into feeds
        result = []
        for feed in feeds:
            feed.unread_count = unread_counts.get(feed.id, 0)
            result.append(feed.to_dict())

        return result

    finally:
        await client.close()


@mcp.tool()
async def get_feed_info(feed_id: int) -> dict:
    """Get detailed information about a specific feed.

    Args:
        feed_id: ID of the feed

    Returns:
        Feed information dictionary
    """
    client = await _get_client()

    try:
        feeds = await client.list_feeds()
        unread_counts = await client.get_unread_counts()

        for feed in feeds:
            if feed.id == feed_id:
                feed.unread_count = unread_counts.get(feed.id, 0)
                return feed.to_dict()

        raise ValueError(f"Feed {feed_id} not found")

    finally:
        await client.close()


@mcp.tool()
async def mark_as_read(article_ids: list[int]) -> bool:
    """Mark articles as read.

    Args:
        article_ids: List of article IDs to mark as read

    Returns:
        True if successful
    """
    if not article_ids:
        return True

    client = await _get_client()

    try:
        return await client.mark_as_read(article_ids)
    finally:
        await client.close()


@mcp.tool()
async def mark_as_unread(article_ids: list[int]) -> bool:
    """Mark articles as unread.

    Args:
        article_ids: List of article IDs to mark as unread

    Returns:
        True if successful
    """
    if not article_ids:
        return True

    client = await _get_client()

    try:
        return await client.mark_as_unread(article_ids)
    finally:
        await client.close()


@mcp.tool()
async def star_article(article_id: int) -> bool:
    """Star an article.

    Args:
        article_id: ID of the article to star

    Returns:
        True if successful
    """
    client = await _get_client()

    try:
        return await client.star_article(article_id)
    finally:
        await client.close()


@mcp.tool()
async def unstar_article(article_id: int) -> bool:
    """Unstar an article.

    Args:
        article_id: ID of the article to unstar

    Returns:
        True if successful
    """
    client = await _get_client()

    try:
        return await client.unstar_article(article_id)
    finally:
        await client.close()


@mcp.tool()
async def get_feed_stats() -> list[dict]:
    """Get statistics for all feeds.

    Returns:
        List of feed statistics dictionaries
    """
    client = await _get_client()

    try:
        feeds = await client.list_feeds()
        unread_counts = await client.get_unread_counts()

        result = []
        for feed in feeds:
            unread = unread_counts.get(feed.id, 0)
            # Note: FreshRSS API doesn't provide total count easily
            # We'll estimate based on unread or set to 0
            result.append(
                {
                    "feed_id": feed.id,
                    "feed_name": feed.name,
                    "unread_count": unread,
                    "total_count": 0,  # Not available via simple API
                    "last_updated": 0,  # Would require per-feed fetch
                }
            )

        return result

    finally:
        await client.close()


def main():
    """Run the MCP server."""

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get configuration
    config = Config.from_env()

    logger.info(
        f"Starting FreshRSS MCP Server on {config.mcp_server_host}:{config.mcp_server_port}"
    )

    # Run with HTTP transport
    mcp.run(
        transport="streamable-http",
        host=config.mcp_server_host,
        port=config.mcp_server_port,
    )


if __name__ == "__main__":
    main()
