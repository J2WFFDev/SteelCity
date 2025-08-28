#!/usr/bin/env python3
import csv, sys, math, datetime as dt
def iso(s): return dt.datetime.fromisoformat(s.replace("Z","+00:00"))

if len(sys.argv) < 3:
    print("usage: events_from_csv.py decoded.csv events.csv [thr=120] [gap_s=0.20] [hz=25]")
    sys.exit(2)

src, dst = sys.argv[1], sys.argv[2]
thr   = float(sys.argv[3]) if len(sys.argv)>3 else 120.0
gap_s = float(sys.argv[4]) if len(sys.argv)>4 else 0.20
hz    = float(sys.argv[5]) if len(sys.argv)>5 else 25.0

rows = list(csv.DictReader(open(src, newline="")))
events, cur = [], None
prev_t = None

for r in rows:
    try:
        t = iso(r["utc_iso"])
        mag = float(r["mag"])
    except Exception:
        continue

    # end event if quiet too long since last above-threshold sample
    if cur and prev_t and (t - cur["t_last"]).total_seconds() >= gap_s and mag <= thr:
        # finalize
        if cur["n"] == 1:
            dur = 1.0/hz
            area = cur["first_mag"] * dur
            mean = rms = cur["first_mag"]
        else:
            dur  = (cur["t_last"] - cur["t0"]).total_seconds()
            mean = (cur["tw"] > 0) and (cur["area"] / cur["tw"]) or 0.0
            rms  = (cur["tw"] > 0) and math.sqrt(cur["tw2"] / cur["tw"]) or 0.0
            area = cur["area"]
        events.append({
            "start": cur["t0"], "end": cur["t_last"], "dur": dur, "n": cur["n"],
            "type_hex": cur["type_hex"], "max": cur["max"], "tmax": cur["tmax"],
            "dx": cur["dx"], "dy": cur["dy"], "dz": cur["dz"],
            "mean": mean, "rms": rms, "area": area
        })
        cur = None

    if mag > thr:
        if not cur:
            cur = dict(t0=t, t_last=t, n=0, first_mag=mag,
                       area=0.0, tw=0.0, tw2=0.0,
                       max=0.0, tmax=t, dx="0", dy="0", dz="0",
                       type_hex=r.get("type_hex",""))
        cur["n"] += 1
        if cur["n"] > 1:
            dt_s = (t - cur["prev_t"]).total_seconds()
            cur["area"] += 0.5 * (mag + cur["prev_mag"]) * dt_s
            cur["tw"]   += dt_s
            cur["tw2"]  += 0.5 * (mag*mag + cur["prev_mag"]*cur["prev_mag"]) * dt_s
        if mag > cur["max"]:
            cur["max"] = mag; cur["tmax"] = t
            cur["dx"], cur["dy"], cur["dz"] = r["d08"], r["d09"], r["d10"]
        cur["prev_t"], cur["prev_mag"] = t, mag
        cur["t_last"] = t

    prev_t = t

# handle trailing open event
if cur:
    if cur["n"] == 1:
        dur = 1.0/hz
        area = cur["first_mag"] * dur
        mean = rms = cur["first_mag"]
    else:
        dur  = (cur["t_last"] - cur["t0"]).total_seconds()
        mean = (cur["tw"] > 0) and (cur["area"] / cur["tw"]) or 0.0
        rms  = (cur["tw"] > 0) and math.sqrt(cur["tw2"] / cur["tw"]) or 0.0
        area = cur["area"]
    events.append({
        "start": cur["t0"], "end": cur["t_last"], "dur": dur, "n": cur["n"],
        "type_hex": cur["type_hex"], "max": cur["max"], "tmax": cur["tmax"],
        "dx": cur["dx"], "dy": cur["dy"], "dz": cur["dz"],
        "mean": mean, "rms": rms, "area": area
    })

with open(dst,"w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["start_iso","end_iso","dur_s","n","type_hex",
                "max_mag","t_at_max","d08","d09","d10","mean","rms","area"])
    for e in events:
        w.writerow([e["start"].isoformat(), e["end"].isoformat(), f"{e['dur']:.3f}",
                    e["n"], e["type_hex"], f"{e['max']:.1f}", e["tmax"].isoformat(),
                    e["dx"], e["dy"], e["dz"], f"{e['mean']:.1f}", f"{e['rms']:.1f}", f"{e['area']:.1f}"])
print(f"[events] wrote {dst} with {len(events)} events (thr={thr}, gap={gap_s}s)")
