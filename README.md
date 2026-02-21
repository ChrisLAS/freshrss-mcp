# FreshRSS MCP Server

An MCP server that wraps the FreshRSS Google Reader API, exposing RSS feed management as tools for AI agents. Uses **Streamable HTTP** transport for integration with the OpenClaw gateway via the `openclaw-mcp-bridge` plugin.

Token-optimized: returns only essential fields with configurable summary truncation, achieving ~90% reduction vs raw RSS XML payloads.

---

## NixOS Installation

The flake exports a NixOS module that runs the server as a hardened systemd service.

### 1. Add the flake input

In your host's `flake.nix`:

```nix
inputs = {
  freshrss-mcp.url = "github:ChrisLAS/freshrss-mcp";
  freshrss-mcp.inputs.nixpkgs.follows = "nixpkgs";
};
```

Pass it through to your NixOS configuration:

```nix
nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
  modules = [
    ./system.nix
    freshrss-mcp.nixosModules.default
  ];
};
```

### 2. Configure the service

In your host config (e.g. `system.nix`):

```nix
services.freshrss-mcp-server = {
  enable = true;
  freshRssUrl = "https://freshrss.example.com";
  username = "youruser";
  passwordFile = "/home/youruser/.config/secrets/freshrss-mcp";
  port = 3005;
  host = "0.0.0.0";  # or "127.0.0.1" for loopback only
};
```

The password file must use systemd EnvironmentFile format:

```
FRESHRSS_PASSWORD=your-api-password-here
```

### 3. Rebuild

```bash
sudo nixos-rebuild switch
systemctl status freshrss-mcp-server  # verify it's running
```

The service runs as a sandboxed DynamicUser with hardened security settings.

---

## OpenClaw Gateway Setup

Register the FreshRSS MCP server in the `openclaw-mcp-bridge` plugin inside `~/.openclaw/openclaw.json`. Add a server entry to the existing `servers` array:

```json
{
  "plugins": {
    "entries": {
      "openclaw-mcp-bridge": {
        "enabled": true,
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

Then restart the gateway: `openclaw gateway restart`

Tools will appear with the `freshrss_` prefix, e.g. `freshrss_list_feeds`, `freshrss_get_unread_articles`.

---

## For AI Agents: Setup & Installation Guide

This section is written for agentic LLM sessions that need to deploy, configure, or extend this server.

### Quick Start (non-NixOS)

```bash
# Clone
git clone https://github.com/ChrisLAS/freshrss-mcp.git
cd freshrss-mcp

# Install deps (requires Python 3.12+ and uv)
uv sync

# Set required env vars
export FRESHRSS_URL="https://freshrss.example.com"
export FRESHRSS_USERNAME="youruser"
export FRESHRSS_PASSWORD="yourpass"

# Start server (binds to 127.0.0.1:8000/mcp by default)
uv run freshrss-mcp

# Override host/port
export MCP_SERVER_HOST="0.0.0.0"
export MCP_SERVER_PORT=3005
uv run freshrss-mcp
```

### Quick Start (NixOS)

```bash
# Enter dev shell (provides uv, python, ruff)
nix develop

# Install deps and run tests
uv sync
uv run pytest -v

# Start the server
export FRESHRSS_URL="https://freshrss.example.com"
export FRESHRSS_USERNAME="youruser"
export FRESHRSS_PASSWORD="yourpass"
uv run freshrss-mcp
```

On NixOS, the Nix devshell sets `UV_PYTHON_DOWNLOADS=never` and `UV_PYTHON` automatically to avoid dynamically linked binary issues.

### Verify the Server

```bash
# List tools via JSON-RPC
curl -s http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq .

# Call a tool
curl -s http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_feeds","arguments":{}}}' | jq .

# MCP Inspector (interactive)
npx @modelcontextprotocol/inspector --url http://127.0.0.1:8000/mcp
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FRESHRSS_URL` | Yes | — | FreshRSS instance URL |
| `FRESHRSS_USERNAME` | Yes | — | FreshRSS username |
| `FRESHRSS_PASSWORD` | Yes | — | FreshRSS API password |
| `FRESHRSS_API_PATH` | No | `/api/greader.php` | Google Reader API path |
| `MCP_SERVER_HOST` | No | `127.0.0.1` | Bind address |
| `MCP_SERVER_PORT` | No | `8000` | Bind port |

### Available Tools

| Tool | Description | Key Args |
|------|-------------|----------|
| `get_unread_articles` | Fetch unread articles with filtering | `limit`, `feed_ids`, `since_timestamp`, `max_summary_length` |
| `get_articles_by_feed` | Articles from a specific feed | `feed_id`, `limit`, `include_read` |
| `search_articles` | Client-side keyword search in titles/summaries | `query`, `limit`, `feed_ids` |
| `list_feeds` | All subscribed feeds with unread counts | — |
| `get_feed_info` | Detailed info for one feed | `feed_id` |
| `get_feed_stats` | Statistics for all feeds | — |
| `mark_as_read` | Batch mark articles as read | `article_ids` |
| `mark_as_unread` | Batch mark articles as unread | `article_ids` |
| `star_article` | Star/favorite an article | `article_id` |
| `unstar_article` | Remove star from an article | `article_id` |

### Architecture Notes

- **Transport**: Streamable HTTP (POST `/mcp`), not stdio. The OpenClaw `openclaw-mcp-bridge` plugin discovers tools via HTTP.
- **Auth**: Lazy authentication — the FreshRSS client authenticates on the first API call, not at startup.
- **Error handling**: Every tool catches all exceptions and returns `"Error: ..."` strings. MCP protocol never sees uncaught exceptions.
- **Config**: pydantic-settings `BaseSettings` with `SecretStr` for the password. Validation happens at startup.
- **Dependencies**: `fastmcp`, `httpx`, `pydantic-settings`. No version pins.
- **Tests**: 67 unit tests covering config, client, tools, and models. Run with `uv run pytest -v`.

### Project Structure

```
src/freshrss_mcp/
  server.py    — FastMCP entry point, signal handlers, streamable-http transport
  tools.py     — 10 MCP tool definitions with error boundaries
  client.py    — Async FreshRSS Google Reader API client (httpx)
  config.py    — pydantic-settings config from env vars
  models.py    — Article and Feed dataclasses
tests/
  test_config.py   — Config validation, defaults, secret masking
  test_client.py   — Auth, feeds, articles, ID extraction
  test_tools.py    — Tool happy paths + error boundaries
  test_models.py   — Serialization, construction, edge cases
```

## Known Limitations

- **Client-side search**: FreshRSS API lacks server-side search; `search_articles` fetches articles then filters locally.
- **No pagination**: Article fetches use a single `limit` parameter without cursor-based pagination.
- **No real-time updates**: The server is request-driven; no push/webhook mechanism for new articles.

## License

MIT
