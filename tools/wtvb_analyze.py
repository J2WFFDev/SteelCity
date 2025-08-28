#!/usr/bin/env python3
# VERSION: wtvb_analyze v0.1
import csv, sys, statistics as stat
from collections import Counter, defaultdict
from datetime import datetime, timezone

def iso(t): return datetime.fromisoformat(t.replace("Z","+00:00"))

if len(sys.argv)!=2:
    print("usage: wtvb_analyze.py wtvb_stream.csv"); exit(2)

path = sys.argv[1]
rows = list(csv.DictReader(open(path, newline="")))
if not rows:
    print("[info] empty file"); exit(0)

# Count message types
types = Counter(r["type_hex"] for r in rows)
print("--- WTVB message types ---")
for t,c in sorted(types.items(), key=lambda x:-x[1]): print(f"{t} {c}")

# Rough sampling period for the most common type
main_type = max(types, key=types.get)
times = [iso(r["utc_iso"]) for r in rows if r["type_hex"]==main_type]
if len(times) > 5:
    dts = [(t2-t1).total_seconds() for t1,t2 in zip(times, times[1:])]
    dts = [d for d in dts if d>0]
    if dts:
        avg = sum(dts)/len(dts)
        print(f"\n[rate] dominant type {main_type}: ~{1/avg:.1f} Hz (avg Δ={avg*1000:.0f} ms)")
print("\n--- per-word variability (overall) ---")
# Words are w00..w15 in columns 3..18
vals = defaultdict(list)
for r in rows:
    for i in range(16):
        vals[i].append(int(r[f"w{i:02d}"]))
for i in range(16):
    v = vals[i]
    mean = sum(v)/len(v)
    sd = (stat.pstdev(v) if len(v)>1 else 0.0)
    print(f"w{i:02d} mean={mean:.1f} sd={sd:.1f}")

print("\n--- top movers (sd desc, ignore magic/type/trailer) ---")
cands = [(i, stat.pstdev(vals[i])) for i in range(2,15)]
for i,sd in sorted(cands, key=lambda x:-x[1])[:6]:
    print(f"w{i:02d} sd={sd:.1f}")
