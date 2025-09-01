#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

PIDFILE="logs/bridge.pid"

if [[ -f "$PIDFILE" ]]; then
    PID="$(cat "$PIDFILE" 2>/dev/null || true)"
    if [[ -n "${PID:-}" ]] && ps -p "$PID" >/dev/null 2>&1; then
        echo "Stopping bridge PID $PID ..."
        kill "$PID" 2>/dev/null || true
        # Give it a moment to exit cleanly
        for i in {1..20}; do
            if ps -p "$PID" >/dev/null 2>&1; then
                sleep 0.2
            else
                break
            fi
        done
        if ps -p "$PID" >/dev/null 2>&1; then
            echo "Force killing bridge PID $PID ..."
            kill -9 "$PID" 2>/dev/null || true
        fi
        rm -f "$PIDFILE" 2>/dev/null || true
        echo "Bridge stopped."
        exit 0
    fi
fi

# Fallback: try to find process by module name if pidfile missing/stale
PIDS=$(pgrep -f "python .* -m scripts.run_bridge" || true)
if [[ -n "${PIDS:-}" ]]; then
    echo "Stopping bridge processes: $PIDS"
    kill $PIDS 2>/dev/null || true
    sleep 0.5
    PIDS2=$(pgrep -f "python .* -m scripts.run_bridge" || true)
    if [[ -n "${PIDS2:-}" ]]; then
        echo "Force killing: $PIDS2"
        kill -9 $PIDS2 2>/dev/null || true
    fi
    rm -f "$PIDFILE" 2>/dev/null || true
    echo "Bridge stopped."
else
    echo "No running bridge found."
fi
