"""Data models for FreshRSS MCP Server."""

from dataclasses import dataclass


@dataclass
class Article:
    """Represents a FreshRSS article with minimal fields for token efficiency."""

    id: int
    title: str
    summary: str
    url: str
    published: int
    feed_name: str
    is_read: bool
    is_starred: bool

    def to_dict(self) -> dict:
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
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "unread_count": self.unread_count,
        }
