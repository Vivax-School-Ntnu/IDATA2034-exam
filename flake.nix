{
  description = "IDATA2034 exam";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    # uv >= 0.13.4 has not reached nixos-unstable yet
    nixpkgs-master.url = "github:NixOS/nixpkgs/master";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      nixpkgs,
      nixpkgs-master,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python314;
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            python
            nixpkgs-master.legacyPackages.${system}.uv
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
