#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
import sqlite3
from pathlib import Path
from typing import Optional, Iterable, Tuple


def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def fmt_dur(seconds: float) -> str:
    if seconds is None:
        return "-"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def cmd_sessions(con: sqlite3.Connection, limit: int = 50) -> None:
    # Note: ts_ms is from time.monotonic(). Only compare within a session.
    q = """
    WITH per AS (
      SELECT session_id,
             COUNT(*) AS n,
             MIN(ts_ms) AS tmin,
             MAX(ts_ms) AS tmax,
             SUM(CASE WHEN msg='HIT' THEN 1 ELSE 0 END) AS hits,
             SUM(CASE WHEN msg='T0' THEN 1 ELSE 0 END) AS t0s
      FROM events
      GROUP BY session_id
    )
    SELECT session_id, n, hits, t0s, tmin, tmax, (tmax - tmin)/1000.0 AS dur_s
    FROM per
    ORDER BY tmax DESC
    LIMIT ?;
    """
    cur = con.execute(q, (limit,))
    rows = cur.fetchall()
    print("session_id,n,hit_count,t0_count,duration")
    for r in rows:
        print(f"{r['session_id']},{r['n']},{r['hits']},{r['t0s']},{fmt_dur(r['dur_s'])}")


def cmd_types(con: sqlite3.Connection, session: Optional[str]) -> None:
    if session:
        q = "SELECT type, msg, COUNT(*) AS n FROM events WHERE session_id=? GROUP BY type, msg ORDER BY n DESC"
        cur = con.execute(q, (session,))
    else:
        q = "SELECT type, msg, COUNT(*) AS n FROM events GROUP BY type, msg ORDER BY n DESC"
        cur = con.execute(q)
    print("type,msg,count")
    for r in cur.fetchall():
        t = r[0] if r[0] is not None else ""
        m = r[1] if r[1] is not None else ""
        print(f"{t},{m},{r[2]}")


def cmd_hits(con: sqlite3.Connection, session: Optional[str], plate: Optional[str]) -> None:
    where = ["type='event'", "msg='HIT'"]
    params: list = []
    if session:
        where.append("session_id = ?")
        params.append(session)
    if plate:
        where.append("plate = ?")
        params.append(plate)
    q = f"""
        SELECT plate,
               COUNT(*) AS n,
               MIN(t_rel_ms) AS tmin,
               MAX(t_rel_ms) AS tmax,
               AVG(t_rel_ms) AS tavg
        FROM events
        WHERE {" AND ".join(where)}
        GROUP BY plate
        ORDER BY n DESC
    """
    cur = con.execute(q, params)
    print("plate,count,t_rel_min_ms,t_rel_max_ms,t_rel_avg_ms")
    for r in cur.fetchall():
        print(f"{r['plate']},{r['n']},{r['tmin']:.1f},{r['tmax']:.1f},{r['tavg']:.1f}")


def cmd_gaps(con: sqlite3.Connection, session: Optional[str], threshold_sec: float, limit: int) -> None:
    params: list = []
    sess_clause = ""
    if session:
        sess_clause = "WHERE session_id = ?"
        params.append(session)
    # Compute gaps by ts_ms order; ts_ms is monotonic within a process/session
    q = f"""
    WITH seq AS (
      SELECT id, session_id, ts_ms,
             ts_ms - LAG(ts_ms) OVER (PARTITION BY session_id ORDER BY ts_ms) AS dt
      FROM events {sess_clause}
    )
    SELECT session_id, COUNT(*) AS ngaps,
           MAX(dt)/1000.0 AS max_gap_s,
           AVG(CASE WHEN dt > ?*1000.0 THEN dt END)/1000.0 AS avg_gap_s
    FROM seq
    WHERE dt > ?*1000.0
    GROUP BY session_id
    ORDER BY max_gap_s DESC
    LIMIT ?
    """
    cur = con.execute(q, (*params, threshold_sec, threshold_sec, limit))
    print("session_id,ngaps,max_gap,avg_gap_over_threshold")
    for r in cur.fetchall():
        print(f"{r['session_id']},{r['ngaps']},{fmt_dur(r['max_gap_s'])},{fmt_dur(r['avg_gap_s'])}")


def cmd_recent(con: sqlite3.Connection, window_sec: float, session: Optional[str]) -> None:
    # Because ts_ms is monotonic, define "recent" relative to the session (or global) max ts_ms
    if session:
        q_bounds = "SELECT MAX(ts_ms) FROM events WHERE session_id=?"
        (tmax,) = con.execute(q_bounds, (session,)).fetchone()
        if tmax is None:
            print("No data for that session")
            return
        q = "SELECT type, msg, COUNT(*) FROM events WHERE session_id=? AND ts_ms > ? GROUP BY type, msg ORDER BY 3 DESC"
        cur = con.execute(q, (session, tmax - window_sec * 1000.0))
    else:
        (tmax,) = con.execute("SELECT MAX(ts_ms) FROM events").fetchone()
        if tmax is None:
            print("No data")
            return
        q = "SELECT type, msg, COUNT(*) FROM events WHERE ts_ms > ? GROUP BY type, msg ORDER BY 3 DESC"
        cur = con.execute(q, (tmax - window_sec * 1000.0,))
    print("type,msg,count")
    for r in cur.fetchall():
        t = r[0] if r[0] is not None else ""
        m = r[1] if r[1] is not None else ""
        print(f"{t},{m},{r[2]}")


def cmd_export(con: sqlite3.Connection, session: str, out: Path) -> None:
    q = "SELECT seq, ts_ms, type, msg, plate, t_rel_ms, session_id, pid, schema, data_json FROM events WHERE session_id=? ORDER BY seq"
    cur = con.execute(q, (session,))
    rows = cur.fetchall()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["seq", "ts_ms", "type", "msg", "plate", "t_rel_ms", "session_id", "pid", "schema", "data_json"])
        for r in rows:
            w.writerow([r["seq"], r["ts_ms"], r["type"], r["msg"], r["plate"], r["t_rel_ms"], r["session_id"], r["pid"], r["schema"], r["data_json"]])
    print(f"Exported {len(rows)} rows to {out}")


def cmd_last_seen(con: sqlite3.Connection, session: Optional[str], limit: int) -> None:
    """Per-plate last-seen summary.

    Notes:
    - ts_ms is monotonic per process; for cross-session comparisons, prefer filtering by session.
    """
    params: list = []
    sess_clause = ""
    if session:
        sess_clause = "WHERE session_id = ?"
        params.append(session)
    q = f"""
    WITH per AS (
      SELECT plate,
             COUNT(*) AS n,
             MIN(ts_ms) AS tmin,
             MAX(ts_ms) AS tmax
      FROM events
      {sess_clause}
      AND plate IS NOT NULL
      GROUP BY plate
    )
    SELECT plate, n, tmin, tmax, (tmax - tmin)/1000.0 AS span_s
    FROM per
    ORDER BY tmax DESC
    LIMIT ?
    """
    cur = con.execute(q, (*params, limit))
    print("plate,count,tmin_ms,tmax_ms,span")
    for r in cur.fetchall():
        print(f"{r['plate']},{r['n']},{r['tmin']},{r['tmax']},{fmt_dur(r['span_s'])}")


def _tmax_bound(con: sqlite3.Connection, session: Optional[str]) -> Optional[float]:
    if session:
        (tmax,) = con.execute("SELECT MAX(ts_ms) FROM events WHERE session_id=?", (session,)).fetchone()
    else:
        (tmax,) = con.execute("SELECT MAX(ts_ms) FROM events").fetchone()
    return tmax


def cmd_cadence(
    con: sqlite3.Connection,
    window_sec: float,
    session: Optional[str],
    by: str = "type_msg",
    limit: int = 20,
) -> None:
    """Event rates over a recent window relative to max ts_ms.

    by: one of 'type_msg' (default), 'type', 'plate', or 'all'.
    """
    tmax = _tmax_bound(con, session)
    if tmax is None:
        print("No data")
        return
    tmin = tmax - window_sec * 1000.0
    params: list = []
    where = ["ts_ms > ?"]
    params.append(tmin)
    if session:
        where.append("session_id = ?")
        params.append(session)

    if by == "all":
        q = f"SELECT COUNT(*) AS n FROM events WHERE {' AND '.join(where)}"
        (n,) = con.execute(q, params).fetchone()
        rate = (n / max(1.0, window_sec)) * 60.0
        print("window_sec,count,per_minute")
        print(f"{int(window_sec)},{n},{rate:.2f}")
        return

    if by == "plate":
        sel = "plate"
        grp = "plate"
    elif by == "type":
        sel = "type"
        grp = "type"
    else:
        sel = "type, msg"
        grp = "type, msg"

    q = f"""
    SELECT {sel}, COUNT(*) AS n
    FROM events
    WHERE {" AND ".join(where)}
    GROUP BY {grp}
    ORDER BY n DESC
    LIMIT ?
    """
    cur = con.execute(q, (*params, limit))
    header = {
        "plate": "plate,count,per_minute",
        "type": "type,count,per_minute",
        "type, msg": "type,msg,count,per_minute",
    }[sel]
    print(header)
    for r in cur.fetchall():
        if sel == "plate":
            key = r[0] if r[0] is not None else ""
            n = r[1]
            rpm = (n / max(1.0, window_sec)) * 60.0
            print(f"{key},{n},{rpm:.2f}")
        elif sel == "type":
            key = r[0] if r[0] is not None else ""
            n = r[1]
            rpm = (n / max(1.0, window_sec)) * 60.0
            print(f"{key},{n},{rpm:.2f}")
        else:
            t = r[0] if r[0] is not None else ""
            m = r[1] if r[1] is not None else ""
            n = r[2]
            rpm = (n / max(1.0, window_sec)) * 60.0
            print(f"{t},{m},{n},{rpm:.2f}")


def cmd_errors_recent(con: sqlite3.Connection, window_sec: float, session: Optional[str], limit: int) -> None:
    tmax = _tmax_bound(con, session)
    if tmax is None:
        print("No data")
        return
    tmin = tmax - window_sec * 1000.0
    params: list = [tmin]
    where = ["type='error'", "ts_ms > ?"]
    if session:
        where.append("session_id = ?")
        params.append(session)
    q = f"SELECT msg, COUNT(*) AS n FROM events WHERE {' AND '.join(where)} GROUP BY msg ORDER BY n DESC LIMIT ?"
    cur = con.execute(q, (*params, limit))
    print("msg,count")
    for r in cur.fetchall():
        print(f"{r['msg']},{r['n']}")


def cmd_gap_list(con: sqlite3.Connection, session: Optional[str], threshold_sec: float, limit: int) -> None:
    params: list = [threshold_sec * 1000.0]
    sess_clause = ""
    if session:
        sess_clause = "WHERE session_id = ?"
        params.insert(0, session)
    q = f"""
    WITH seq AS (
      SELECT session_id, seq,
             ts_ms,
             LAG(ts_ms) OVER (PARTITION BY session_id ORDER BY ts_ms) AS prev_ts,
             LAG(seq)   OVER (PARTITION BY session_id ORDER BY ts_ms) AS prev_seq
      FROM events
      {sess_clause}
    )
    SELECT session_id, prev_seq, seq, (ts_ms - prev_ts)/1000.0 AS gap_s
    FROM seq
    WHERE prev_ts IS NOT NULL AND (ts_ms - prev_ts) > ?
    ORDER BY gap_s DESC
    LIMIT ?
    """
    cur = con.execute(q, (*params, limit))
    print("session_id,prev_seq,seq,gap")
    for r in cur.fetchall():
        print(f"{r['session_id']},{r['prev_seq']},{r['seq']},{fmt_dur(r['gap_s'])}")


def main() -> None:
    ap = argparse.ArgumentParser(description="SQLite reporting for SteelCity events")
    ap.add_argument("--db", default="logs/bridge.db", type=Path, help="Path to SQLite DB (default: logs/bridge.db)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("sessions", help="List recent sessions with counts and durations")
    sp.add_argument("--limit", type=int, default=20, help="Max sessions to list (default: 20)")

    sp = sub.add_parser("types", help="Count records by type and msg")
    sp.add_argument("--session", help="Filter by session_id")

    sp = sub.add_parser("hits", help="Hit stats by plate (optionally filter by session)")
    sp.add_argument("--session", help="Filter by session_id")
    sp.add_argument("--plate", help="Filter by plate")

    sp = sub.add_parser("gaps", help="Find large gaps (by ts_ms) within session(s)")
    sp.add_argument("--session", help="Filter by session_id")
    sp.add_argument("--threshold-sec", type=float, default=10.0, help="Gap threshold in seconds (default: 10)")
    sp.add_argument("--limit", type=int, default=50, help="Max rows (default: 50)")

    sp = sub.add_parser("recent", help="Counts over the most recent window relative to max ts_ms")
    sp.add_argument("--window-sec", type=float, default=900, help="Window size in seconds (default: 900 = 15 min)")
    sp.add_argument("--minutes", type=float, help="Alternative to --window-sec: minutes (e.g., 30 for 30 minutes)")
    sp.add_argument("--session", help="Filter by session_id")

    sp = sub.add_parser("export", help="Export a session to CSV")
    sp.add_argument("--session", required=True, help="Session ID to export")
    sp.add_argument("--out", type=Path, required=True, help="Output CSV path")

    sp = sub.add_parser("last_seen", help="Per-plate last seen summary (ts_ms is monotonic; prefer within-session)")
    sp.add_argument("--session", help="Filter by session_id")
    sp.add_argument("--limit", type=int, default=50, help="Max rows (default: 50)")

    sp = sub.add_parser("cadence", help="Event rates over a recent window")
    sp.add_argument("--window-sec", type=float, default=600, help="Window size in seconds (default: 600)")
    sp.add_argument("--minutes", type=float, help="Alternative to --window-sec: minutes (e.g., 10 for 10 minutes)")
    sp.add_argument("--session", help="Filter by session_id")
    sp.add_argument("--by", choices=["type_msg", "type", "plate", "all"], default="type_msg", help="Group by (default: type_msg)")
    sp.add_argument("--limit", type=int, default=20, help="Max rows (default: 20)")

    sp = sub.add_parser("errors_recent", help="Top error messages over a recent window")
    sp.add_argument("--window-sec", type=float, default=1800, help="Window size in seconds (default: 1800 = 30 min)")
    sp.add_argument("--minutes", type=float, help="Alternative to --window-sec: minutes (e.g., 30 for 30 minutes)")
    sp.add_argument("--session", help="Filter by session_id")
    sp.add_argument("--limit", type=int, default=50, help="Max rows (default: 50)")

    sp = sub.add_parser("gap_list", help="List largest gaps by ts_ms within session(s)")
    sp.add_argument("--session", help="Filter by session_id")
    sp.add_argument("--threshold-sec", type=float, default=10.0, help="Gap threshold in seconds (default: 10)")
    sp.add_argument("--limit", type=int, default=50, help="Max rows (default: 50)")

    args = ap.parse_args()

    con = connect(args.db)
    try:
        if args.cmd == "sessions":
            cmd_sessions(con, limit=getattr(args, "limit", 20))
        elif args.cmd == "types":
            cmd_types(con, session=getattr(args, "session", None))
        elif args.cmd == "hits":
            cmd_hits(con, session=getattr(args, "session", None), plate=getattr(args, "plate", None))
        elif args.cmd == "gaps":
            cmd_gaps(con, session=getattr(args, "session", None), threshold_sec=getattr(args, "threshold_sec", 10.0), limit=getattr(args, "limit", 50))
        elif args.cmd == "recent":
            _ws = getattr(args, "window_sec", 900.0)
            _m = getattr(args, "minutes", None)
            if _m is not None:
                try:
                    _ws = float(_m) * 60.0
                except Exception:
                    pass
            cmd_recent(con, window_sec=_ws, session=getattr(args, "session", None))
        elif args.cmd == "export":
            cmd_export(con, session=args.session, out=args.out)
        elif args.cmd == "last_seen":
            cmd_last_seen(con, session=getattr(args, "session", None), limit=getattr(args, "limit", 50))
        elif args.cmd == "cadence":
            _ws = getattr(args, "window_sec", 600.0)
            _m = getattr(args, "minutes", None)
            if _m is not None:
                try:
                    _ws = float(_m) * 60.0
                except Exception:
                    pass
            cmd_cadence(con, window_sec=_ws, session=getattr(args, "session", None), by=getattr(args, "by", "type_msg"), limit=getattr(args, "limit", 20))
        elif args.cmd == "errors_recent":
            _ws = getattr(args, "window_sec", 1800.0)
            _m = getattr(args, "minutes", None)
            if _m is not None:
                try:
                    _ws = float(_m) * 60.0
                except Exception:
                    pass
            cmd_errors_recent(con, window_sec=_ws, session=getattr(args, "session", None), limit=getattr(args, "limit", 50))
        elif args.cmd == "gap_list":
            cmd_gap_list(con, session=getattr(args, "session", None), threshold_sec=getattr(args, "threshold_sec", 10.0), limit=getattr(args, "limit", 50))
        else:
            raise SystemExit(2)
    finally:
        con.close()


if __name__ == "__main__":
    main()
