#!/usr/bin/env python3
import csv, sys, collections

path = sys.argv[1] if len(sys.argv)>1 else "amg_log.csv"
by_tail = collections.defaultdict(list)

def h2i(x): return int(x,16)

with open(path, newline="") as f:
    r = csv.DictReader(f)
    for row in r:
        if row.get("type") != "frame": 
            continue
        # header bytes b2/b3 both equal the shot index in your captures
        try:
            n = h2i(row["b2"])
        except Exception:
            continue
        tail = row["tail_hex"]
        p1 = int(row["p1"]); p2 = int(row["p2"]); p3 = int(row["p3"]); p4 = int(row["p4"])
        by_tail[tail].append((n, p1, p2, p3, p4, row["hex"]))

for tail, items in sorted(by_tail.items()):
    items.sort(key=lambda x: x[0])
    print(f"\n=== tail {tail} (string since power-on) ===")
    for n,p1,p2,p3,p4,hexstr in items:
        print(f"  shot {n:2d}:  T={p1/100:.2f}s  split={p2/100:.2f}s  first={p3/100:.2f}s  (dup={p4/100:.2f}s)  {hexstr}")
