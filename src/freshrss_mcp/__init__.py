"""FreshRSS MCP Server — Streamable HTTP transport for OpenClaw integration."""

from .client import AuthenticationError, FreshRSSClient
from .models import Article, Feed
from .server import main

__all__ = [
    "main",
    "FreshRSSClient",
    "AuthenticationError",
    "Article",
    "Feed",
]

__version__ = "0.2.0"
