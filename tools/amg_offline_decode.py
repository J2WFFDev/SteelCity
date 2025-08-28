#!/usr/bin/env python3
import csv, sys

def le16(b): return int.from_bytes(b, "little", signed=False)

def parse_frame_hex(h):
    b = bytes.fromhex(h)
    if len(b)!=14: return None
    return dict(
        b0=b[0], b1=b[1], b2=b[2], b3=b[3], b4=b[4],
        p1=le16(b[5:7]), p2=le16(b[7:9]), p3=le16(b[9:11]), p4=le16(b[11:13]),
        tail=b[13], hex=h
    )

def is_shot(f):
    # From your captures: shot frames have b1==0x03 and b2==b3 (1-based shot index),
    # with p1=Tn, p2=Δn, p3=T1, p4=Tn (dup).
    return f["b1"]==0x03 and f["b2"]==f["b3"] and f["p1"]>0

if len(sys.argv)!=3:
    print("usage: amg_offline_decode.py sniff_all.csv shot_summary.csv"); sys.exit(2)

src, dst = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(src, newline="")))
w = csv.writer(open(dst, "w", newline=""))
w.writerow(["utc_iso","tail_hex","shot_idx","T_s","split_s","first_s","hex"])

seen=set()
for r in rows:
    f = parse_frame_hex(r["hex"])
    if not f: continue
    if not is_shot(f): continue
    key = (f["tail"], f["b2"])
    if key in seen: continue
    seen.add(key)
    T, dT, T1 = f["p1"]/100.0, f["p2"]/100.0, f["p3"]/100.0
    tail_hex = f"0x{f['tail']:02x}"
    print(f"[tail {tail_hex}] shot {f['b2']:2d}: T={T:.2f}s split={dT:.2f}s first={T1:.2f}s {f['hex'][:12]}…")
    w.writerow([r["utc_iso"], tail_hex, f["b2"], f"{T:.3f}", f"{dT:.3f}", f"{T1:.3f}", f["hex"]])
