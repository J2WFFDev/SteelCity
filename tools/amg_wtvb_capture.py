#!/usr/bin/env python3
# VERSION: amg_wtvb_capture v0.1
import asyncio, argparse, csv, datetime as dt, os
from bleak import BleakScanner, BleakClient

def now_iso():
    return dt.datetime.utcnow().isoformat(timespec="milliseconds")+"Z"

# ---------- AMG (14 bytes) ----------
def le16(b): return int.from_bytes(b,"little",signed=False)
def le32(b): return int.from_bytes(b,"little",signed=False)

def parse_amg_frame(b: bytes):
    if len(b)!=14: return None
    return dict(
        b0=b[0], b1=b[1], b2=b[2], b3=b[3], b4=b[4],
        p1=le16(b[5:7]), p2=le16(b[7:9]), p3=le16(b[9:11]), p4=le16(b[11:13]),
        tail=b[13], hex=b.hex(), secs=le32(b[1:5])
    )

def amg_is_shot(f):
    # shot frames: b1==0x03 and b2==b3 (1-based index); p1=Tn, p2=Δn, p3=T1, p4=Tn(dup)
    return f["b1"]==0x03 and f["b2"]==f["b3"] and f["p1"]>0

# ---------- WTVB (32 bytes) ----------
def parse_wtvb_words(b: bytes):
    if len(b)!=32: return None
    words = [int.from_bytes(b[i:i+2],"little",signed=False) for i in range(0,32,2)]
    # words[0] is magic 0x6155; words[1] looks like a "type" code that changes
    return dict(words=words, hex=b.hex(), type=words[1])

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="hci0")
    # AMG
    ap.add_argument("--amg-mac", default="60:09:C3:1F:DC:1A")
    ap.add_argument("--amg-ctl", default="6e400003-b5a3-f393-e0a9-e50e24dcca9e")
    # WTVB
    ap.add_argument("--wtvb-mac", default="F8:FE:92:31:12:E3")
    ap.add_argument("--wtvb-ctl", default="0000ffe4-0000-1000-8000-00805f9a34fb")
    # Files
    ap.add_argument("--shots-csv", default=os.path.expanduser("~/projects/steelcity/amg_shots.csv"))
    ap.add_argument("--wtvb-csv",  default=os.path.expanduser("~/projects/steelcity/wtvb_stream.csv"))
    ap.add_argument("--secs", type=float, default=120.0)
    args = ap.parse_args()

    print("[version] amg_wtvb_capture v0.1")

    # writers
    shots_fp = open(args.shots_csv, "w", newline=""); shots_w = csv.writer(shots_fp)
    shots_w.writerow(["utc_iso","tail_hex","shot_idx","T_s","split_s","first_s","hex"])
    wtvb_fp = open(args.wtvb_csv, "w", newline=""); wtvb_w = csv.writer(wtvb_fp)
    wtvb_w.writerow(["utc_iso","type_hex"] + [f"w{i:02d}" for i in range(16)] + ["hex"])

    amg_client = BleakClient(args.amg_mac, timeout=20.0, device=args.adapter)
    wtvb_client = BleakClient(args.wtvb_mac, timeout=20.0, device=args.adapter)

    async def amg_cb(_, data:bytearray):
        f = parse_amg_frame(bytes(data))
        if not f: return
        if amg_is_shot(f):
            T  = f["p1"]/100.0
            dT = f["p2"]/100.0
            T1 = f["p3"]/100.0
            tail_hex = f"0x{f['tail']:02x}"
            print(f"[AMG tail {tail_hex}] shot {f['b2']:2d}: T={T:.2f}s split={dT:.2f}s first={T1:.2f}s {f['hex'][:12]}…")
            shots_w.writerow([now_iso(), tail_hex, f["b2"], f"{T:.3f}", f"{dT:.3f}", f"{T1:.3f}", f["hex"]])
            shots_fp.flush()

    async def wtvb_cb(_, data:bytearray):
        p = parse_wtvb_words(bytes(data))
        if not p: return
        type_hex = f"0x{p['type']:04x}"
        row = [now_iso(), type_hex] + p["words"] + [p["hex"]]
        wtvb_w.writerow(row); wtvb_fp.flush()

    print(f"[ble] connect AMG {args.amg_mac} …")
    await amg_client.connect()
    print(f"[ble] connect WTVB {args.wtvb_mac} …")
    await wtvb_client.connect()
    try:
        print(f"[sub] AMG {args.amg_ctl}")
        await amg_client.start_notify(args.amg_ctl, amg_cb)
        print(f"[sub] WTVB {args.wtvb_ctl}")
        await wtvb_client.start_notify(args.wtvb_ctl, wtvb_cb)
        print("[live] capturing both streams… (Ctrl+C to stop)")
        try:
            await asyncio.sleep(args.secs)
        except KeyboardInterrupt:
            pass
    finally:
        try: await amg_client.disconnect()
        except: pass
        try: await wtvb_client.disconnect()
        except: pass
        shots_fp.close(); wtvb_fp.close()
        print("[done] wrote:")
        print("  -", args.shots_csv)
        print("  -", args.wtvb_csv)

if __name__ == "__main__":
    asyncio.run(main())
