#!/usr/bin/env python3
# VERSION: wtvb_extract_wit_frames v0.1
import csv, sys

TYPES = {
    0x50:"TIME", 0x51:"ACC",  0x52:"GYRO", 0x53:"ANGLE",
    0x54:"MAG",  0x55:"PORT", 0x56:"PRESS",0x57:"LL",
    0x58:"VEL",  0x59:"QUAT", 0x5A:"GPSACC",0x5F:"READ",
}

def int16(lo, hi):
    v = (hi << 8) | lo
    return v - 65536 if v >= 32768 else v

def scan_frames(b: bytes):
    """Find valid 11-byte WIT frames (0x55 TYPE d0..d3 SUM) inside bytes b."""
    out = []
    n = len(b)
    for i in range(0, n - 10):
        if b[i] != 0x55: 
            continue
        typ = b[i+1]
        if typ not in TYPES:
            continue
        if (sum(b[i:i+10]) & 0xFF) == b[i+10]:
            out.append((i, bytes(b[i:i+11])))
    return out

def decode_frame(fr: bytes):
    """Return (type_code, type_name, dict_of_fields) for a valid 11-byte frame."""
    typ = fr[1]
    name = TYPES.get(typ, f"0x{typ:02X}")
    d = [int16(fr[2], fr[3]), int16(fr[4], fr[5]), int16(fr[6], fr[7]), int16(fr[8], fr[9])]
    if   typ == 0x51:  # ACC -> g, temp C
        ax, ay, az, t = d
        return typ, name, dict(ax_g=ax/32768*16, ay_g=ay/32768*16, az_g=az/32768*16, temp_c=t/100)
    elif typ == 0x52:  # GYRO -> °/s, volt
        wx, wy, wz, v = d
        return typ, name, dict(wx_dps=wx/32768*2000, wy_dps=wy/32768*2000, wz_dps=wz/32768*2000, volt=v/100)
    elif typ == 0x53:  # ANGLE -> °
        r, p, y, ver = d
        return typ, name, dict(roll_deg=r/32768*180, pitch_deg=p/32768*180, yaw_deg=y/32768*180, ver=ver)
    elif typ == 0x59:  # QUAT -> unitless
        q0, q1, q2, q3 = d
        return typ, name, dict(q0=q0/32768, q1=q1/32768, q2=q2/32768, q3=q3/32768)
    else:
        return typ, name, {f"d{i+1}": d[i] for i in range(4)}

def words16_to_bytes_le(words):
    b = bytearray()
    for w in words:
        b.append(w & 0xFF)
        b.append((w >> 8) & 0xFF)
    return bytes(b)

def main():
    if len(sys.argv) != 3:
        print("usage: wtvb_extract_wit_frames.py wtvb_stream.csv decoded.csv"); sys.exit(2)
    src, dst = sys.argv[1], sys.argv[2]

    rows = list(csv.DictReader(open(src, newline="")))
    out = csv.writer(open(dst, "w", newline=""))
    out.writerow(["utc_iso","embed_off","type_code","type_name","fields","raw_hex"])

    n_frames = 0
    for r in rows:
        words = [int(r[f"w{i:02d}"]) for i in range(16)]
        blob = words16_to_bytes_le(words)
        for off, fr in scan_frames(blob):
            typ, name, vals = decode_frame(fr)
            out.writerow([r["utc_iso"], off, f"0x{typ:02X}", name, vals, fr.hex()])
            n_frames += 1

    print(f"[extract] wrote {dst} with {n_frames} embedded WIT frames.")

if __name__ == "__main__":
    main()
