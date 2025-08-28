#!/usr/bin/env python3
# VERSION: amg_wtvb_join v0.1
import csv, sys, datetime as dt

def parse_iso(s):
    return dt.datetime.fromisoformat(s.replace("Z","+00:00"))

if len(sys.argv)!=4:
    print("usage: amg_wtvb_join.py amg_shots.csv wtvb_stream.csv fused.csv"); sys.exit(2)

amg, wtvb, dst = sys.argv[1], sys.argv[2], sys.argv[3]

# Load AMG shots (compatible with amg_wtvb_capture or amg_live_decode output)
shots=[]
with open(amg, newline="") as f:
    r=csv.DictReader(f)
    for row in r:
        if "type" in row and row["type"] and row["type"]!="shot":
            if row["type"]=="string_end": continue
        shots.append(dict(t=parse_iso(row.get("utc_iso") or row.get("utc")),
                          tail=row.get("tail_hex") or row.get("tail"),
                          idx=int(row.get("shot_idx") or row.get("shot") or 0)))

# Load WTVB stream
W=[]
with open(wtvb, newline="") as f:
    r=csv.DictReader(f)
    for row in r:
        t=parse_iso(row["utc_iso"])
        words=[int(row[f"w{i:02d}"]) for i in range(16)]
        W.append((t, row["type_hex"], words))
W.sort(key=lambda x:x[0])

out = csv.writer(open(dst, "w", newline=""))
out.writerow(["shot_utc","tail","shot_idx","win_ms","samples","peak_type","peak_word","peak_delta","peak_value","peak_at_ms"])

for s in shots:
    t0 = s["t"]
    t_start = t0 - dt.timedelta(milliseconds=750)
    t_end   = t0 + dt.timedelta(milliseconds=1000)
    chunk=[w for w in W if t_start <= w[0] <= t_end]
    if not chunk:
        out.writerow([t0.isoformat(), s["tail"], s["idx"], 1750, 0, "", "", "", "", ""])
        continue
    base = chunk[0][2]
    peak_delta=-1; peak_i=-1; peak_val=None; peak_t=None; peak_type=""
    # scan words 2..14 (skip magic w00 and type w01 and trailing w15)
    for t, typ, words in chunk:
        for i in range(2,15):
            d = abs(words[i] - base[i])
            if d > peak_delta:
                peak_delta = d; peak_i = i; peak_val = words[i]; peak_t = t; peak_type = typ
    win_ms = int((t_end - t_start).total_seconds()*1000)
    dt_ms  = int((peak_t - t_start).total_seconds()*1000) if peak_t else ""
    out.writerow([t0.isoformat(), s["tail"], s["idx"], win_ms, len(chunk), peak_type, f"w{peak_i:02d}", peak_delta, peak_val, dt_ms])

print(f"[join] wrote {dst} with {len(shots)} shots.")
