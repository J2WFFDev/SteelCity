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

    cur = con.execute("SELECT seq, ts_ms, session_id, msg, data_json FROM events " + ("WHERE session_id = ?" if session else "") + " ORDER BY ts_ms", tuple(params))
    rows = cur.fetchall()

    # Partition into per-session lists of T0s and HITs to allow multi-session runs
    per_session: dict = {}
    for r in rows:
        sid = r["session_id"] or ""
        per_session.setdefault(sid, {"t0s": [], "hits": []})
        if r["msg"] == "T0":
            # include parsed data_json for potential amg fields
            per_session[sid]["t0s"].append((r["seq"], r["ts_ms"], r["data_json"]))
        elif r["msg"] == "HIT":
            per_session[sid]["hits"].append((r["seq"], r["ts_ms"], r["data_json"]))

    matches: List[Match] = []
    for sid, lists in per_session.items():
        t0s = lists["t0s"]
        hits = lists["hits"]
        # Iterate hits with an index to allow advancing; simple linear scan per session
        hit_idx = 0
        for t0_seq, t0_ts in t0s:
            t0_amg = None
            try:
                if t0_seq and isinstance(t0s[0], tuple):
                    # t0s entries are (seq, ts_ms, data_json)
                    pass
            except Exception:
                pass
            # unpack t0 fields defensively
            if len((t0_seq, t0_ts)) >= 2:
                # attempt to extract amg info from the stored data_json if present
                try:
                    t0_data_json = t0s[0][2] if len(t0s[0]) > 2 else None
                except Exception:
                    t0_data_json = None
            else:
                t0_data_json = None
            # First try to match by AMG fields if present (stronger match):
            matched = False
            # look ahead through hits within a reasonable time window to find matching amg
            look_idx = hit_idx
            while look_idx < len(hits):
                h_seq, h_ts, h_data_json = hits[look_idx]
                if h_ts <= t0_ts:
                    look_idx += 1
                    continue
                offset = h_ts - t0_ts
                if offset > max_lag_ms:
                    break
                # try to parse amg info from JSON fields
                try:
                    import json as _json
                    t0_amg = None
                    h_amg = None
                    if t0s and len(t0s[0]) > 2 and t0s[0][2]:
                        try:
                            t0_amg = _json.loads(t0s[0][2]).get('amg')
                        except Exception:
                            t0_amg = None
                    if h_data_json:
                        try:
                            h_amg = _json.loads(h_data_json).get('amg')
                        except Exception:
                            h_amg = None
                except Exception:
                    t0_amg = None
                    h_amg = None

                # If both sides have amg info, prefer exact shot_idx match or tail_hex match
                if t0_amg and h_amg:
                    try:
                        if t0_amg.get('shot_idx') == h_amg.get('shot_idx') or t0_amg.get('tail_hex') == h_amg.get('tail_hex'):
                            matches.append(Match(session_id=sid, t0_seq=t0_seq, t0_ts_ms=t0_ts, hit_seq=h_seq, hit_ts_ms=h_ts, offset_ms=offset))
                            matched = True
                            # advance main hit_idx to look after this hit for next T0
                            hit_idx = look_idx + 1
                            break
                    except Exception:
                        pass

                # otherwise, if no amg info or no match, fall back to earliest-hit-in-window policy
                if not t0_amg and not h_amg:
                    # accept first hit within window
                    matches.append(Match(session_id=sid, t0_seq=t0_seq, t0_ts_ms=t0_ts, hit_seq=h_seq, hit_ts_ms=h_ts, offset_ms=offset))
                    matched = True
                    hit_idx = look_idx + 1
                    break

                look_idx += 1
            # if not matched, continue to next T0
            if not matched:
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
