#!/usr/bin/env python3
"""
watch_events.py — follow a decoded CSV and print event summaries.

Usage:
  python tools/watch_events.py decoded.csv [--thr 120] [--gap-s 0.20] [--hz 25]
Optional (handy for testing offline files):
  --from-start        process existing rows from the beginning (skip header)
  --exit-on-eof       stop when file ends (instead of following)
Output (CSV header once, then one line per event):
  start_utc,end_utc,duration_s,count,max_mag,peak_w08,peak_w09,peak_w10,peak_d08,peak_d09,peak_d10,peak_utc
Notes:
  - Expects the decoder's columns: utc_iso,w08,w09,w10,d08,d09,d10,mag,...
  - Gap closes an event when time since last >thr sample exceeds --gap-s seconds.
  - Follows file rotation/truncation like `tail -F`.
"""

from __future__ import annotations
import argparse, csv, os, time, sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Iterator, Tuple

DEF_THR = 120.0
DEF_GAP = 0.20
DEF_HZ  = 25.0

def _err(msg: str) -> None:
    sys.stderr.write(msg.rstrip() + "\n")

def _parse_iso_utc(s: str) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip()
    # accept '...Z' or '...+00:00' or naive (treat as UTC)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def _iso_z(dt: datetime) -> str:
    # 'YYYY-MM-DDTHH:MM:SS.mmmZ' (millisecond precision)
    s = dt.astimezone(timezone.utc).isoformat(timespec="milliseconds")
    return s.replace("+00:00", "Z")

def _follow_lines(path: str, from_start: bool, exit_on_eof: bool, poll: float = 0.10) -> Iterator[str]:
    """Generator yielding lines as they appear; handles rotation/truncation."""
    fd = None
    inode = None
    pos = 0
    def _open():
        nonlocal fd, inode, pos
        fd = open(path, "r", encoding="utf-8", newline="")
        st = os.fstat(fd.fileno())
        inode = (st.st_dev, st.st_ino)
        pos = 0
        # skip header when from_start; otherwise start at EOF
        first = fd.readline()
        if not from_start:
            # jump to end for tailing
            fd.seek(0, os.SEEK_END)
        else:
            # already consumed header; start at current position
            pos = fd.tell()

    def _rotated() -> bool:
        try:
            st = os.stat(path)
        except FileNotFoundError:
            return True
        return (st.st_dev, st.st_ino) != inode

    _open()
    buf = ""
    while True:
        line = fd.readline()
        if line:
            pos = fd.tell()
            yield line
            continue

        # EOF
        if exit_on_eof:
            break

        # rotation or truncation?
        try:
            st_now = os.stat(path)
            st_fd  = os.fstat(fd.fileno())
            if (st_now.st_size < pos) or ((st_now.st_dev, st_now.st_ino) != (st_fd.st_dev, st_fd.st_ino)):
                try:
                    fd.close()
                except Exception:
                    pass
                _open()
        except FileNotFoundError:
            # wait for file to reappear
            time.sleep(poll)
            continue

        time.sleep(poll)

@dataclass
class Event:
    start: datetime
    end: datetime
    count: int
    max_mag: float
    peak_w08: int
    peak_w09: int
    peak_w10: int
    peak_d08: int
    peak_d09: int
    peak_d10: int
    peak_utc: datetime

def _new_event(ts: datetime, w08:int,w09:int,w10:int,d08:int,d09:int,d10:int,mag:float) -> Event:
    return Event(
        start=ts, end=ts, count=1, max_mag=mag,
        peak_w08=w08, peak_w09=w09, peak_w10=w10,
        peak_d08=d08, peak_d09=d09, peak_d10=d10,
        peak_utc=ts
    )

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Watch decoded CSV and emit event summaries.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("decoded_csv", help="Path to decoded CSV (from wtvb_decode_5561.py)")
    ap.add_argument("--thr", type=float, default=DEF_THR, help="Magnitude threshold to enter/continue an event")
    ap.add_argument("--gap-s", type=float, default=DEF_GAP, help="Seconds below threshold to close an event")
    ap.add_argument("--hz", type=float, default=DEF_HZ, help="Nominal stream rate (used for sanity; timestamps still drive gaps)")
    ap.add_argument("--from-start", action="store_true", help="Process existing rows from file start (skip header), then follow")
    ap.add_argument("--exit-on-eof", action="store_true", help="Exit when EOF reached (pair with --from-start for offline summary)")
    args = ap.parse_args(argv)

    # Print header
    print("start_utc,end_utc,duration_s,count,max_mag,peak_w08,peak_w09,peak_w10,peak_d08,peak_d09,peak_d10,peak_utc", flush=True)

    cur: Optional[Event] = None
    last_above: Optional[datetime] = None

    # Skip the first CSV header line by letting _follow_lines consume it internally.
    for line in _follow_lines(args.decoded_csv, from_start=args.from_start, exit_on_eof=args.exit_on_eof):
        line = line.strip()
        if not line:
            continue
        # naive CSV split (decoder outputs no quoted commas)
        parts = line.split(",")
        # Heuristic: header or short line → skip
        if parts[0].lower().startswith("utc_iso") or len(parts) < 14:
            continue
        try:
            utc_iso = parts[0]
            ts = _parse_iso_utc(utc_iso)
            if ts is None:
                raise ValueError("bad timestamp")
            # indices per decoder schema
            w08 = int(parts[2]); w09 = int(parts[3]); w10 = int(parts[4])
            d08 = int(parts[5]); d09 = int(parts[6]); d10 = int(parts[7])
            mag = float(parts[8])
        except Exception as e:
            _err(f"skip line: {e}: {line[:120]}")
            continue

        if mag > args.thr:
            if cur is None:
                cur = _new_event(ts, w08,w09,w10,d08,d09,d10,mag)
            else:
                cur.end = ts
                cur.count += 1
                if mag > cur.max_mag:
                    cur.max_mag = mag
                    cur.peak_w08,cur.peak_w09,cur.peak_w10 = w08,w09,w10
                    cur.peak_d08,cur.peak_d09,cur.peak_d10 = d08,d09,d10
                    cur.peak_utc = ts
            last_above = ts
        else:
            # below threshold; close if we’ve been quiet long enough
            if cur is not None and last_above is not None:
                quiet = (ts - last_above).total_seconds()
                if quiet > args.gap_s:
                    dur = (cur.end - cur.start).total_seconds() if cur.count > 1 else 0.0
                    print(",".join([
                        _iso_z(cur.start),
                        _iso_z(cur.end),
                        f"{dur:.3f}",
                        str(cur.count),
                        f"{cur.max_mag:.1f}",
                        str(cur.peak_w08), str(cur.peak_w09), str(cur.peak_w10),
                        str(cur.peak_d08), str(cur.peak_d09), str(cur.peak_d10),
                        _iso_z(cur.peak_utc),
                    ]), flush=True)
                    cur = None
                    last_above = None
            # else: still waiting for an event to start or gap not exceeded

    # EOF cleanup if user asked to exit
    if args.exit_on_eof and cur is not None:
        dur = (cur.end - cur.start).total_seconds() if cur.count > 1 else 0.0
        print(",".join([
            _iso_z(cur.start),
            _iso_z(cur.end),
            f"{dur:.3f}",
            str(cur.count),
            f"{cur.max_mag:.1f}",
            str(cur.peak_w08), str(cur.peak_w09), str(cur.peak_w10),
            str(cur.peak_d08), str(cur.peak_d09), str(cur.peak_d10),
            _iso_z(cur.peak_utc),
        ]), flush=True)

    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass
