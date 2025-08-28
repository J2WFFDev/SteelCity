#!/usr/bin/env python3
# Decode WTVB01 records saved by amg_sniff_all.py into a friendlier CSV
import csv, sys, struct

def s16(u): return struct.unpack('<h', struct.pack('<H', u))[0]
def parse_5561(h):
    b = bytes.fromhex(h)
    if len(b) < 28 or b[0]!=0x55 or b[1]!=0x61: return None
    vals = struct.unpack_from('<' + 'H'*13, b, 2)
    (VXL,VYL,VZL, ADXL,ADYL,ADZL, TEMPL,
     DXL,DYL,DZL, HZXL,HZYL,HZZL) = vals
    VX,VY,VZ = s16(VXL), s16(VYL), s16(VZL)
    ADX,ADY,ADZ = s16(ADXL)/32768*180, s16(ADYL)/32768*180, s16(ADZL)/32768*180
    TEMP = s16(TEMPL)/100.0
    DX,DY,DZ = s16(DXL), s16(DYL), s16(DZL)
    HZX,HZY,HZZ = s16(HZXL), s16(HZYL), s16(HZZL)
    return dict(VX=VX,VY=VY,VZ=VZ,ADX=ADX,ADY=ADY,ADZ=ADZ,TEMP=TEMP,
                DX=DX,DY=DY,DZ=DZ,HZX=HZX,HZY=HZY,HZZ=HZZ)

if len(sys.argv)!=3:
    print("usage: wtvb_offline_decode.py wtvb_sniff.csv out.csv"); sys.exit(2)

src, dst = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(src, newline="")))
w = csv.writer(open(dst, "w", newline=""))
w.writerow(["utc_iso","VX_mm_s","VY_mm_s","VZ_mm_s",
            "ADX_deg","ADY_deg","ADZ_deg","TEMP_C",
            "DX_um","DY_um","DZ_um","HZX_Hz","HZY_Hz","HZZ_Hz","raw_hex"])

for r in rows:
    pkt = parse_5561(r["hex"])
    if not pkt: continue
    w.writerow([r["utc_iso"], pkt["VX"], pkt["VY"], pkt["VZ"],
                f"{pkt['ADX']:.3f}", f"{pkt['ADY']:.3f}", f"{pkt['ADZ']:.3f}", f"{pkt['TEMP']:.2f}",
                pkt["DX"], pkt["DY"], pkt["DZ"], pkt["HZX"], pkt["HZY"], pkt["HZZ"], r["hex"]])
print("[ok] wrote", dst)
