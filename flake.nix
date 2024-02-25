{
  description = "Generic templated configuration management for Kubernetes, Terraform and other things";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # see https://github.com/nix-community/poetry2nix/tree/master#api for more functions and examples.
        pkgs = nixpkgs.legacyPackages.${system};
        inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryEnv mkPoetryApplication defaultPoetryOverrides;
        pypkgs-build-requirements = {
          libmagic = [ "setuptools" ];
          reclass = [ "setuptools" ];
          kadet = [ "poetry" ];
        };
        p2n-overrides = defaultPoetryOverrides.extend (self: super:
          let
            inherit (self.lib.asserts) assertMsg;
          in
          builtins.mapAttrs (package: build-requirements:
            (builtins.getAttr package super).overridePythonAttrs (old: {
              buildInputs = (old.buildInputs or [ ]) ++ (builtins.map (pkg: if builtins.isString pkg then builtins.getAttr pkg super else pkg) build-requirements);
            })
          ) pypkgs-build-requirements
          );
        overrides = p2n-overrides.extend (
            self: super: let
              inherit (self.lib.asserts) assertMsg;
            in {
              rpds-py = super.rpds-py.overridePythonAttrs (old: {
                cargoDeps =
                  assert assertMsg (old.version == "0.18.0")
                    "Expected ${old.version} to be version 0.18.0, remove this workaround in poetryOverrides.nix";
                  assert assertMsg (old.cargoDeps.hash == "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
                    "Workaround no longer needed, remove it in poetryOverrides.nix";
                  self.pkgs.rustPlatform.fetchCargoTarball {
                    inherit (old) src;
                    name = "${old.pname}-${old.version}";
                    hash = "sha256-wd1teRDhjQWlKjFIahURj0iwcfkpyUvqIWXXscW7eek=";
                  };
              });
            }
        );
      in {
        packages = {
          kapitan = mkPoetryApplication {
            projectDir = self;
            overrides = overrides;
          };
          default = self.packages.${system}.kapitan;
        };

        devShells.default = pkgs.mkShell {
          inputsFrom = [ self.packages.${system}.kapitan ];
          packages = [ pkgs.poetry ];
        };
      });
}
