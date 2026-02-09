"""Configuration management for FreshRSS MCP Server."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Server configuration from environment variables."""
    
    freshrss_url: str
    freshrss_username: str
    freshrss_password: str
    freshrss_api_path: str = "/api/greader.php"
    mcp_server_port: int = 3004
    mcp_server_host: str = "0.0.0.0"
    default_article_limit: int = 20
    default_summary_length: int = 500
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        required_vars = ["FRESHRSS_URL", "FRESHRSS_USERNAME", "FRESHRSS_PASSWORD"]
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return cls(
            freshrss_url=os.getenv("FRESHRSS_URL", ""),
            freshrss_username=os.getenv("FRESHRSS_USERNAME", ""),
            freshrss_password=os.getenv("FRESHRSS_PASSWORD", ""),
            freshrss_api_path=os.getenv("FRESHRSS_API_PATH", "/api/greader.php"),
            mcp_server_port=int(os.getenv("MCP_SERVER_PORT", "3004")),
            mcp_server_host=os.getenv("MCP_SERVER_HOST", "0.0.0.0"),
            default_article_limit=int(os.getenv("DEFAULT_ARTICLE_LIMIT", "20")),
            default_summary_length=int(os.getenv("DEFAULT_SUMMARY_LENGTH", "500")),
        )
