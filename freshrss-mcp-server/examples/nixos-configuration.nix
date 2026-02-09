# NixOS Configuration Example

To deploy FreshRSS MCP Server on your NixOS system, add this to your configuration:

## Flake Input

```nix
{
  inputs.freshrss-mcp-server = {
    url = "path:/path/to/freshrss-mcp-server";  # Or git repository URL
    # url = "github:yourusername/freshrss-mcp-server";
  };

  outputs = { self, nixpkgs, freshrss-mcp-server, ... }@inputs: {
    nixosConfigurations.yourhostname = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      specialArgs = { inherit inputs; };
      modules = [
        # Import the module
        freshrss-mcp-server.nixosModules.default
        
        # Your configuration
        ({ config, pkgs, ... }: {
          # Enable the service
          services.freshrss-mcp-server = {
            enable = true;
            
            # FreshRSS connection settings
            freshRssUrl = "https://freshrss.trailertrash.io";
            username = "chrisf";
            
            # Use agenix or sops-nix for secrets
            passwordFile = config.age.secrets.freshrss-password.path;
            # Or: passwordFile = "/run/secrets/freshrss-password";
            
            # Server settings
            port = 3004;
            host = "127.0.0.1";  # Use localhost for reverse proxy
            
            # Open firewall (only if not using reverse proxy)
            openFirewall = false;
          };
          
          # Optional: Reverse proxy with nginx
          services.nginx = {
            enable = true;
            virtualHosts."freshrss-mcp.yourdomain.com" = {
              forceSSL = true;
              enableACME = true;
              locations."/" = {
                proxyPass = "http://127.0.0.1:3004";
                proxyWebsockets = true;
              };
            };
          };
          
          # Firewall
          networking.firewall.allowedTCPPorts = [ 80 443 ];
        })
      ];
    };
  };
}
```

## Using agenix for Secrets

Create `secrets/freshrss-password.age`:

```nix
# secrets.nix
{
  "freshrss-password.age".publicKeys = [ your-ssh-key ];
}
```

Create the secret file with your password, then in your system configuration:

```nix
age.secrets.freshrss-password = {
  file = ./secrets/freshrss-password.age;
  owner = "freshrss-mcp-server";
  group = "freshrss-mcp-server";
};
```

## Using sops-nix for Secrets

```nix
sops.secrets.freshrss-password = {
  sopsFile = ./secrets.yaml;
  owner = "freshrss-mcp-server";
};
```

## Systemd Service Details

The service runs with these security hardening features:
- DynamicUser (no permanent user created)
- PrivateTmp
- ProtectSystem = "strict"
- ProtectHome = true
- NoNewPrivileges
- PrivateDevices
- SystemCallFilter = "@system-service"
- And more...

## Viewing Logs

```bash
# View service logs
journalctl -u freshrss-mcp-server -f

# Check service status
systemctl status freshrss-mcp-server
```

## Testing the Server

Once deployed, test with curl:

```bash
# The server uses MCP protocol, so you'll need an MCP client
# Here's a simple test using the example client:
nix run .#client-example
```
