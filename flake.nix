{
  description = "FreshRSS MCP Server — Streamable HTTP transport for OpenClaw";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.uv
            pkgs.python313
            pkgs.ruff
          ];

          env = {
            UV_PYTHON_DOWNLOADS = "never";
            UV_PYTHON = "${pkgs.python313}/bin/python3.13";
          };

          shellHook = ''
            echo "FreshRSS MCP Server dev shell"
            echo "  uv sync          — install deps"
            echo "  uv run pytest    — run tests"
            echo "  uv run freshrss-mcp — start server"
          '';
        };
      }
    )
    // {
      nixosModules.default =
        {
          config,
          lib,
          pkgs,
          ...
        }:
        with lib;
        let
          cfg = config.services.freshrss-mcp-server;
        in
        {
          options.services.freshrss-mcp-server = {
            enable = mkEnableOption "FreshRSS MCP Server";

            port = mkOption {
              type = types.port;
              default = 8765;
              description = "Port for the Streamable HTTP transport";
            };

            host = mkOption {
              type = types.str;
              default = "127.0.0.1";
              description = "Host to bind to";
            };

            freshRssUrl = mkOption {
              type = types.str;
              description = "URL of FreshRSS instance";
              example = "https://freshrss.example.com";
            };

            username = mkOption {
              type = types.str;
              description = "FreshRSS username";
            };

            passwordFile = mkOption {
              type = types.path;
              description = "Path to env file containing FRESHRSS_PASSWORD=<value>";
            };

            apiPath = mkOption {
              type = types.str;
              default = "/api/greader.php";
              description = "FreshRSS API path";
            };

            openFirewall = mkOption {
              type = types.bool;
              default = false;
              description = "Whether to open the firewall for the server port";
            };

            srcDir = mkOption {
              type = types.path;
              default = self;
              description = "Path to the freshrss-mcp source directory";
            };
          };

          config = mkIf cfg.enable {
            systemd.services.freshrss-mcp-server = {
              description = "FreshRSS MCP Server (Streamable HTTP)";
              after = [ "network.target" ];
              wantedBy = [ "multi-user.target" ];

              serviceConfig = {
                Type = "simple";
                ExecStart = "${pkgs.uv}/bin/uv run --directory ${cfg.srcDir} freshrss-mcp";

                Environment = [
                  "FRESHRSS_URL=${cfg.freshRssUrl}"
                  "FRESHRSS_USERNAME=${cfg.username}"
                  "FRESHRSS_API_PATH=${cfg.apiPath}"
                  "MCP_SERVER_PORT=${toString cfg.port}"
                  "MCP_SERVER_HOST=${cfg.host}"
                  "UV_PYTHON_DOWNLOADS=never"
                  "UV_PYTHON=${pkgs.python313}/bin/python3.13"
                ];

                EnvironmentFile = cfg.passwordFile;

                DynamicUser = true;
                PrivateTmp = true;
                ProtectSystem = "strict";
                ProtectHome = "read-only";
                NoNewPrivileges = true;
                PrivateDevices = true;
                ProtectKernelTunables = true;
                ProtectControlGroups = true;
                RestrictSUIDSGID = true;
                RestrictRealtime = true;
                SystemCallFilter = "@system-service";
                SystemCallArchitectures = "native";

                Restart = "on-failure";
                RestartSec = 5;
                TimeoutStopSec = 10;
                KillSignal = "SIGINT";
              };
            };

            networking.firewall.allowedTCPPorts = mkIf cfg.openFirewall [ cfg.port ];
          };
        };
    };
}
