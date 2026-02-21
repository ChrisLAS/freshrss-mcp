# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## What This Project Is

FreshRSS MCP server using **Streamable HTTP** transport, designed for the **OpenClaw** gateway's `openclaw-mcp-bridge` plugin. It wraps the FreshRSS Google Reader API and exposes 10 MCP tools for RSS feed management.

**Transport**: Streamable HTTP (POST to `/mcp`) -- NOT stdio. The OpenClaw MCP bridge discovers tools via HTTP POST with JSON-RPC 2.0, not by spawning a subprocess.

**Runtime**: Python 3.12+, managed by `uv`. Deployed on NixOS as a systemd service.

## Project Layout

```
freshrss-mcp/
  pyproject.toml          # uv/PEP 621 — entry point: freshrss-mcp
  uv.lock                 # Committed lockfile
  .python-version         # 3.13
  flake.nix               # Dev shell + NixOS module (systemd service)
  src/freshrss_mcp/
    server.py             # FastMCP entry point (streamable-http transport)
    tools.py              # 10 MCP tool definitions with error boundaries
    client.py             # FreshRSS Google Reader API client (async, httpx)
    config.py             # pydantic-settings config from env vars
    models.py             # Article and Feed dataclasses
  tests/                  # 67 unit tests
    test_config.py        # Config validation, defaults, secret masking
    test_client.py        # Auth, feeds, articles, ID extraction, edge cases
    test_tools.py         # Every tool happy path + error boundary
    test_models.py        # Serialization, construction, mutability
```

## Key Architecture Decisions

1. **Lazy authentication**: `client.py` calls `_ensure_authenticated()` before every API method. No need to pre-auth at startup.

2. **Error boundaries**: Every tool in `tools.py` catches all exceptions and returns `"Error: ..."` strings. MCP protocol never sees uncaught exceptions.

3. **pydantic-settings**: `config.py` uses `BaseSettings` with `SecretStr` for the password. Missing env vars produce clear validation errors at startup.

4. **Single client instance**: `FreshRSSClient` is created once in `server.py` and shared across all tool calls. No per-call client creation.

5. **No version pins**: `pyproject.toml` has no version constraints on dependencies, per the MCP build spec.

## How to Run

```bash
# Dev
uv sync && uv run pytest -v

# Start server (needs env vars)
export FRESHRSS_URL="https://freshrss.trailertrash.io"
export FRESHRSS_USERNAME="chrisf"
export FRESHRSS_PASSWORD="..."
export MCP_SERVER_PORT=8765
uv run freshrss-mcp

# Server binds to http://127.0.0.1:8765/mcp
```

## NixOS Integration

The flake exports `nixosModules.default`. Host config (rvbee) at `/home/chrisf/build/config`:

```nix
# In flake.nix inputs:
freshrss-mcp.url = "github:ChrisLAS/freshrss-mcp";
freshrss-mcp.inputs.nixpkgs.follows = "nixpkgs";

# In rvbee modules:
freshrss-mcp.nixosModules.default

# In services config:
services.freshrss-mcp-server = {
  enable = true;
  freshRssUrl = "https://freshrss.trailertrash.io";
  username = "chrisf";
  passwordFile = "/home/chrisf/.config/secrets/freshrss-mcp";
  port = 3005;
  host = "0.0.0.0";
};
```

The password file must be an env file: `FRESHRSS_PASSWORD=<value>`.

## OpenClaw Bridge Config

The server is consumed by the `openclaw-mcp-bridge` plugin in `~/.openclaw/openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "openclaw-mcp-bridge": {
        "config": {
          "servers": [
            {
              "name": "FreshRSS",
              "url": "http://127.0.0.1:3005",
              "prefix": "freshrss"
            }
          ]
        }
      }
    }
  }
}
```

Tools appear as: `freshrss_list_feeds`, `freshrss_get_unread_articles`, etc.

## Quick Reference

```bash
bd ready          # Find available work
bd show <id>      # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>     # Complete work
bd sync           # Sync with git
```

## Landing the Plane (Session Completion)

When ending a session, you MUST:

1. File issues for remaining work
2. Run quality gates: `uv run pytest -v` and `ruff check src/ tests/`
3. Update issue status via `bd close`
4. Push to remote:
   ```bash
   git pull --rebase && bd sync && git push
   git status  # MUST show "up to date with origin"
   ```

Work is NOT complete until `git push` succeeds.
