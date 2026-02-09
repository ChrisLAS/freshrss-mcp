# FreshRSS MCP Server Development Prompt

## Objective
Build a Model Context Protocol (MCP) server that integrates with FreshRSS, optimized for token efficiency when used by AI agents to retrieve and manage RSS feed articles.

## Core Requirements

### 1. Technology Stack
- **Language**: Python 3.11+
- **Package Manager**: uv (Astral's fast Python package manager)
  - Native support for `pyproject.toml` and lockfiles
  - Excellent NixOS integration (simpler than Poetry)
  - Fast dependency resolution and installation
  - Compatible with pip and standard Python tooling
- **Framework**: Use `mcp` Python SDK for MCP server implementation
- **HTTP Server**: Expose MCP over HTTP on port 3004
- **FreshRSS API**: Integrate with Google Reader API (compatible with FreshRSS)
- **NixOS**: Follow NixOS best practices for packaging and deployment

### 2. Token Optimization (Critical Priority)
The primary goal is to minimize token usage when AI agents interact with RSS feeds:

- **Minimal Response Payloads**: Return only essential fields (id, title, summary, url, published_date, feed_name, read_status)
- **Server-Side Filtering**: Implement filters (unread only, by feed, by date range, by keyword) to reduce data transfer
- **Incremental Updates**: Track and return only new/changed articles since last fetch
- **Deduplication**: Remove duplicate articles across feeds server-side
- **Configurable Limits**: Allow limiting number of articles returned per request
- **Summary Truncation**: Option to truncate article summaries to N characters
- **Exclude Read Articles**: Default to returning unread only unless explicitly requested

### 3. MCP Tools to Implement

Expose the following MCP tools:

```python
# Article Retrieval
get_unread_articles(
    limit: int = 20,
    feed_ids: list[int] | None = None,
    since_timestamp: int | None = None,
    max_summary_length: int | None = 500
) -> list[Article]

get_articles_by_feed(
    feed_id: int,
    limit: int = 20,
    include_read: bool = False
) -> list[Article]

search_articles(
    query: str,
    limit: int = 10,
    feed_ids: list[int] | None = None
) -> list[Article]

# Feed Management
list_feeds() -> list[Feed]

get_feed_info(feed_id: int) -> Feed

# Article Management
mark_as_read(article_ids: list[int]) -> bool

mark_as_unread(article_ids: list[int]) -> bool

star_article(article_id: int) -> bool

unstar_article(article_id: int) -> bool

# Stats (useful for prioritization)
get_feed_stats() -> dict[int, FeedStats]  # unread_count, last_updated, etc.
```

### 4. Data Models

Define minimal, token-efficient data structures:

```python
@dataclass
class Article:
    id: int
    title: str
    summary: str  # truncated if max_summary_length set
    url: str
    published: int  # Unix timestamp
    feed_name: str
    is_read: bool
    is_starred: bool

@dataclass
class Feed:
    id: int
    name: str
    url: str
    unread_count: int
    
@dataclass
class FeedStats:
    feed_id: int
    feed_name: str
    unread_count: int
    total_count: int
    last_updated: int  # Unix timestamp
```

### 5. Configuration

Support configuration via environment variables and/or config file:

```bash
FRESHRSS_URL=http://localhost:8080
FRESHRSS_USERNAME=admin
FRESHRSS_PASSWORD=secret
FRESHRSS_API_PATH=/api/greader.php
MCP_SERVER_PORT=3004
MCP_SERVER_HOST=0.0.0.0
DEFAULT_ARTICLE_LIMIT=20
DEFAULT_SUMMARY_LENGTH=500
CACHE_TTL=60  # seconds to cache feed metadata
```

### 6. FreshRSS API Integration

- Use FreshRSS Google Reader API compatibility
- Implement authentication (SID token-based)
- Handle common API endpoints:
  - `/api/greader.php/accounts/ClientLogin` - Authentication
  - `/api/greader.php/reader/api/0/subscription/list` - List feeds
  - `/api/greader.php/reader/api/0/stream/contents/` - Get articles
  - `/api/greader.php/reader/api/0/edit-tag` - Mark read/starred
  - `/api/greader.php/reader/api/0/unread-count` - Get unread counts

### 7. Error Handling & Logging

- Structured logging using Python `logging` module
- Graceful degradation if FreshRSS is unavailable
- Clear error messages returned via MCP
- Retry logic for transient FreshRSS API failures

### 8. Integration Testing

Create comprehensive integration tests:

- Mock FreshRSS API responses
- Test all MCP tools with various parameters
- Test token optimization (measure response payload sizes)
- Test error conditions (auth failure, network errors, malformed responses)
- Test caching behavior
- Use `pytest` with `pytest-asyncio` for async tests

### 9. NixOS Packaging (Nix Flake)

Create a production-ready Nix flake following best practices:

**Required components:**
- `flake.nix` with:
  - `packages.default`: The MCP server package
  - `apps.default`: Runnable application
  - `devShells.default`: Development environment with all dependencies (including uv)
  - `nixosModules.default`: NixOS module for system-wide deployment
  
**uv Integration:**
- Use `pkgs.uv` in devShell for development
- For package building, consider using `pkgs.python3Packages.buildPythonApplication` with uv-generated requirements
- Alternatively, use `uv export --format requirements-txt` to generate a requirements.txt for Nix
- Include `uv.lock` in the repository for reproducible builds
- The flake should work seamlessly with both `nix develop` (using uv) and `nix build` (pure Nix build)

**Example flake structure:**
```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            uv
            python311
          ];
          shellHook = ''
            export UV_PYTHON=${pkgs.python311}/bin/python
          '';
        };
      }
    );
}
```

**NixOS Module should provide:**
- `services.freshrss-mcp-server.enable`
- `services.freshrss-mcp-server.port`
- `services.freshrss-mcp-server.freshRssUrl`
- `services.freshrss-mcp-server.credentials` (via systemd credentials or agenix)
- Systemd service definition with proper hardening
- User/group creation
- Automatic service restart on failure

**Flake best practices:**
- Pin nixpkgs to a stable release
- Use `flake-utils` for multi-system support
- Proper dependency management via `uv2nix` or direct integration with uv
- Include `flake.lock` for reproducibility
- Add proper metadata (description, license, maintainers)
- Leverage uv's native Nix compatibility for simpler dependency management

**Systemd hardening:**
```nix
serviceConfig = {
  DynamicUser = true;
  PrivateTmp = true;
  ProtectSystem = "strict";
  ProtectHome = true;
  NoNewPrivileges = true;
  PrivateDevices = true;
  ProtectKernelTunables = true;
  ProtectControlGroups = true;
  RestrictSUIDSGID = true;
  LockPersonality = true;
  RestrictRealtime = true;
  SystemCallFilter = "@system-service";
  SystemCallArchitectures = "native";
};
```

### 10. Documentation

Include in the repository:

- `README.md` with:
  - Quick start guide (including uv setup: `uv sync`, `uv run`)
  - Configuration options
  - Example MCP client usage
  - Token optimization tips
  - Deployment instructions (NixOS and standalone)
  - Development setup with uv
  
- `ARCHITECTURE.md` explaining:
  - Token optimization strategies implemented
  - FreshRSS API integration details
  - Caching strategy
  - Why uv was chosen for NixOS compatibility
  
- `examples/` directory with:
  - Example MCP client code
  - Example NixOS configuration
  - Docker Compose setup for testing

### 11. Project Structure

```
freshrss-mcp-server/
├── flake.nix
├── flake.lock
├── pyproject.toml          # uv-managed dependencies
├── uv.lock                 # uv lockfile
├── .python-version         # Python version for uv
├── README.md
├── ARCHITECTURE.md
├── src/
│   └── freshrss_mcp_server/
│       ├── __init__.py
│       ├── __main__.py
│       ├── server.py           # MCP server implementation
│       ├── freshrss_client.py  # FreshRSS API client
│       ├── models.py           # Data models
│       ├── config.py           # Configuration management
│       └── utils.py            # Helper functions
├── tests/
│   ├── __init__.py
│   ├── test_server.py
│   ├── test_freshrss_client.py
│   ├── test_token_optimization.py
│   └── fixtures/
│       └── mock_responses.py
├── examples/
│   ├── client_example.py
│   ├── nixos-configuration.nix
│   └── docker-compose.yml
└── nixos/
    └── module.nix
```

### 12. Implementation Priorities

1. **Phase 1**: Core FreshRSS client with authentication
2. **Phase 2**: Basic MCP server with `get_unread_articles` and `mark_as_read`
3. **Phase 3**: Token optimization features (filtering, truncation, caching)
4. **Phase 4**: Complete all MCP tools
5. **Phase 5**: Integration tests
6. **Phase 6**: NixOS packaging and module
7. **Phase 7**: Documentation and examples

### 13. Success Criteria

- MCP server successfully exposes all specified tools
- Token usage reduced by at least 60% compared to raw RSS XML parsing
- All integration tests pass
- NixOS module deploys cleanly on NixOS 24.05+
- Development environment can be entered via `nix develop`
- Server can be run via `nix run`
- Clear documentation allows others to deploy and use the server

### 14. Additional Considerations

- **Performance**: Handle at least 100 req/sec on modest hardware
- **Memory**: Keep memory footprint under 100MB for typical usage
- **Concurrency**: Support multiple concurrent MCP clients
- **Observability**: Expose metrics (optional) via Prometheus endpoint
- **Security**: No hardcoded credentials, support for credential management

## Getting Started

1. Initialize Python project with uv (`uv init`)
2. Add MCP SDK and HTTP dependencies via `uv add`
3. Implement FreshRSS authentication
4. Build core MCP tools incrementally
5. Add tests as you go (use `uv run pytest`)
6. Create Nix flake after core functionality works
7. Iterate on token optimization

## Questions to Address

- Should articles be cached in-memory or always fetched fresh?
- What's the optimal default for `max_summary_length`?
- Should there be a tool for batch operations (mark multiple articles)?
- Do we need webhook support for real-time updates?

Please implement this server following the requirements above, with special attention to token optimization and NixOS best practices.
