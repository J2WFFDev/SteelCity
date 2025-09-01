#!/usr/bin/env python3
import argparse, json, os, sys, collections


def read_tail(path: str, max_lines: int) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = f.readlines()
            if max_lines <= 0:
                return data
            return data[-max_lines:]
    except FileNotFoundError:
        return []


def main():
    ap = argparse.ArgumentParser(description="Summarize recent AMG events from NDJSON")
    ap.add_argument("--file", required=True, help="NDJSON path to scan")
    ap.add_argument("--tail", type=int, default=500, help="Number of lines from end to scan (default 500)")
    args = ap.parse_args()

    lines = read_tail(args.file, args.tail)
    msgs = collections.Counter()
    matches = []
    for line in lines:
        try:
            rec = json.loads(line)
        except Exception:
            continue
        msg = rec.get("msg", "") or ""
        typ = rec.get("type")
        if msg in ("T0", "SESSION_END", "amg_connected") or (
            isinstance(msg, str) and msg.startswith("AMG_")
        ) or msg == "HIT":
            msgs[msg] += 1
            matches.append(line.rstrip("\n"))

    print("SUMMARY (last {} lines):".format(args.tail))
    if not msgs:
        print("  No AMG-related events found.")
    else:
        for k, v in msgs.items():
            print(f"  {k}: {v}")
    print("-- LAST MATCHING LINES --")
    for s in matches[-20:]:
        print(s)


if __name__ == "__main__":
    main()
