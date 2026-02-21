"""Tests for config.py — environment-based configuration loading."""

import os

import pytest

from freshrss_mcp.config import Config, load_config


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Remove all FRESHRSS/MCP env vars before each test."""
    for key in list(os.environ):
        if key.startswith(("FRESHRSS_", "MCP_SERVER_")):
            monkeypatch.delenv(key, raising=False)


def test_load_config_missing_required_vars():
    """Missing required env vars produce a clear validation error."""
    with pytest.raises((ValueError, SystemExit)):
        load_config()


def test_load_config_missing_password_only(monkeypatch):
    """Missing just the password still fails."""
    monkeypatch.setenv("FRESHRSS_URL", "https://rss.example.com")
    monkeypatch.setenv("FRESHRSS_USERNAME", "alice")
    with pytest.raises((ValueError, SystemExit)):
        load_config()


def test_load_config_all_required(monkeypatch):
    """All required vars present produces a valid Config."""
    monkeypatch.setenv("FRESHRSS_URL", "https://rss.example.com")
    monkeypatch.setenv("FRESHRSS_USERNAME", "alice")
    monkeypatch.setenv("FRESHRSS_PASSWORD", "s3cret")

    config = load_config()

    assert config.freshrss_url == "https://rss.example.com"
    assert config.freshrss_username == "alice"
    assert config.freshrss_password.get_secret_value() == "s3cret"


def test_defaults(monkeypatch):
    """Optional fields use sensible defaults."""
    monkeypatch.setenv("FRESHRSS_URL", "https://rss.example.com")
    monkeypatch.setenv("FRESHRSS_USERNAME", "alice")
    monkeypatch.setenv("FRESHRSS_PASSWORD", "s3cret")

    config = load_config()

    assert config.freshrss_api_path == "/api/greader.php"
    assert config.server_host == "127.0.0.1"
    assert config.server_port == 8000


def test_custom_port_and_host(monkeypatch):
    """Custom host/port are read from env."""
    monkeypatch.setenv("FRESHRSS_URL", "https://rss.example.com")
    monkeypatch.setenv("FRESHRSS_USERNAME", "alice")
    monkeypatch.setenv("FRESHRSS_PASSWORD", "s3cret")
    monkeypatch.setenv("MCP_SERVER_HOST", "0.0.0.0")
    monkeypatch.setenv("MCP_SERVER_PORT", "9999")

    config = load_config()

    assert config.server_host == "0.0.0.0"
    assert config.server_port == 9999


def test_password_is_secret(monkeypatch):
    """Password is masked in string representation."""
    monkeypatch.setenv("FRESHRSS_URL", "https://rss.example.com")
    monkeypatch.setenv("FRESHRSS_USERNAME", "alice")
    monkeypatch.setenv("FRESHRSS_PASSWORD", "s3cret")

    config = load_config()

    assert "s3cret" not in repr(config)
    assert "s3cret" not in str(config)


def test_extra_env_vars_ignored(monkeypatch):
    """Unknown env vars don't cause failures (extra='ignore')."""
    monkeypatch.setenv("FRESHRSS_URL", "https://rss.example.com")
    monkeypatch.setenv("FRESHRSS_USERNAME", "alice")
    monkeypatch.setenv("FRESHRSS_PASSWORD", "s3cret")
    monkeypatch.setenv("FRESHRSS_UNKNOWN_VAR", "whatever")

    config = load_config()
    assert config.freshrss_url == "https://rss.example.com"


def test_config_direct_construction():
    """Config can be constructed directly with keyword args."""
    config = Config(
        FRESHRSS_URL="https://rss.example.com",
        FRESHRSS_USERNAME="bob",
        FRESHRSS_PASSWORD="pw",
    )
    assert config.freshrss_username == "bob"
