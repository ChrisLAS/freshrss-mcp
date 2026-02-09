"""FreshRSS MCP Server - Model Context Protocol integration for FreshRSS."""

from .server import main, mcp
from .freshrss_client import FreshRSSClient, AuthenticationError
from .models import Article, Feed, FeedStats

__all__ = [
    "main",
    "mcp",
    "FreshRSSClient",
    "AuthenticationError",
    "Article",
    "Feed",
    "FeedStats",
]

__version__ = "0.1.0"
