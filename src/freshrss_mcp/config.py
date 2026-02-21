"""Configuration management for FreshRSS MCP Server.

All configuration comes from environment variables. Uses pydantic-settings
for validation so missing or malformed credentials produce clear errors
at startup rather than cryptic failures during tool calls.
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Server configuration loaded from environment variables."""

    freshrss_url: str = Field(alias="FRESHRSS_URL")
    freshrss_username: str = Field(alias="FRESHRSS_USERNAME")
    freshrss_password: SecretStr = Field(alias="FRESHRSS_PASSWORD")
    freshrss_api_path: str = Field(default="/api/greader.php", alias="FRESHRSS_API_PATH")
    server_host: str = Field(default="127.0.0.1", alias="MCP_SERVER_HOST")
    server_port: int = Field(default=8000, alias="MCP_SERVER_PORT")

    model_config = SettingsConfigDict(
        populate_by_name=True,
        extra="ignore",
    )


def load_config() -> Config:
    """Load and validate config from environment. Raises on missing required vars."""
    return Config()
