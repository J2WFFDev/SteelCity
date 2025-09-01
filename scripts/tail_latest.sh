#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

latest=$(ls -t logs/bridge_*.ndjson 2>/dev/null | head -n 1 || true)
echo LATEST:${latest:-none}
if [[ -n "${latest}" && -f "$latest" ]]; then
  tail -n "${1:-50}" "$latest"
else
  echo "no ndjson files found"
fi
