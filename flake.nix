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
            pkgs.python312
            pkgs.ruff
          ];

          env = {
            UV_PYTHON_DOWNLOADS = "never";
            UV_PYTHON = "${pkgs.python312}/bin/python3.12";
          };

          shellHook = ''
            echo "FreshRSS MCP Server dev shell"
            echo "  uv sync          — install deps"
            echo "  uv run pytest    — run tests"
            echo "  uv run freshrss-mcp — start server"
          '';
        };
      }
    );
}
