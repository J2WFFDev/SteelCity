#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

pat="${1:-bt50|amg_|HIT|error}"
latest=$(ls -t logs/bridge_*.ndjson 2>/dev/null | head -n 1 || true)
echo LATEST:${latest:-none}
if [[ -n "${latest}" && -f "$latest" ]]; then
  grep -naE "$pat" "$latest" || true
else
  echo "no ndjson files found"
fi
