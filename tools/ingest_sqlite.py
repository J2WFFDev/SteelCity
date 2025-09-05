#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sqlite3, os, time
from typing import Optional, Dict, Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  seq INTEGER NOT NULL,
  ts_ms REAL NOT NULL,
  type TEXT NOT NULL,
  msg TEXT,
  plate TEXT,
  t_rel_ms REAL,
  session_id TEXT,
  pid INTEGER,
  schema TEXT,
  data_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts_ms);
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_sess_seq ON events(session_id, seq);
"""

def ensure_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(SCHEMA)
    return conn


def ingest_file(conn: sqlite3.Connection, path: str, session: Optional[str] = None, limit: Optional[int] = None) -> int:
    n = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if session and rec.get("session_id") != session:
                continue
            # Determine ts_ms: prefer the recorded monotonic ts_ms, else fall back to
            # t_rel_ms (if present) or current wall-clock time in ms. This keeps
            # existing downstream consumers working when `ts_ms` is not present
            # in the NDJSON (the logger now omits machine timestamps).
            def _compute_ts_ms(r):
                v = r.get("ts_ms", None)
                if v is not None:
                    try:
                        return float(v)
                    except Exception:
                        pass
                v = r.get("t_rel_ms", None)
                if v is not None:
                    try:
                        return float(v)
                    except Exception:
                        pass
                return time.time() * 1000.0

            conn.execute(
                "INSERT OR IGNORE INTO events(seq, ts_ms, type, msg, plate, t_rel_ms, session_id, pid, schema, data_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    int(rec.get("seq", 0)),
                    float(_compute_ts_ms(rec)),
                    str(rec.get("type")),
                    rec.get("msg"),
                    rec.get("plate"),
                    None if rec.get("t_rel_ms", None) is None else float(rec.get("t_rel_ms")),
                    rec.get("session_id"),
                    int(rec.get("pid", -1)) if isinstance(rec.get("pid", None), int) else None,
                    rec.get("schema"),
                    json.dumps(rec.get("data", {}), separators=(",", ":")),
                ),
            )
            n += 1
            if limit and n >= limit:
                break
    conn.commit()
    return n


def main():
    ap = argparse.ArgumentParser(description="Ingest NDJSON into a local SQLite DB")
    ap.add_argument("log", help="Path to NDJSON file (e.g., logs/bridge_YYYYMMDD.ndjson)")
    ap.add_argument("--db", default="logs/bridge.db", help="SQLite DB path (default: logs/bridge.db)")
    ap.add_argument("--session", help="Filter by session_id")
    ap.add_argument("--limit", type=int, help="Max lines to ingest from file")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.db), exist_ok=True)
    conn = ensure_db(args.db)
    t0 = time.time()
    n = ingest_file(conn, args.log, session=args.session, limit=args.limit)
    dt = time.time() - t0
    print(f"Ingested {n} records from {args.log} into {args.db} in {dt:.2f}s")


if __name__ == "__main__":
    main()
