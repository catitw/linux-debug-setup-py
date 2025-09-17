set shell := ["bash", "-c"]

# List all the just commands
default:
    @just --list


# Update all the flake inputs
[group('nix')]
up:
  nix flake update --commit-lock-file -L --show-trace --verbose

# Update specific input
# Usage: just upp nixpkgs
[group('nix')]
upp input:
  nix flake update {{input}} --commit-lock-file
