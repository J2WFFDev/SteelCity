#!/usr/bin/env bash
set -euo pipefail

# timed_bridge_run.sh
# Usage:
#   ./scripts/timed_bridge_run.sh [DURATION_SECONDS]
# Env:
#   BRIDGE_CONFIG: optional path to config yaml (default: config.yaml)
#   AMG_DEBUG_RAW: if set, forwarded to the bridge process
#   TAIL_LINES: how many lines to tail at the end (default: 120)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

# Ensure venv and logs
python3 -m venv .venv >/dev/null 2>&1 || true
source .venv/bin/activate
mkdir -p logs

# Environment
export PYTHONPATH=src

DURATION="${1:-90}"
TAIL_LINES="${TAIL_LINES:-120}"
PIDFILE="logs/bridge.pid"
OUTFILE="logs/bridge_run.out"

# Start bridge (respects BRIDGE_CONFIG)
./scripts/run_bridge.sh

# Wait until PID file exists and process is alive (max ~10s)
for i in {1..100}; do
  if [[ -f "$PIDFILE" ]]; then
    PID=$(cat "$PIDFILE" 2>/dev/null || true)
    if [[ -n "${PID:-}" ]] && ps -p "$PID" >/dev/null 2>&1; then
      echo "Bridge running with PID $PID"
      break
    fi
  fi
  sleep 0.1
  if [[ $i -eq 100 ]]; then
    echo "ERROR: Bridge PID did not become available within 10s" >&2
    exit 1
  fi
done

# Sleep for requested duration
sleep "$DURATION"

# Stop bridge and tail logs
./scripts/stop_bridge.sh || true

echo "==== NDJSON TAIL ===="
# tail the latest ndjson file; if multiple exist, fallback to tail all
NDJSON_LATEST=$(ls -1t logs/bridge_*.ndjson 2>/dev/null | head -n 1 || true)
if [[ -n "${NDJSON_LATEST:-}" ]]; then
  tail -n "$TAIL_LINES" "$NDJSON_LATEST" || true
else
  tail -n "$TAIL_LINES" logs/bridge_*.ndjson 2>/dev/null || true
fi

echo "==== PROCESS STDOUT (bridge_run.out) ===="
if [[ -f "$OUTFILE" ]]; then
  tail -n "$TAIL_LINES" "$OUTFILE" || true
fi
