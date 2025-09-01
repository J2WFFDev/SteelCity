#!/usr/bin/env bash
set -euo pipefail

# Run from project root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

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

echo "LIVE: Following ${latest} for AMG events… (Ctrl+C to stop)"
export PYTHONUNBUFFERED=1
# Stream only new lines; rely on stdin mode of watcher to avoid file seek behavior
tail -n0 -F "${latest}" | PYTHONPATH=.:src .venv/bin/python -m tools.watch_amg --pretty
