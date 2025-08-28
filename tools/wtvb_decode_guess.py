#!/usr/bin/env python3
import csv, sys
from datetime import datetime, timezone
def iso(s): return datetime.fromisoformat(s.replace("Z","+00:00"))
def s16(x): 
    x=int(x); 
    return x-65536 if x>=32768 else x

if len(sys.argv)!=2:
    print("usage: wtvb_decode_guess.py wtvb_stream.csv"); sys.exit(2)

rows=list(csv.DictReader(open(sys.argv[1], newline="")))
print("utc_iso           type  w08  w09  w10   (signed ints)")
for r in rows[:200]:
    t=r["utc_iso"]; typ=r["type_hex"]
    w8,w9,w10 = s16(r["w08"]), s16(r["w09"]), s16(r["w10"])
    print(f"{t} {typ:>6} {w8:5d} {w9:5d} {w10:5d}")
