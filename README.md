# FreshRSS MCP Server

An MCP server that wraps the FreshRSS Google Reader API, exposing RSS feed management as tools for AI agents. Uses **Streamable HTTP** transport for integration with the OpenClaw gateway via the `openclaw-mcp-bridge` plugin.

Token-optimized: returns only essential fields with configurable summary truncation, achieving ~90% reduction vs raw RSS XML payloads.

## Tools

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

## Configuration

All configuration comes from environment variables. Missing required vars produce a clear error at startup.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FRESHRSS_URL` | Yes | — | FreshRSS instance URL (e.g. `https://freshrss.example.com`) |
| `FRESHRSS_USERNAME` | Yes | — | FreshRSS username |
| `FRESHRSS_PASSWORD` | Yes | — | FreshRSS password (API password) |
| `FRESHRSS_API_PATH` | No | `/api/greader.php` | Google Reader API endpoint path |
| `MCP_SERVER_HOST` | No | `127.0.0.1` | Host to bind the HTTP server to |
| `MCP_SERVER_PORT` | No | `8000` | Port for the HTTP server |

## OpenClaw Registration

The server runs as a persistent HTTP service. Register it in the `openclaw-mcp-bridge` plugin config inside `~/.openclaw/openclaw.json`:

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
              "url": "http://127.0.0.1:8000",
              "prefix": "freshrss",
              "tokenFile": "/home/you/.config/secrets/freshrss-mcp-token"
            }
          ]
        }
      }
    }
  }
}
```

Then restart the gateway: `openclaw gateway restart`.

Tools will appear as `freshrss_get_unread_articles`, `freshrss_list_feeds`, etc.

## Development Setup

### With Nix (recommended)

```bash
nix develop
uv sync
uv run pytest -v
```

### Without Nix

Requires Python 3.12+ and `uv`. On NixOS, set `UV_PYTHON_DOWNLOADS=never`.

```bash
uv sync
uv run pytest -v
uv run freshrss-mcp  # starts the server
```

### Running the Server

```bash
export FRESHRSS_URL="https://freshrss.example.com"
export FRESHRSS_USERNAME="youruser"
export FRESHRSS_PASSWORD="yourpass"
uv run freshrss-mcp
```

The server binds to `127.0.0.1:8000` by default and serves MCP over Streamable HTTP at `/mcp`.

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector --url http://127.0.0.1:8000/mcp
```

## Known Limitations

- **Client-side search**: FreshRSS API lacks server-side search; `search_articles` fetches articles then filters locally.
- **No pagination**: Article fetches use a single `limit` parameter without cursor-based pagination.
- **Auth on every startup**: The FreshRSS client authenticates once at server start. If the token expires during a long-running session, the server must be restarted.
- **No real-time updates**: The server is request-driven; there is no push/webhook mechanism for new articles.

## License

MIT
