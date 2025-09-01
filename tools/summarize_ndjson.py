import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple


@dataclass
class Gap:
    start_ts: float
    end_ts: float
    dur_ms: float


def parse_ndjson_lines(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for ln, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception as e:
                print(f"WARN: Failed to parse line {ln}: {e}")


def summarize(path: Path, gap_threshold_s: float = 10.0, session_filter: Optional[str] = None) -> None:
    counts = Counter()
    by_msg = Counter()
    # Use min/max across the file; records may span multiple runs where ts_ms resets
    min_ts: Optional[float] = None
    max_ts: Optional[float] = None

    # bt50 stream/gaps
    last_bt50_ts: Optional[float] = None
    bt50_count = 0
    bt50_gaps: list[Gap] = []
    bt50_intervals_ms: list[float] = []

    # status alive cadence
    last_alive_ts: Optional[float] = None
    alive_intervals_ms: list[float] = []
    alive_null_trel = 0
    alive_with_trel = 0

    # basic error inventory
    errors = Counter()

    # naive session reset detector: seq <= 10 after we've seen seq > 100
    saw_large_seq = False
    seq_resets: list[Tuple[float, int]] = []

    matched_any = False
    for rec in parse_ndjson_lines(path):
        if session_filter is not None and rec.get("session_id") != session_filter:
            continue
        matched_any = True
        ts = float(rec.get("ts_ms", 0))
        if min_ts is None or ts < min_ts:
            min_ts = ts
        if max_ts is None or ts > max_ts:
            max_ts = ts

        rtype = rec.get("type")
        counts[rtype] += 1
        msg = rec.get("msg")
        if msg:
            by_msg[msg] += 1

        # Rough session detection via seq pattern
        seq = rec.get("seq")
        if isinstance(seq, int):
            if seq > 100:
                saw_large_seq = True
            elif saw_large_seq and seq <= 10:
                seq_resets.append((ts, seq))

        # Status cadence and t_rel_ms presence
        if rtype == "status" and rec.get("msg") == "alive":
            if rec.get("t_rel_ms") is None:
                alive_null_trel += 1
            else:
                alive_with_trel += 1
            if last_alive_ts is not None:
                dt = ts - last_alive_ts
                if dt > 0:
                    alive_intervals_ms.append(dt)
            last_alive_ts = ts

        # bt50 stream cadence and gaps
        if rtype == "info" and msg == "bt50_stream":
            bt50_count += 1
            if last_bt50_ts is not None:
                dt = ts - last_bt50_ts
                if dt > 0:
                    bt50_intervals_ms.append(dt)
                if dt > gap_threshold_s * 1000.0:
                    bt50_gaps.append(Gap(last_bt50_ts, ts, dt))
            last_bt50_ts = ts

        if rtype == "error":
            emsg = rec.get("msg") or "error"
            ek = f"{emsg}:{rec.get('data', {}).get('error', '')}"
            errors[ek] += 1

    # Print summary
    print(f"File: {path}")
    if session_filter is not None:
        print(f"Session filter: {session_filter}")
    if session_filter is not None and not matched_any:
        print("No records matched the requested session_id.")
        return
    if min_ts is not None and max_ts is not None and max_ts >= min_ts:
        dur_ms = max_ts - min_ts
        print(f"Time span: {dur_ms/1000:.1f}s ({dur_ms/60000:.2f} min)")
    print("Counts by type:")
    for k in sorted(counts):
        print(f"  {k}: {counts[k]}")
    if by_msg:
        print("Top messages:")
        for k, v in by_msg.most_common(10):
            print(f"  {k}: {v}")

    if bt50_count:
        print(f"bt50_stream entries: {bt50_count}")
        if bt50_intervals_ms:
            avg_bt50_dt = sum(bt50_intervals_ms) / len(bt50_intervals_ms)
            print(f"  avg interval: {avg_bt50_dt:.1f} ms")
        print(f"  gaps > {gap_threshold_s:.0f}s: {len(bt50_gaps)}")
        if bt50_gaps:
            biggest = max(bt50_gaps, key=lambda g: g.dur_ms)
            print(f"  biggest gap: {biggest.dur_ms/1000:.1f}s starting at ts≈{biggest.start_ts:.0f}")

    if alive_intervals_ms:
        avg_alive_dt = sum(alive_intervals_ms) / len(alive_intervals_ms)
        print(f"status/alive cadence: avg {avg_alive_dt:.1f} ms")
        print(f"  alive with t_rel_ms: {alive_with_trel}, null t_rel_ms: {alive_null_trel}")

    if errors:
        print("Errors (grouped):")
        for k, v in errors.most_common(10):
            print(f"  {k[:100]}: {v}")

    if seq_resets:
        print(f"Potential session restarts (seq reset detected): {len(seq_resets)}")
        for ts, seq in seq_resets[:5]:
            print(f"  ts≈{ts:.0f} seq={seq}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Summarize SteelCity NDJSON logs")
    ap.add_argument("path", type=Path, help="Path to bridge_YYYYMMDD.ndjson")
    ap.add_argument("--gap-sec", type=float, default=10.0, help="Gap threshold seconds for bt50 stream")
    ap.add_argument("--session", type=str, default=None, help="Only include records with this session_id")
    args = ap.parse_args()
    summarize(args.path, gap_threshold_s=args.gap_sec, session_filter=args.session)


if __name__ == "__main__":
    main()
