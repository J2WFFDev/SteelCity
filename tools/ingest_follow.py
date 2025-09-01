#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sqlite3, os, time, sys, pathlib, signal
from typing import Optional


def ensure_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(
        """
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
    )
    return conn


def current_daily_file(log_dir: pathlib.Path, prefix: str) -> pathlib.Path:
    day = time.strftime("%Y%m%d")
    return log_dir / f"{prefix}_{day}.ndjson"


def ingest_line(conn: sqlite3.Connection, rec: dict) -> None:
    try:
        conn.execute(
            "INSERT OR IGNORE INTO events(seq, ts_ms, type, msg, plate, t_rel_ms, session_id, pid, schema, data_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                int(rec.get("seq", 0)),
                float(rec.get("ts_ms", 0.0)),
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
    except Exception:
        # best-effort: skip bad lines
        pass


def follow_and_ingest(
    log_dir: pathlib.Path,
    prefix: str,
    db_path: pathlib.Path,
    poll_ms: int = 500,
    from_start: bool = False,
) -> None:
    conn = ensure_db(str(db_path))
    stopping = False

    def _stop(*_a):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    last_size = 0
    fpath = current_daily_file(log_dir, prefix)
    fh: Optional[object] = None
    while not stopping:
        try:
            # Handle day rollover: reopen if path changed
            new_path = current_daily_file(log_dir, prefix)
            if new_path != fpath:
                if fh:
                    fh.close()
                    fh = None
                fpath = new_path
                last_size = 0

            # Open if needed
            if fh is None:
                os.makedirs(log_dir, exist_ok=True)
                fh = open(fpath, "r", encoding="utf-8")
                # Position file pointer depending on mode
                if from_start:
                    fh.seek(0, os.SEEK_SET)
                else:
                    # default follower behavior: only new lines
                    fh.seek(0, os.SEEK_END)
                last_size = fh.tell()

            # Read any new lines
            where = fh.tell()
            line = fh.readline()
            if not line:
                time.sleep(max(0.01, poll_ms/1000.0))
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            ingest_line(conn, rec)
            conn.commit()
        except FileNotFoundError:
            # No file yet; wait and retry (e.g., early boot)
            time.sleep(max(0.05, poll_ms/1000.0))
        except Exception:
            # Transient errors: small backoff
            time.sleep(0.2)

    if fh:
        fh.close()
    conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Follow NDJSON and ingest to SQLite in near-real-time")
    ap.add_argument("--logs", default="logs", help="Logs directory (default: logs)")
    ap.add_argument("--prefix", default="bridge", help="NDJSON file prefix (default: bridge)")
    ap.add_argument("--db", default="logs/bridge.db", help="SQLite DB path (default: logs/bridge.db)")
    ap.add_argument("--poll-ms", type=int, default=200, help="Polling interval for new data (default: 200 ms)")
    ap.add_argument("--from-start", action="store_true", help="Start reading from beginning of current daily file instead of end")
    args = ap.parse_args()

    follow_and_ingest(
        pathlib.Path(args.logs),
        args.prefix,
        pathlib.Path(args.db),
        poll_ms=args.poll_ms,
        from_start=args.from_start,
    )


if __name__ == "__main__":
    main()
