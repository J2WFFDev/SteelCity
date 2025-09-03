#!/usr/bin/env python3
"""Compute offsets between T0 and the next HIT per session and summarize distribution.
Usage: python tools/compute_offsets.py /path/to/bridge.db [max_lag_ms]
If max_lag_ms is provided, also write matches.csv with matched pairs within that lag.
"""
import sqlite3, sys, csv
from collections import defaultdict

if len(sys.argv) < 2:
    print('Usage: compute_offsets.py /path/to/bridge.db [max_lag_ms]')
    raise SystemExit(2)

db = sys.argv[1]
max_lag = float(sys.argv[2]) if len(sys.argv) > 2 else None
con = sqlite3.connect(db)
cur = con.cursor()
rows = cur.execute("select session_id, seq, ts_ms, msg from events where msg in ('T0','HIT') order by ts_ms").fetchall()
per = defaultdict(lambda: {'t0': [], 'hit': []})
for sid, seq, ts, msg in rows:
    per[sid or ''][msg.lower()].append((seq, ts))

all_offsets = []
matches = []
for sid, lists in per.items():
    t0s = lists['t0']
    hits = lists['hit']
    hit_idx = 0
    for t0_seq, t0_ts in t0s:
        # advance until first hit after t0
        while hit_idx < len(hits) and hits[hit_idx][1] <= t0_ts:
            hit_idx += 1
        if hit_idx >= len(hits):
            break
        candidate_seq, candidate_ts = hits[hit_idx]
        offset = candidate_ts - t0_ts
        all_offsets.append(offset)
        matches.append((sid, t0_seq, t0_ts, candidate_seq, candidate_ts, offset))
        hit_idx += 1

print('Total T0s considered:', len(all_offsets))
if not all_offsets:
    print('No T0-HIT pairs found.')
    raise SystemExit(0)

# Basic stats
import math
n = len(all_offsets)
mean = sum(all_offsets)/n
var = sum((x-mean)**2 for x in all_offsets)/n
std = math.sqrt(var)
print(f'Mean offset: {mean:.1f} ms, std: {std:.1f} ms, min: {min(all_offsets):.1f}, max: {max(all_offsets):.1f}')

# Simple histogram buckets
buckets = [0,50,100,200,500,1000,2000,5000,10000]
hist = {b:0 for b in buckets}
for v in all_offsets:
    for b in buckets:
        if v <= b:
            hist[b]+=1
            break
print('\nHistogram (<=ms):')
for b in buckets:
    print(f' <={b}: {hist[b]}')

# If max_lag provided, write a CSV of matches within that lag
if max_lag is not None:
    out = 'reports/matched_t0_hit.csv'
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['session_id','t0_seq','t0_ts_ms','hit_seq','hit_ts_ms','offset_ms'])
        cnt = 0
        for m in matches:
            if m[-1] <= max_lag:
                w.writerow([m[0], m[1], f'{m[2]:.3f}', m[3], f'{m[4]:.3f}', f'{m[5]:.3f}'])
                cnt += 1
    print(f'Wrote {cnt} matches within {max_lag} ms to {out}')

print('\nSample matches (first 20):')
for m in matches[:20]:
    print(m)
con.close()
