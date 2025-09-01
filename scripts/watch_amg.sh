#!/usr/bin/env bash
set -euo pipefail

# Always run from project root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

# Pick the newest bridge_*.ndjson
echo "Waiting for NDJSON in logs/ …"
latest=""
for i in {1..60}; do
  latest=$(ls -1t logs/bridge_*.ndjson 2>/dev/null | head -n 1 || true)
  if [[ -n "${latest}" && -f "${latest}" ]]; then
    break
  fi
  sleep 1
done
if [[ -z "${latest}" || ! -f "${latest}" ]]; then
  echo "No NDJSON found in logs/ after waiting. Is the bridge running?"
  exit 2
fi

echo "Watching ${latest} (AMG events)…"
export PYTHONUNBUFFERED=1
PYTHONPATH=.:src .venv/bin/python -m tools.watch_amg --pretty --file "${latest}" "$@"
