#!/usr/bin/env python3
"""Generate a timing correlation report between timer T0 events and sensor HIT events.

This tool connects to the existing events SQLite DB (default: `logs/bridge.db`),
finds T0 (timer) events and subsequent HIT events within a given window, and
emits a CSV of matched pairs plus a small summary printed to stdout.

The matching policy (simple, low-risk): for each T0 event, pick the earliest
HIT event with ts_ms > t0_ts_ms and (ts_ms - t0_ts_ms) <= max_lag_ms.
"""
from __future__ import annotations
import argparse
import csv
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class Match:
    session_id: str
    t0_seq: int
    t0_ts_ms: float
    hit_seq: int
    hit_ts_ms: float
    offset_ms: float


def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def generate_matches(con: sqlite3.Connection, session: Optional[str], max_lag_ms: float) -> List[Match]:
    # Fetch T0 and HIT events for the session (or all sessions if None)
    params: list = []
    sess_clause = ""
    if session:
        sess_clause = "WHERE session_id = ?"
        params.append(session)

    q_t0 = f"SELECT seq, ts_ms, session_id FROM events {sess_clause} AND msg = 'T0' ORDER BY ts_ms"
    q_hit = f"SELECT seq, ts_ms, session_id FROM events {sess_clause} AND msg = 'HIT' ORDER BY ts_ms"

    # If session clause is empty, need to remove the stray AND
    if not session:
        q_t0 = q_t0.replace(" WHERE  AND", " WHERE") if " WHERE  AND" in q_t0 else q_t0
        q_t0 = q_t0.replace("  AND", " ")
        q_t0 = q_t0.replace("WHERE  AND", "WHERE ")
        q_hit = q_hit.replace(" WHERE  AND", " WHERE") if " WHERE  AND" in q_hit else q_hit

    cur = con.execute("SELECT seq, ts_ms, session_id, msg FROM events " + ("WHERE session_id = ?" if session else "") + " ORDER BY ts_ms", tuple(params))
    rows = cur.fetchall()

    # Partition into per-session lists of T0s and HITs to allow multi-session runs
    per_session: dict = {}
    for r in rows:
        sid = r["session_id"] or ""
        per_session.setdefault(sid, {"t0s": [], "hits": []})
        if r["msg"] == "T0":
            per_session[sid]["t0s"].append((r["seq"], r["ts_ms"]))
        elif r["msg"] == "HIT":
            per_session[sid]["hits"].append((r["seq"], r["ts_ms"]))

    matches: List[Match] = []
    for sid, lists in per_session.items():
        t0s = lists["t0s"]
        hits = lists["hits"]
        # Iterate hits with an index to allow advancing; simple linear scan per session
        hit_idx = 0
        for t0_seq, t0_ts in t0s:
            # advance hit_idx until the first hit with ts_ms > t0_ts
            while hit_idx < len(hits) and hits[hit_idx][1] <= t0_ts:
                hit_idx += 1
            if hit_idx >= len(hits):
                break
            candidate_seq, candidate_ts = hits[hit_idx]
            offset = candidate_ts - t0_ts
            if offset <= max_lag_ms:
                matches.append(Match(session_id=sid, t0_seq=t0_seq, t0_ts_ms=t0_ts, hit_seq=candidate_seq, hit_ts_ms=candidate_ts, offset_ms=offset))
                # advance to next hit for the next T0 (one-to-one mapping)
                hit_idx += 1
            else:
                # no hit within the allowed window for this T0
                continue

    return matches


def summarize(matches: List[Match]) -> Tuple[int, int, float, float]:
    # return (n_matches, n_sessions, mean_offset_ms, stddev_ms)
    if not matches:
        return 0, 0, 0.0, 0.0
    n = len(matches)
    sessions = len(set(m.session_id for m in matches))
    offsets = [m.offset_ms for m in matches]
    mean = sum(offsets) / n
    var = sum((x - mean) ** 2 for x in offsets) / n
    std = math.sqrt(var)
    return n, sessions, mean, std


def write_csv(matches: List[Match], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["session_id", "t0_seq", "t0_ts_ms", "hit_seq", "hit_ts_ms", "offset_ms"])
        for m in matches:
            w.writerow([m.session_id, m.t0_seq, f"{m.t0_ts_ms:.3f}", m.hit_seq, f"{m.hit_ts_ms:.3f}", f"{m.offset_ms:.3f}"])


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Timing correlation report between T0 and HIT events")
    ap.add_argument("--db", type=Path, default=Path("logs/bridge.db"), help="Path to SQLite DB (default: logs/bridge.db)")
    ap.add_argument("--session", help="Filter by session_id (optional)")
    ap.add_argument("--max-lag-ms", type=float, default=500.0, help="Maximum allowed lag between T0 and HIT in milliseconds (default: 500ms)")
    ap.add_argument("--out", type=Path, default=Path("reports/timing_correlation.csv"), help="Output CSV path")
    args = ap.parse_args(argv)

    con = connect(args.db)
    try:
        matches = generate_matches(con, args.session, args.max_lag_ms)
        write_csv(matches, args.out)
        n, sessions, mean, std = summarize(matches)
        print(f"Wrote {len(matches)} matched pairs to {args.out}")
        print(f"Sessions with matches: {sessions}")
        if n:
            print(f"Mean offset: {mean:.2f} ms (std: {std:.2f} ms)")
        else:
            print("No matches found with the given criteria.")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
