{
  description = "FreshRSS MCP Server - Model Context Protocol integration for FreshRSS";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
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
        python = pkgs.python311;

        # Build the package
        freshrss-mcp-server = pkgs.python311Packages.buildPythonApplication {
          pname = "freshrss-mcp-server";
          version = "0.1.0";
          pyproject = true;

          src = ./.;

          nativeBuildInputs = with pkgs.python311Packages; [
            hatchling
          ];

          propagatedBuildInputs = with pkgs.python311Packages; [
            mcp
            httpx
            pydantic
          ];

          meta = with pkgs.lib; {
            description = "MCP server for FreshRSS integration";
            license = licenses.mit;
            maintainers = [ ];
          };
        };
      in
      {
        packages = {
          default = freshrss-mcp-server;
          freshrss-mcp-server = freshrss-mcp-server;
        };

        apps = {
          default = {
            type = "app";
            program = "${freshrss-mcp-server}/bin/freshrss-mcp-server";
          };
        };

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            uv
            python311
            ruff
          ];

          shellHook = ''
            echo "FreshRSS MCP Server development environment"
            echo "Run 'uv sync' to install dependencies"
            echo "Run 'uv run freshrss-mcp-server' to start the server"
          '';
        };
      }
    )
    // {
      # NixOS module
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
          python = pkgs.python311;

          freshrss-mcp-server = pkgs.python311Packages.buildPythonApplication {
            pname = "freshrss-mcp-server";
            version = "0.1.0";
            pyproject = true;
            src = ./.;
            nativeBuildInputs = with pkgs.python311Packages; [ hatchling ];
            propagatedBuildInputs = with pkgs.python311Packages; [
              mcp
              httpx
              pydantic
            ];
          };
        in
        {
          options.services.freshrss-mcp-server = {
            enable = mkEnableOption "FreshRSS MCP Server";

            port = mkOption {
              type = types.port;
              default = 3004;
              description = "Port to listen on";
            };

            host = mkOption {
              type = types.str;
              default = "0.0.0.0";
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
              description = "Path to file containing FreshRSS password";
            };

            apiPath = mkOption {
              type = types.str;
              default = "/api/greader.php";
              description = "FreshRSS API path";
            };

            defaultArticleLimit = mkOption {
              type = types.int;
              default = 20;
              description = "Default number of articles to return";
            };

            defaultSummaryLength = mkOption {
              type = types.int;
              default = 500;
              description = "Default maximum summary length";
            };

            openFirewall = mkOption {
              type = types.bool;
              default = false;
              description = "Whether to open the firewall for the server port";
            };
          };

          config = mkIf cfg.enable {
            systemd.services.freshrss-mcp-server = {
              description = "FreshRSS MCP Server";
              after = [ "network.target" ];
              wantedBy = [ "multi-user.target" ];

              serviceConfig = {
                Type = "simple";
                ExecStart = "${freshrss-mcp-server}/bin/freshrss-mcp-server";

                # Environment variables
                Environment = [
                  "FRESHRSS_URL=${cfg.freshRssUrl}"
                  "FRESHRSS_USERNAME=${cfg.username}"
                  "FRESHRSS_API_PATH=${cfg.apiPath}"
                  "MCP_SERVER_PORT=${toString cfg.port}"
                  "MCP_SERVER_HOST=${cfg.host}"
                  "DEFAULT_ARTICLE_LIMIT=${toString cfg.defaultArticleLimit}"
                  "DEFAULT_SUMMARY_LENGTH=${toString cfg.defaultSummaryLength}"
                ];

                # Load password from file
                EnvironmentFile = cfg.passwordFile;

                # Systemd hardening
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

                Restart = "on-failure";
                RestartSec = 5;
              };
            };

            # Open firewall if requested
            networking.firewall.allowedTCPPorts = mkIf cfg.openFirewall [ cfg.port ];
          };
        };
    };
}
