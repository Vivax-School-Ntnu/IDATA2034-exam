{
  description = "IDATA2034 exam";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      nixpkgs,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python313;
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            python
            pkgs.uv
            pkgs.ruff
            pkgs.basedpyright
          ];

          env = {
            UV_PYTHON = python.interpreter;
            # uv's standalone interpreters are dynamically linked against an FHS layout
            UV_PYTHON_DOWNLOADS = "never";
            UV_PYTHON_PREFERENCE = "only-system";

            # manylinux wheels dlopen these at import time
            LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
              pkgs.stdenv.cc.cc.lib
              pkgs.zlib
            ];
          };

          # nixpkgs' python hooks export it, which leaks store site-packages into the venv
          shellHook = ''
            unset PYTHONPATH
          '';
        };
      }
    );
}
