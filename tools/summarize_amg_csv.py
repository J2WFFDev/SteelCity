#!/usr/bin/env python3
import csv, sys
from collections import defaultdict

if len(sys.argv) != 2:
    print("usage: summarize_amg_csv.py <shot_summary.csv>"); sys.exit(2)
path = sys.argv[1]

try:
    with open(path, newline="") as f:
        r = list(csv.DictReader(f))
except FileNotFoundError:
    print(f"[err] not found: {path}"); sys.exit(2)

if not r:
    print("[info] empty file"); sys.exit(0)

by_tail = defaultdict(list)
for row in r:
    by_tail[row["tail_hex"]].append(row)

for tail in sorted(by_tail.keys()):
    print(f"=== tail {tail} (string since power-on) ===")
    rows = sorted(by_tail[tail], key=lambda x: int(x["shot_idx"]))
    for row in rows:
        print(f"  shot {int(row['shot_idx']):2d}:  T={float(row['T_s']):.2f}s  split={float(row['split_s']):.2f}s  first={float(row['first_s']):.2f}s  {row['hex'][:12]}…")
    print()
