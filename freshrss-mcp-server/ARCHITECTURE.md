# FreshRSS MCP Server Architecture

## Overview

FreshRSS MCP Server is a Model Context Protocol (MCP) implementation that bridges FreshRSS RSS aggregator with AI agents. It provides a token-optimized interface for retrieving and managing RSS articles.

## Design Goals

1. **Token Efficiency**: Minimize data transfer by returning only essential fields
2. **FreshRSS Compatibility**: Use Google Reader API for maximum compatibility
3. **NixOS Integration**: First-class support for NixOS deployment
4. **Developer Experience**: Simple setup with `uv` and clear documentation

## Architecture Components

### 1. FreshRSS Client (`freshrss_client.py`)

The client layer handles all communication with FreshRSS using the Google Reader API:

- **Authentication**: SID token-based authentication via `/accounts/ClientLogin`
- **Feed Management**: List subscriptions, get unread counts
- **Article Operations**: Fetch, mark read/unread, star/unstar
- **ID Extraction**: Parse Google Reader format IDs (numeric and string-based)

Key design decisions:
- Async/await for non-blocking I/O
- httpx for HTTP client (modern, async-capable)
- Automatic token management
- Graceful error handling with custom `AuthenticationError`

### 2. MCP Server (`server.py`)

The server layer exposes FreshRSS functionality via MCP tools:

**Article Retrieval Tools:**
- `get_unread_articles`: Fetch unread articles with filtering
- `get_articles_by_feed`: Get articles from specific feed
- `search_articles`: Client-side keyword search

**Feed Management Tools:**
- `list_feeds`: List all subscriptions with unread counts
- `get_feed_info`: Detailed feed information
- `get_feed_stats`: Statistics for all feeds

**Article Management Tools:**
- `mark_as_read/unread`: Batch read status updates
- `star_article/unstar_article`: Favorite articles

Key design decisions:
- FastMCP from `mcp` package for clean tool registration
- Tools use type hints for automatic schema generation
- Consistent error handling and client lifecycle management

### 3. Data Models (`models.py`)

Token-optimized dataclasses for minimal payload size:

```python
Article: id, title, summary, url, published, feed_name, is_read, is_starred
Feed: id, name, url, unread_count
FeedStats: feed_id, feed_name, unread_count, total_count, last_updated
```

Each model has:
- Type-safe fields
- `to_dict()` method for JSON serialization
- Minimal required fields (no bloated metadata)

### 4. Configuration (`config.py`)

Environment-based configuration:

```python
Config.from_env()  # Loads from environment variables
```

Required: `FRESHRSS_URL`, `FRESHRSS_USERNAME`, `FRESHRSS_PASSWORD`
Optional: API path, port, host, defaults for limits

Design decisions:
- No config files (12-factor app approach)
- Clear error messages for missing vars
- Type conversion handled automatically

## Token Optimization Strategies

### 1. Minimal Response Payloads

Only essential fields are returned:
- No HTML content (use summary only)
- No metadata like author, tags (unless needed)
- Unix timestamps instead of ISO strings (smaller)
- Feed name instead of full feed object

### 2. Server-Side Filtering

- `include_read=False` by default (only unread)
- `since_timestamp` for incremental updates
- `feed_ids` for targeted fetching
- Configurable `limit` parameter

### 3. Summary Truncation

Default 500 character limit with smart truncation:
- Truncates at word boundaries
- Adds "..." ellipsis
- Configurable via `max_summary_length` parameter

### 4. No Client-Side Aggregation

FreshRSS API returns pre-aggregated data:
- Unread counts from dedicated endpoint
- No need to count articles client-side
- Reduces response processing time

## NixOS Integration

### Flake Structure

```
flake.nix
├── packages.default    # Build the Python application
├── apps.default        # Run the server
├── devShells.default   # Development environment with uv
└── nixosModules.default # System service module
```

### Why uv?

- Faster than Poetry (written in Rust)
- Native `pyproject.toml` support
- Lockfile for reproducible builds
- Simple Nix integration
- Single binary (easy to include in devShell)

### NixOS Module Features

- Systemd service with auto-restart
- Security hardening (DynamicUser, ProtectSystem, etc.)
- Secret management via `passwordFile` (supports agenix/sops-nix)
- Firewall configuration option
- Configurable via NixOS options

## Testing Strategy

### Unit Tests (`test_models.py`)

- Model instantiation and serialization
- Configuration loading
- Error handling for missing env vars

### Integration Tests (`test_freshrss_client.py`)

- Mocked HTTP responses
- Authentication flow
- All API operations
- ID extraction utilities

No live FreshRSS instance required for tests.

## Security Considerations

1. **No Hardcoded Secrets**: All credentials via environment
2. **NixOS Password File**: Use systemd credentials or secret managers
3. **Systemd Hardening**: Dynamic user, no home access, restricted syscalls
4. **HTTPS Only**: FreshRSS URL should use HTTPS in production
5. **Token Management**: Auth tokens not persisted to disk

## Performance Characteristics

- **Response Time**: <100ms for typical operations (local FreshRSS)
- **Memory Usage**: <50MB typical (no caching)
- **Concurrency**: Supports multiple simultaneous MCP clients
- **Scalability**: Limited by FreshRSS API rate limits

## Future Improvements

1. **WebSocket Support**: Real-time article updates
2. **Caching Layer**: Optional Redis/memory for feed metadata
3. **Metrics**: Prometheus endpoint for monitoring
4. **Full-Text Search**: Integration with FreshRSS search API
5. **Batch Operations**: More efficient bulk mark-read operations

## Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| HTTP Client | httpx | Async support, modern API |
| MCP Framework | mcp (FastMCP) | Official SDK, decorator-based |
| Python | 3.11+ | Type hints, async improvements |
| Package Manager | uv | Fast, Nix-friendly |
| Testing | pytest | Industry standard |
| Deployment | NixOS | Declarative, reproducible |

## File Organization

```
freshrss-mcp-server/
├── src/freshrss_mcp_server/  # Main package
├── tests/                     # Test files
├── examples/                  # Usage examples
├── flake.nix                  # Nix configuration
├── pyproject.toml             # uv/Python config
└── README.md                  # User documentation
```

## Conclusion

FreshRSS MCP Server follows modern Python best practices with a focus on:
- Token efficiency for AI agent workflows
- Clean separation of concerns
- NixOS-first deployment
- Comprehensive testing
- Clear documentation

The architecture is intentionally simple to maintain reliability while providing all necessary functionality for RSS-based AI workflows.
