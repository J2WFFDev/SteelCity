#!/usr/bin/env python3
# VERSION: amg_wtvb_features v0.1
import csv, sys, statistics as stat
from datetime import datetime, timedelta

def iso(t): return datetime.fromisoformat(t.replace("Z","+00:00"))

if len(sys.argv)!=4:
    print("usage: amg_wtvb_features.py amg_shots.csv wtvb_stream.csv features.csv"); exit(2)

amg_path, wtvb_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

# Load shots
shots=[]
with open(amg_path, newline="") as f:
    r=csv.DictReader(f)
    for row in r:
        # support both amg_wtvb_capture and amg_live_decode formats
        if row.get("type") and row["type"]!="shot": continue
        t = iso(row.get("utc_iso") or row.get("utc"))
        shots.append(dict(t=t, tail=row.get("tail_hex") or row.get("tail") or "", idx=int(row.get("shot_idx") or row.get("shot") or 0)))
shots.sort(key=lambda x:x["t"])

# Load WTVB
W=[]
with open(wtvb_path, newline="") as f:
    r=csv.DictReader(f)
    for row in r:
        t=iso(row["utc_iso"])
        words=[int(row[f"w{i:02d}"]) for i in range(16)]
        W.append((t, row["type_hex"], words))
W.sort(key=lambda x:x[0])

def slice_w(t0, pre_ms=300, post_ms=800):
    t_start = t0 - timedelta(milliseconds=pre_ms)
    t_end   = t0 + timedelta(milliseconds=post_ms)
    return [(t,typ,ws) for (t,typ,ws) in W if t_start<=t<=t_end], t_start

OUT = csv.writer(open(out_path,"w",newline=""))
cols = [
  "shot_utc","tail","shot_idx",
  "samples","pre_ms","post_ms",
  "peak_up_word","peak_up_delta","peak_up_at_ms",
  "peak_dn_word","peak_dn_delta","peak_dn_at_ms",
  "area_abs_sum"
]
OUT.writerow(cols)

for s in shots:
    chunk, t_start = slice_w(s["t"])
    if not chunk:
        OUT.writerow([s["t"].isoformat(), s["tail"], s["idx"], 0, 300, 800, "", "", "", "", "", "", ""])
        continue

    # baseline = median over pre-shot portion only
    pre = [ws for (t,typ,ws) in chunk if t < s["t"]]
    if not pre: pre = [chunk[0][2]]
    base = [stat.median([w[i] for w in pre]) for i in range(16)]

    peak_up = (-1, -1, None, "")   # (delta, idx, t, typ)
    peak_dn = ( 1e9, -1, None, "")
    area = 0

    for (t,typ,ws) in chunk:
        for i in range(2,15):  # payload region
            d = ws[i] - base[i]
            area += abs(d)
            if d > peak_up[0]:
                peak_up = (d, i, t, typ)
            if d < peak_dn[0]:
                peak_dn = (d, i, t, typ)

    up_dt = int((peak_up[2]-t_start).total_seconds()*1000) if peak_up[2] else ""
    dn_dt = int((peak_dn[2]-t_start).total_seconds()*1000) if peak_dn[2] else ""
    OUT.writerow([
        s["t"].isoformat(), s["tail"], s["idx"],
        len(chunk), 300, 800,
        f"w{peak_up[1]:02d}", peak_up[0], up_dt,
        f"w{peak_dn[1]:02d}", peak_dn[0], dn_dt,
        area
    ])

print(f"[features] wrote {out_path} with {len(shots)} shots.")
