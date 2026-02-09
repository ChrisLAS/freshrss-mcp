# FreshRSS MCP Server

> **For LLM Agents:** If you're reading this to deploy or work on this project, please see **[AGENTS.md](./freshrss-mcp-server/AGENTS.md)** for detailed deployment and development instructions.

A Model Context Protocol (MCP) server that integrates with FreshRSS, dramatically optimizing token usage when AI agents read RSS feeds. Instead of transmitting full RSS XML with all metadata, this server returns only essential fields with intelligent filtering and truncation.

## Why an MCP Server for FreshRSS?

### The Problem

When AI agents read RSS feeds directly, they face significant inefficiencies:

1. **Bloated XML Payloads**: Raw RSS XML contains repetitive metadata, CDATA sections, XML namespaces, and boilerplate that AI doesn't need
2. **No Server-Side Filtering**: Agents download entire feeds then filter locally, wasting tokens on already-read articles
3. **Redundant Content**: Full HTML articles, author bios, duplicate categories - all consume tokens unnecessarily
4. **Multiple Round-Trips**: To get unread counts, feed lists, and articles requires separate XML fetches
5. **No Incremental Updates**: Every request downloads the entire feed history

### Real-World Token Comparison

| Scenario | Raw RSS Approach | MCP Server Approach | Savings |
|----------|------------------|---------------------|---------|
| Get 20 unread articles | ~8,000-15,000 tokens | ~800-1,200 tokens | **~90%** |
| List all feeds | ~2,000-5,000 tokens | ~200-400 tokens | **~90%** |
| Search across feeds | ~20,000+ tokens | ~1,500-2,500 tokens | **~90%** |
| Mark articles read | Manual parsing + POST | Single tool call | **~95%** |

*Based on typical RSS feeds with 50-200 items and standard metadata*

### How We Achieve These Savings

#### 1. **Minimal Response Payloads**

We return only 7 essential fields per article:
```json
{
  "id": 12345,
  "title": "Article Title",
  "summary": "Brief excerpt...",
  "url": "https://example.com/article",
  "published": 1707312000,
  "feed_name": "Source Feed",
  "is_read": false,
  "is_starred": false
}
```

**Excluded bloat:**
- ❌ Full HTML content (use summary only)
- ❌ XML namespaces and CDATA
- ❌ Author email, website, bio
- ❌ Duplicate categories/tags
- ❌ Feed metadata repeated per item
- ❌ XML structure overhead

#### 2. **Server-Side Filtering**

Instead of downloading everything and filtering client-side:

```python
# Raw RSS approach (wasteful)
all_articles = fetch_all_feeds()  # 200 items, 10,000 tokens
unread = [a for a in all_articles if not a.read]  # AI processes all 200

# MCP approach (efficient)
unread = get_unread_articles(limit=20)  # 20 items, 1,000 tokens
```

FreshRSS tracks read/unread state server-side, so we only return what the AI needs.

#### 3. **Intelligent Summary Truncation**

Full articles can be 5,000-10,000 tokens. We truncate to configurable limits:

```python
# Default 500 characters, smart word-boundary truncation
summary = truncate(article.summary, max_length=500)
# "This is the beginning of a long article that..."
```

User can adjust per-request:
- `max_summary_length=200` for quick scanning
- `max_summary_length=1000` for detailed reading
- `max_summary_length=None` for full content (when needed)

#### 4. **Incremental Updates**

Track `since_timestamp` to fetch only new articles:

```python
# Only get articles published in last hour
new_articles = get_unread_articles(
    since_timestamp=1707312000,
    limit=50
)
```

#### 5. **Parallel Feed Aggregation**

Instead of fetching each feed separately:

```python
# MCP server aggregates multiple feeds server-side
articles = get_unread_articles(
    feed_ids=[123, 456, 789],  # 3 feeds
    limit=30
)
```

Single request, optimized payload.

## Features

- **🎯 Token Optimized**: 90%+ reduction vs raw RSS
- **📡 Real-time FreshRSS Integration**: Google Reader API compatibility
- **🔧 Complete MCP Toolset**: All CRUD operations for feeds and articles
- **🔒 NixOS Ready**: Production-grade deployment with systemd hardening
- **⚡ Async/Await**: Non-blocking I/O for concurrent clients
- **🧪 Well Tested**: 15 comprehensive tests

## Available MCP Tools

### Article Retrieval
- `get_unread_articles(limit, feed_ids, since_timestamp, max_summary_length)` - Get unread with filtering
- `get_articles_by_feed(feed_id, limit, include_read)` - Per-feed articles
- `search_articles(query, limit, feed_ids)` - Keyword search

### Feed Management
- `list_feeds()` - All subscriptions with unread counts
- `get_feed_info(feed_id)` - Detailed feed information
- `get_feed_stats()` - Statistics for all feeds

### Article Management
- `mark_as_read(article_ids)` - Batch mark read
- `mark_as_unread(article_ids)` - Batch mark unread
- `star_article(article_id)` - Star/favorite
- `unstar_article(article_id)` - Remove star

## NixOS Installation

### Prerequisites

- NixOS with flakes enabled
- Git
- FreshRSS account with API access enabled
- Password stored in `~/.config/secrets/freshrss-mcp`

### Step 1: Clone Repository

```bash
git clone https://github.com/ChrisLAS/freshrss-mcp.git
cd freshrss-mcp
```

### Step 2: Create Secrets File

Create the password file (outside of git):

```bash
mkdir -p ~/.config/secrets
echo "FRESHRSS_PASSWORD=your_password_here" > ~/.config/secrets/freshrss-mcp
chmod 600 ~/.config/secrets/freshrss-mcp
```

### Step 3: Add to Your Flake

Add to your `flake.nix`:

```nix
{
  inputs.freshrss-mcp = {
    url = "github:ChrisLAS/freshrss-mcp";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, freshrss-mcp, ... }@inputs: {
    nixosConfigurations.your-host = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      specialArgs = { inherit inputs; };
      modules = [
        # Import the module
        freshrss-mcp.nixosModules.default
        
        # Your configuration
        ({ config, pkgs, ... }: {
          services.freshrss-mcp-server = {
            enable = true;
            freshRssUrl = "https://freshrss.trailertrash.io";
            username = "chrisf";
            passwordFile = "/home/chrisf/.config/secrets/freshrss-mcp";
            port = 3004;
            host = "127.0.0.1";  # localhost only (recommended)
            openFirewall = false;
          };
          
          # Optional: Nginx reverse proxy for external access
          services.nginx = {
            enable = true;
            virtualHosts."freshrss-mcp.local" = {
              locations."/" = {
                proxyPass = "http://127.0.0.1:3004";
                proxyWebsockets = true;
              };
            };
          };
        })
      ];
    };
  };
}
```

### Step 4: Rebuild NixOS

```bash
sudo nixos-rebuild switch --flake .#your-host
```

### Step 5: Verify Installation

```bash
# Check service is running
systemctl status freshrss-mcp-server

# View logs
journalctl -u freshrss-mcp-server -f

# Test connection
curl http://127.0.0.1:3004/mcp
```

## Development

### Using Nix (Recommended)

```bash
# Enter development shell
nix develop

# Install dependencies
uv sync

# Run tests
uv run pytest

# Run server locally
export FRESHRSS_URL="https://freshrss.trailertrash.io"
export FRESHRSS_USERNAME="chrisf"
export FRESHRSS_PASSWORD="your_password"
uv run freshrss-mcp-server
```

### Without Nix

Requires Python 3.11+ and `uv`:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run tests
uv run pytest
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `FRESHRSS_URL` | Required | FreshRSS instance URL |
| `FRESHRSS_USERNAME` | Required | FreshRSS username |
| `FRESHRSS_PASSWORD` | Required | FreshRSS password |
| `FRESHRSS_API_PATH` | `/api/greader.php` | API endpoint path |
| `MCP_SERVER_PORT` | `3004` | Server port |
| `MCP_SERVER_HOST` | `0.0.0.0` | Server host |
| `DEFAULT_ARTICLE_LIMIT` | `20` | Default articles per request |
| `DEFAULT_SUMMARY_LENGTH` | `500` | Default summary truncation |

## Architecture

See [ARCHITECTURE.md](./freshrss-mcp-server/ARCHITECTURE.md) for detailed design documentation.

## Testing

```bash
# Run all tests
uv run pytest -v

# Run with coverage
uv run pytest --cov=freshrss_mcp_server

# Lint code
uv run ruff check .

# Format code
uv run ruff format .
```

## Security

- ✅ **No secrets in Nix store**: Password loaded from file at runtime
- ✅ **Systemd hardening**: Dynamic user, ProtectSystem, PrivateTmp, etc.
- ✅ **Localhost by default**: Not exposed to network unless configured
- ✅ **Automatic restarts**: Service recovers from failures

## License

MIT License - See LICENSE file for details

## Contributing

This project uses [beads](https://github.com/anomalyco/beads) for task tracking. Run `bd ready` to see available work.

---

**For LLM Agents:** See [AGENTS.md](./freshrss-mcp-server/AGENTS.md) for detailed deployment instructions.
