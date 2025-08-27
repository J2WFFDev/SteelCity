#!/usr/bin/env python3
import asyncio, argparse, datetime as dt, csv, os
from bleak import BleakScanner, BleakClient

def now_ms():
    return dt.datetime.utcnow().isoformat(timespec="milliseconds")+"Z"

async def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--mac")
    g.add_argument("--name", default="AMG")
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--secs", type=float, default=30.0)
    ap.add_argument("--csv", default="sniff_all.csv")
    args = ap.parse_args()

    if os.path.exists(args.csv) and os.stat(args.csv).st_size == 0:
        pass
    header_needed = not os.path.exists(args.csv) or os.stat(args.csv).st_size == 0
    f = open(args.csv, "a", newline="")
    w = csv.writer(f)
    if header_needed:
        w.writerow(["utc_iso","uuid","len","hex"])

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
        # subscribe to all notify/indicate chars
        subs = []
        for svc in client.services:
            for ch in svc.characteristics:
                props = set(ch.properties or [])
                if "notify" in props or "indicate" in props:
                    u = str(ch.uuid).lower()
                    async def make_cb(uuid):
                        async def cb(_, data: bytearray):
                            b = bytes(data)
                            print(f"[{uuid}] len={len(b)} hex={b.hex()}")
                            w.writerow([now_ms(), uuid, len(b), b.hex()]); f.flush()
                        return cb
                    cb = await make_cb(u)
                    print(f"[sub] {u} ({','.join(props)})")
                    await client.start_notify(ch.uuid, cb)
                    subs.append(ch.uuid)

        print("[sniffing] press Start/beep/arrow; Ctrl+C to stop early")
        try:
            await asyncio.sleep(args.secs)
        except KeyboardInterrupt:
            pass

        for u in subs:
            try: await client.stop_notify(u)
            except Exception: pass
    f.close()

if __name__ == "__main__":
    asyncio.run(main())
