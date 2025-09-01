# Streaming Ingest and DB Usage

This project supports both batch ingestion (ad-hoc) and streaming ingestion (near real-time).

## Goals
- Write each NDJSON record into SQLite as it is produced (no need to wait for a run to end)
- Make ingestion idempotent (safe to restart) and resilient
- Keep logs as the source of truth; DB is a convenient indexed view

## Components
- Batch tool: `tools/ingest_sqlite.py`
  - Inserts records from one NDJSON into `logs/bridge.db`
  - Idempotent via unique index `(session_id, seq)` and `INSERT OR IGNORE`
  - Useful for historic backfills or selective `--session` ingest
- Streaming service: `tools/ingest_follow.py`
  - Follows the current `logs/bridge_YYYYMMDD.ndjson` and inserts each line as it’s appended
  - Handles day rollover
  - Runs as a user-level service via `etc/ingest.user.service`

## Install/Run
- Install streaming ingest service:
  ```bash
  ./scripts/install_ingest_service.sh
  # verify
  systemctl --user status ingest.user.service --no-pager
  ```
- Ad-hoc backfill or selective session:
  ```bash
  python tools/ingest_sqlite.py logs/bridge_20250829.ndjson --db logs/bridge.db --session <SESSION_ID>
  ```

## Schema
Table `events` (indices on `session_id`, `type`, `ts_ms`, unique `(session_id, seq)`):
- `seq`, `ts_ms`, `type`, `msg`, `plate`, `t_rel_ms`, `session_id`, `pid`, `schema`, `data_json`

## Notes
- The ingest tools assume NDJSON is append-only; for corrections, re-run batch ingest.
- SQLite WAL mode is enabled for stable writes.

## Reports
Use `tools/sqlite_reports.py` for quick, indexed views on `logs/bridge.db`:

```bash

# Additional reports
# Per-plate last seen (prefer within a session)
python -m tools.sqlite_reports --db logs/bridge.db last_seen --session <SESSION_ID> --limit 20

# Event cadence over a recent window (grouped by type+msg)
python -m tools.sqlite_reports --db logs/bridge.db cadence --window-sec 600 --session <SESSION_ID>

# Top error messages in the last 30 minutes
python -m tools.sqlite_reports --db logs/bridge.db errors_recent --window-sec 1800 --session <SESSION_ID>

# Largest gaps with timestamps (by ts_ms) within a session
python -m tools.sqlite_reports --db logs/bridge.db gap_list --session <SESSION_ID> --threshold-sec 10 --limit 20
# Recent sessions
python -m tools.sqlite_reports --db logs/bridge.db sessions --limit 10

# Type counts for a session
python -m tools.sqlite_reports --db logs/bridge.db types --session <SESSION_ID>

# Hit stats by plate
python -m tools.sqlite_reports --db logs/bridge.db hits --session <SESSION_ID>

# Gap analysis (>10s) within a session
python -m tools.sqlite_reports --db logs/bridge.db gaps --session <SESSION_ID> --threshold-sec 10

# Export a session to CSV
python -m tools.sqlite_reports --db logs/bridge.db export --session <SESSION_ID> --out logs/session.csv
```
