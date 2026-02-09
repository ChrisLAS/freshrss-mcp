"""Data models for FreshRSS MCP Server."""

from dataclasses import dataclass


@dataclass
class Article:
    """Represents a FreshRSS article with minimal fields for token efficiency."""

    id: int
    title: str
    summary: str
    url: str
    published: int  # Unix timestamp
    feed_name: str
    is_read: bool
    is_starred: bool

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "published": self.published,
            "feed_name": self.feed_name,
            "is_read": self.is_read,
            "is_starred": self.is_starred,
        }


@dataclass
class Feed:
    """Represents a FreshRSS feed."""

    id: int
    name: str
    url: str
    unread_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "unread_count": self.unread_count,
        }


@dataclass
class FeedStats:
    """Statistics for a FreshRSS feed."""

    feed_id: int
    feed_name: str
    unread_count: int
    total_count: int
    last_updated: int  # Unix timestamp

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "feed_id": self.feed_id,
            "feed_name": self.feed_name,
            "unread_count": self.unread_count,
            "total_count": self.total_count,
            "last_updated": self.last_updated,
        }
