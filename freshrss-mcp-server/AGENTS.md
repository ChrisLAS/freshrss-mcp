# FreshRSS MCP Server - Agent Deployment Guide

**Target Audience:** LLM Agent deploying on NixOS  
**FreshRSS Instance:** https://freshrss.trailertrash.io  
**Username:** chrisf  
**Secrets Location:** `~/.config/secrets/`

## Quick Overview

This is an MCP (Model Context Protocol) server that connects to FreshRSS RSS aggregator. It exposes tools for AI agents to:
- Read unread RSS articles
- Search articles
- Mark articles as read/unread
- Star/unstar articles
- List feeds and get statistics

The server runs as a systemd service on NixOS, listening on port 3004 by default.

## Prerequisites

Before starting, verify:
- [ ] NixOS with flakes enabled (`nix flake --version` works)
- [ ] Git access to https://github.com/ChrisLAS/freshrss-mcp
- [ ] Password for chrisf account on freshrss.trailertrash.io
- [ ] `~/.config/` directory exists (create if needed: `mkdir -p ~/.config/secrets`)

## Deployment Steps

### 1. Clone the Repository

```bash
cd ~
git clone https://github.com/ChrisLAS/freshrss-mcp.git
cd freshrss-mcp/freshrss-mcp-server
```

### 2. Create Secrets File

Create the password file at `~/.config/secrets/freshrss-mcp`:

```bash
# Create the secrets directory if it doesn't exist
mkdir -p ~/.config/secrets

# Create the file with the password
# Replace 'your_password_here' with the actual password
cat > ~/.config/secrets/freshrss-mcp << 'EOF'
FRESHRSS_PASSWORD=your_password_here
EOF

# Secure the file permissions
chmod 600 ~/.config/secrets/freshrss-mcp
```

**⚠️ Important:** The file should ONLY contain `FRESHRSS_PASSWORD=...` on one line. No quotes around the password unless the password itself contains special characters.

### 3. Add to NixOS Configuration

Add this to your NixOS `configuration.nix` or flake:

```nix
{ config, pkgs, inputs, ... }:

{
  # Import the freshrss-mcp module
  imports = [
    inputs.freshrss-mcp.nixosModules.default
  ];

  # Configure the service
  services.freshrss-mcp-server = {
    enable = true;
    freshRssUrl = "https://freshrss.trailertrash.io";
    username = "chrisf";
    passwordFile = "/home/chrisf/.config/secrets/freshrss-mcp";
    port = 3004;
    host = "127.0.0.1";  # localhost only, use nginx for external access
    openFirewall = false;  # Set to true only if not using reverse proxy
  };

  # Optional: Nginx reverse proxy (recommended for security)
  services.nginx = {
    enable = true;
    virtualHosts."freshrss-mcp.local" = {
      locations."/" = {
        proxyPass = "http://127.0.0.1:3004";
        proxyWebsockets = true;
      };
    };
  };
}
```

If using a flake, add this to your flake inputs:

```nix
{
  inputs.freshrss-mcp = {
    url = "github:ChrisLAS/freshrss-mcp";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, freshrss-mcp, ... }@inputs: {
    # ... your config
  };
}
```

### 4. Rebuild NixOS

```bash
sudo nixos-rebuild switch --flake .#your-hostname
```

Or if not using flakes:

```bash
sudo nixos-rebuild switch
```

### 5. Verify Deployment

Check that the service is running:

```bash
# Check service status
systemctl status freshrss-mcp-server

# View recent logs
journalctl -u freshrss-mcp-server -n 50

# Follow logs in real-time
journalctl -u freshrss-mcp-server -f
```

Test the server:

```bash
# The server uses MCP protocol over HTTP
# You can check if it's listening
curl http://127.0.0.1:3004/mcp

# Should return MCP protocol info or similar
```

## Configuration Reference

### Environment Variables (set automatically by NixOS module)

- `FRESHRSS_URL` - FreshRSS instance URL
- `FRESHRSS_USERNAME` - Username for authentication
- `FRESHRSS_PASSWORD` - Loaded from passwordFile
- `FRESHRSS_API_PATH` - API endpoint (default: /api/greader.php)
- `MCP_SERVER_PORT` - Port to listen on (default: 3004)
- `MCP_SERVER_HOST` - Host to bind to (default: 0.0.0.0)
- `DEFAULT_ARTICLE_LIMIT` - Default articles per request (default: 20)
- `DEFAULT_SUMMARY_LENGTH` - Default summary truncation (default: 500)

### Secrets File Format

File: `~/.config/secrets/freshrss-mcp`

```
FRESHRSS_PASSWORD=your_actual_password_here
```

- One line only
- No quotes unless password contains spaces
- File permissions should be 600 (rw-------)

## Troubleshooting

### Service fails to start

```bash
# Check logs for errors
journalctl -u freshrss-mcp-server -n 100 --no-pager

# Common issues:
# - Password file not found (check path)
# - Permission denied on password file (chmod 600)
# - Wrong password (check freshrss.trailertrash.io login)
# - FreshRSS API not enabled (check FreshRSS settings)
```

### Authentication failures

```bash
# Test FreshRSS login manually
curl -X POST https://freshrss.trailertrash.io/api/greader.php/accounts/ClientLogin \
  -d "Email=chrisf" \
  -d "Passwd=your_password"

# Should return SID=... if successful
```

### Permission denied on secrets file

```bash
# Fix permissions
chmod 600 ~/.config/secrets/freshrss-mcp
chown chrisf:chrisf ~/.config/secrets/freshrss-mcp

# Verify
ls -la ~/.config/secrets/freshrss-mcp
# Should show: -rw------- 1 chrisf chrisf
```

### Service not accessible

If using `host = "127.0.0.1"` (recommended), the service only listens on localhost:

```bash
# This works (from same machine)
curl http://127.0.0.1:3004/mcp

# This fails (from other machines)
curl http://your-server-ip:3004/mcp

# To allow external access, either:
# 1. Change host to "0.0.0.0" (less secure)
# 2. Use nginx reverse proxy (recommended)
```

## Available MCP Tools

Once deployed, the server exposes these tools:

1. **get_unread_articles** - Get unread articles (with filtering)
2. **get_articles_by_feed** - Get articles from specific feed
3. **search_articles** - Search by keyword
4. **list_feeds** - List all subscriptions
5. **get_feed_info** - Get feed details
6. **get_feed_stats** - Get statistics
7. **mark_as_read** - Mark articles read
8. **mark_as_unread** - Mark articles unread
9. **star_article** - Star an article
10. **unstar_article** - Unstar an article

## Next Steps

After successful deployment:

1. **Connect an MCP client** (like Claude Code, Cline, etc.)
2. **Configure the client** to connect to `http://127.0.0.1:3004/mcp`
3. **Test with a simple query**: "What are my unread RSS articles?"

## Security Notes

- ✅ Service runs as dynamic user (no permanent system user)
- ✅ systemd hardening enabled (ProtectSystem, PrivateTmp, etc.)
- ✅ Password stored in file, not in Nix store
- ✅ Recommended: Use localhost + nginx, not exposed port
- ✅ Secrets file has restrictive permissions (600)

## Useful Commands

```bash
# Restart service
sudo systemctl restart freshrss-mcp-server

# Stop service
sudo systemctl stop freshrss-mcp-server

# Disable auto-start
sudo systemctl disable freshrss-mcp-server

# Re-enable
sudo systemctl enable freshrss-mcp-server

# Check for errors
systemctl status freshrss-mcp-server --no-pager

# View all logs since boot
journalctl -u freshrss-mcp-server --since "1 hour ago"
```

## Getting Help

If deployment fails:

1. Check this file for your specific error in Troubleshooting
2. Review logs: `journalctl -u freshrss-mcp-server -n 100`
3. Verify FreshRSS API is enabled at freshrss.trailertrash.io
4. Test authentication manually (see Troubleshooting section)

## Beads Task Tracking

This project uses beads for task tracking. To see deployment status:

```bash
# From project root
cd ~/freshrss-mcp

# Check ready tasks
bd ready

# View all tasks
bd list

# Check specific task
bd show <task-id>
```

**Current Status:** All implementation phases complete. Deployment is the final step.

---

**Last Updated:** 2026-02-08  
**Version:** 0.1.0  
**Repository:** https://github.com/ChrisLAS/freshrss-mcp
