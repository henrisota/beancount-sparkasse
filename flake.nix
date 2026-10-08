{
  description = "Beancount importers for Sparkasse exports and statements";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";

    flake-parts = {
      url = "github:hercules-ci/flake-parts";
      inputs.nixpkgs-lib.follows = "nixpkgs";
    };
  };

  outputs = inputs:
    inputs.flake-parts.lib.mkFlake {inherit inputs;} {
      systems = ["aarch64-darwin" "x86_64-linux"];

      perSystem = {pkgs, ...}: {
        # uv owns the dependencies through uv.lock, as it does in CI; the shell
        # only provides uv and the interpreter from .python-version.
        devShells.default = pkgs.mkShell {
          packages = [pkgs.uv pkgs.python314];

          env = {
            UV_PYTHON = "${pkgs.python314}/bin/python3";
            UV_PYTHON_DOWNLOADS = "never";
          };

          shellHook = ''
            uv sync --locked --quiet
            source .venv/bin/activate
            prek install --hook-type pre-commit --hook-type pre-push > /dev/null
          '';
        };

        formatter = pkgs.alejandra;
      };
    };
}
