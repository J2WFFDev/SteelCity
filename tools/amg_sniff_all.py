#!/usr/bin/env python3
import asyncio, argparse, datetime as dt, csv, os
from bleak import BleakScanner, BleakClient

def now_ms(): return dt.datetime.utcnow().isoformat(timespec="milliseconds")+"Z"

async def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--mac")
    g.add_argument("--name", default="AMG")
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--secs", type=float, default=30.0)
    ap.add_argument("--csv", default="sniff_all.csv")
    args = ap.parse_args()

    header_needed = not os.path.exists(args.csv) or os.stat(args.csv).st_size == 0
    f = open(args.csv, "a", newline="")
    w = csv.writer(f)
    if header_needed:
        w.writerow(["utc_iso","uuid","len","hex"]); f.flush()

    if args.mac:
        dev = await BleakScanner.find_device_by_address(args.mac, cb=dict(use_bdaddr=False))
    else:
        dev = None
        for d in await BleakScanner.discover(adapter=args.adapter, timeout=8.0):
            if (args.name or "").lower() in (d.name or "").lower():
                dev = d; break
    if not dev: raise SystemExit("device not found")

    print(f"[ble] connect {dev.address} ({dev.name}) …")
    async with BleakClient(dev, timeout=20.0, device=args.adapter) as client:
        subs = []
        for svc in client.services:
            for ch in svc.characteristics:
                props = set(ch.properties or [])
                if "notify" in props or "indicate" in props:
                    u = str(ch.uuid).lower()
                    print(f"[sub] {u} (notify)")
                    def cb(_, data: bytearray, uuid=u):
                        b = bytes(data)
                        print(f"[{uuid}] len={len(b)} hex={b.hex()}")
                        w.writerow([now_ms(), uuid, len(b), b.hex()]); f.flush()
                    await client.start_notify(u, cb)
                    subs.append(u)

        print("[sniffing] press Start/beep/arrow; Ctrl+C to stop early")
        try:
            await asyncio.sleep(args.secs)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            for u in subs:
                try: await client.stop_notify(u)
                except: pass
            f.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
