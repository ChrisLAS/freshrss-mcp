"""FreshRSS MCP Server - Model Context Protocol integration for FreshRSS."""

from .freshrss_client import AuthenticationError, FreshRSSClient
from .models import Article, Feed, FeedStats
from .server import main, mcp

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
