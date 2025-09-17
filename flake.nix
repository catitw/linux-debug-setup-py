{
  description = "A Nix-flake-based Linux-Kernel development environment";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.05";
  };

  outputs =
    { self, nixpkgs, ... }:
    let
      # system should match the system you are running on
      system = "x86_64-linux";
    in
    {
      devShells."${system}".default =
        let
          pkgs = import nixpkgs { inherit system; };
        in
        # the code here is mainly copied from:
        #   https://wiki.nixos.org/wiki/Linux_kernel#Embedded_Linux_Cross-compile_xconfig_and_menuconfig
        (pkgs.mkShell {
          name = "kernel-build-env";
          venvDir = "./.venv";
          buildInputs = with pkgs; [
            python3
            python3Packages.venvShellHook
          ];
          postVenvCreation = ''
            pip install -r ${./requirements.txt}
          '';

          packages =
            with pkgs;
            [
              # we need theses packages to run `make menuconfig` successfully.
              pkg-config
              ncurses

              gcc

              ccache

              # llvmPackages_21.libcxxClang
              llvmPackages_21.clang-unwrapped
              # llvmPackages_21.bintools

              # utils for this project
              parted
              bear
              OVMF.fd
              qemu
              qemu-utils
              
              # crypt libraries for archinstall
              cryptsetup
              util-linux
            ]
            ++ pkgs.linux.nativeBuildInputs;

          shellHook = ''
            venvShellHook

            export LD=ld.lld
            export OVMF_CODE_4M=${pkgs.OVMF.fd}/FV/OVMF_CODE.fd
            export OVMF_VARS_4M=${pkgs.OVMF.fd}/FV/OVMF_VARS.fd

            echo "[devShell] OVMF_CODE_4M=$OVMF_CODE_4M"
            echo "[devShell] OVMF_VARS_4M=$OVMF_VARS_4M"
          '';
        });
    };
}
