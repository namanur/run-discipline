#!/usr/bin/env bash
# Symlinks skills/*/ into ~/.commandcode/skills/ so the harness discovers them.
# Symlinks only, never settings.skills[]: the highest settings layer replaces that
# array whole, so one project-level settings.json would drop every global skill (D3).
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$HOME/.commandcode/skills"
mkdir -p "$target"
for d in "$repo"/skills/*/; do
  name="$(basename "$d")"
  ln -sfn "$d" "$target/$name"
  echo "linked $name"
done
