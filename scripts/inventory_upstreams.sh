#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR="$ROOT/vendor"
OUT="$ROOT/shared/upstream-inventory.md"
{
  echo "# Upstream inventory"
  echo
  echo "Generated from shallow clones in vendor/. This is discovery only; model weights are not bundled."
  echo
  for dir in "$VENDOR"/*; do
    [ -d "$dir" ] || continue
    name="$(basename "$dir")"
    echo "## $name"
    if [ -f "$dir/README.md" ]; then
      echo "- README: vendor/$name/README.md"
      grep -m 5 -E '^(#|##|Requires|Install|Usage|Quick|Run|Launch|Docker|Input|Output)' "$dir/README.md" | sed 's/^/- /' || true
    else
      echo "- README: not found"
    fi
    files=$(find "$dir" -maxdepth 3 -type f \( -name 'requirements*.txt' -o -name 'pyproject.toml' -o -name 'package.json' -o -name 'Dockerfile*' -o -name '*.launch.py' -o -name 'docker-compose*.yml' \) | sort | head -20 || true)
    if [ -n "$files" ]; then
      echo "- Candidate runtime files:"
      while IFS= read -r f; do echo "  - ${f#"$ROOT/"}"; done <<< "$files"
    else
      echo "- Candidate runtime files: none found"
    fi
    echo
  done
} > "$OUT"
cat "$OUT"
