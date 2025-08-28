#!/usr/bin/env python3
# VERSION: wtvb_offline_dump v0.1
import csv, sys, datetime as dt

def le16(b): return int.from_bytes(b, "little", signed=False)
def words_from_hex(h):
    b = bytes.fromhex(h)
    if len(b)!=32 or b[0]!=0x55 or b[1]!=0x61: return None
    return [le16(b[i:i+2]) for i in range(2, 32, 2)]  # 15 words

if len(sys.argv)!=2:
    print("usage: wtvb_offline_dump.py wtvb_sniff.csv"); sys.exit(2)

src = sys.argv[1]
rows = list(csv.DictReader(open(src, newline="")))
if not rows:
    print("[info] empty file"); sys.exit(0)

print("# utc_iso w0..w14  (last column: changed indices)")
last=None
from collections import Counter
c_w14=Counter(); c_w12=Counter(); c_w6=Counter()

for r in rows:
    h = r["hex"].strip()
    ws = words_from_hex(h)
    if not ws: continue
    c_w14[ws[14]] += 1
    c_w12[ws[12]] += 1
    c_w6[ws[6]] += 1
    diffs=[]
    if last:
        diffs=[str(i) for i,(a,b) in enumerate(zip(last,ws)) if a!=b]
    last=ws
    print(f"{r['utc_iso']}  {ws}  Δ[{','.join(diffs)}]")

print("\n--- field frequencies ---")
def top5(c):
    return ", ".join(f"{k}:{v}" for k,v in c.most_common(5))
print("w14 (tail/foot?):", top5(c_w14))
print("w12 (mode/subtype?):", top5(c_w12))
print("w6  (primary reading?):", top5(c_w6))
