# FreshRSS MCP Server

A Model Context Protocol (MCP) server that integrates with FreshRSS, optimized for token efficiency when used by AI agents to retrieve and manage RSS feed articles.

## Features

- **Token Optimized**: Returns only essential fields with configurable summary truncation
- **Complete MCP Tools**: All tools for reading, searching, and managing articles
- **FreshRSS Integration**: Uses Google Reader API for compatibility
- **NixOS Ready**: Full Nix flake with devShell and NixOS module

## Quick Start

### Using uv (Development)

```bash
# Enter development shell
nix develop

# Install dependencies
uv sync

# Set environment variables
export FRESHRSS_URL="https://freshrss.example.com"
export FRESHRSS_USERNAME="your_username"
export FRESHRSS_PASSWORD="your_password"

# Run the server
uv run freshrss-mcp-server
```

### Using Nix

```bash
# Run directly
nix run

# Or install
nix profile install
```

## Configuration

Environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FRESHRSS_URL` | Yes | - | FreshRSS instance URL |
| `FRESHRSS_USERNAME` | Yes | - | FreshRSS username |
| `FRESHRSS_PASSWORD` | Yes | - | FreshRSS password |
| `FRESHRSS_API_PATH` | No | `/api/greader.php` | API endpoint path |
| `MCP_SERVER_PORT` | No | `3004` | Server port |
| `MCP_SERVER_HOST` | No | `0.0.0.0` | Server host |
| `DEFAULT_ARTICLE_LIMIT` | No | `20` | Default article limit |
| `DEFAULT_SUMMARY_LENGTH` | No | `500` | Default summary length |

## MCP Tools

### Article Retrieval

- `get_unread_articles(limit, feed_ids, since_timestamp, max_summary_length)` - Get unread articles
- `get_articles_by_feed(feed_id, limit, include_read)` - Get articles from specific feed
- `search_articles(query, limit, feed_ids)` - Search articles by keyword

### Feed Management

- `list_feeds()` - List all feeds with unread counts
- `get_feed_info(feed_id)` - Get detailed feed information
- `get_feed_stats()` - Get statistics for all feeds

### Article Management

- `mark_as_read(article_ids)` - Mark articles as read
- `mark_as_unread(article_ids)` - Mark articles as unread
- `star_article(article_id)` - Star an article
- `unstar_article(article_id)` - Unstar an article

## NixOS Deployment

Add to your `configuration.nix`:

```nix
{
  inputs.freshrss-mcp-server.url = "path:/path/to/freshrss-mcp-server";
  
  outputs = { self, nixpkgs, freshrss-mcp-server, ... }: {
    nixosConfigurations.hostname = nixpkgs.lib.nixosSystem {
      modules = [
        freshrss-mcp-server.nixosModules.default
        {
          services.freshrss-mcp-server = {
            enable = true;
            freshRssUrl = "https://freshrss.trailertrash.io";
            username = "chrisf";
            passwordFile = "/run/secrets/freshrss-password";
            port = 3004;
            openFirewall = true;
          };
        }
      ];
    };
  };
}
```

## Development

```bash
# Enter dev shell
nix develop

# Run tests
uv run pytest

# Format code
ruff format .

# Check code
ruff check .
```

## License

MIT
