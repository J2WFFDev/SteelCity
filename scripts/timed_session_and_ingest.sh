#!/usr/bin/env bash
set -euo pipefail

# timed_session_and_ingest.sh
# Usage: ./scripts/timed_session_and_ingest.sh [DURATION_SECONDS]
# - Stops the user service to avoid conflicts
# - Starts a timed run with a fresh SESSION_ID
# - After completion, ingests only that session into logs/bridge.db
# - Emits a small report at logs/timed_session_report.txt

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT_DIR"

DURATION="${1:-2700}" # default 45 minutes

mkdir -p logs

echo "[timed] Stopping user service (if running)..."
systemctl --user stop bridge.user.service || true

echo "[timed] Stopping any background bridge instance..."
./scripts/stop_bridge.sh || true
rm -f logs/bridge.pid 2>/dev/null || true

echo "[timed] Preparing venv and environment..."
python3 -m venv .venv >/dev/null 2>&1 || true
source .venv/bin/activate
export PYTHONPATH=src

# Fresh session id, include date/time for convenience
SESSION_ID="run$(date +%Y%m%d_%H%M%S)"
export SESSION_ID
echo "$SESSION_ID" > logs/timed_sid.txt

echo "[timed] SESSION_ID=$SESSION_ID"
echo "[timed] Starting timed run for ${DURATION}s..."

# Run the bridge in background managed by timed script
TAIL_LINES=0 ./scripts/timed_bridge_run.sh "$DURATION"

echo "[timed] Timed run complete. Ingesting session: $SESSION_ID"

# Ensure DB exists and ingest only records for this session from all daily logs (in case of midnight rollover)
touch logs/bridge.db
for f in logs/bridge_*.ndjson; do
  [ -f "$f" ] || continue
  python tools/ingest_sqlite.py "$f" --db logs/bridge.db --session "$SESSION_ID" || true
done

echo "[timed] Ingest complete. Writing report..."
python - <<PY > logs/timed_session_report.txt
import sqlite3, os
db = 'logs/bridge.db'
sid = os.environ.get('SESSION_ID','')
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute("select count(*) from events where session_id=?", (sid,))
rows = cur.fetchone()[0]
cur.execute("select min(ts_ms), max(ts_ms) from events where session_id=?", (sid,))
tsb = cur.fetchone()
print(f"session_id: {sid}")
print(f"rows_ingested: {rows}")
print(f"ts_bounds: {tsb}")
con.close()
PY

echo "[timed] Done. Report at logs/timed_session_report.txt"
echo "[timed] SESSION_ID=$SESSION_ID"
