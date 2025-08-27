#!/usr/bin/env python3
import asyncio, argparse, datetime as dt, csv, os
from bleak import BleakScanner, BleakClient

def now_iso():
    return dt.datetime.utcnow().isoformat(timespec="milliseconds")+"Z"

def le16(b): return int.from_bytes(b, "little", signed=False)

def parse14(b: bytes):
    if len(b)!=14: return None
    tag = b[0]
    b1,b2,b3,b4 = b[1:5]
    n = b2  # shot index (b2==b3 in logs)
    p1 = le16(b[5:7])   # absolute Tn (centiseconds)
    p2 = le16(b[7:9])   # split Δn (centiseconds)
    p3 = le16(b[9:11])  # first shot time T1
    p4 = le16(b[11:13]) # dup of Tn
    tail = b[13]
    return dict(tag=tag, b1=b1, n=n, p1=p1, p2=p2, p3=p3, p4=p4, tail=tail, hex=b.hex())

async def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--mac")
    g.add_argument("--name", default="AMG")
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--ctl", dest="ctl_uuid", default="6e400003-b5a3-f393-e0a9-e50e24dcca9e")
    ap.add_argument("--secs", type=float, default=3600.0, help="listen duration")
    ap.add_argument("--csv", help="optional summary CSV (tail,n,T,split,first,hex)")
    args = ap.parse_args()

    # CSV setup (optional)
    w = None
    if args.csv:
        need_header = not os.path.exists(args.csv) or os.stat(args.csv).st_size==0
        f = open(args.csv, "a", newline="")
        w = csv.writer(f)
        if need_header:
            w.writerow(["utc_iso","tail_hex","shot_n","T_s","split_s","first_s","hex"])

    # find device
    dev = None
    if args.mac:
        dev = await BleakScanner.find_device_by_address(args.mac, cb=dict(use_bdaddr=False))
    else:
        for d in await BleakScanner.discover(adapter=args.adapter, timeout=8.0):
            if args.name.lower() in (d.name or "").lower():
                dev = d; break
    if not dev:
        raise SystemExit("device not found")

    print(f"[ble] connect {dev.address} ({dev.name}) …")
    async with BleakClient(dev, timeout=20.0, device=args.adapter) as client:
        seen = set()  # (tail, n)
        async def cb(_, data: bytearray):
            b = bytes(data)
            if len(b)!=14: return
            p = parse14(b)
            key = (p["tail"], p["n"])
            if key in seen:  # only first time per shot index
                return
            seen.add(key)
            T = p["p1"]/100.0
            d = p["p2"]/100.0
            f1 = p["p3"]/100.0
            print(f"[tail 0x{p['tail']:02x}] shot {p['n']:2d}:  T={T:.2f}s  split={d:.2f}s  first={f1:.2f}s  {p['hex']}")
            if w:
                w.writerow([now_iso(), f"0x{p['tail']:02x}", p["n"], f"{T:.2f}", f"{d:.2f}", f"{f1:.2f}", p["hex"]])

        # subscribe
        print(f"[sub] {args.ctl_uuid}")
        await client.start_notify(args.ctl_uuid, cb)
        print("[listening] press Start/beep/shoot/arrow on the AMG; Ctrl+C to stop early")
        try:
            await asyncio.sleep(args.secs)
        except KeyboardInterrupt:
            pass
        finally:
            try: await client.stop_notify(args.ctl_uuid)
            except: pass
