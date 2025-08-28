#!/usr/bin/env python3
# VERSION: wtvb_live_words v0.1
import asyncio, argparse, datetime as dt
from bleak import BleakScanner, BleakClient

def now(): return dt.datetime.utcnow().isoformat(timespec="milliseconds")+"Z"
def le16(b): return int.from_bytes(b, "little", signed=False)

def words_from_hex(h):
    b = bytes.fromhex(h)
    if len(b)!=32 or b[0]!=0x55 or b[1]!=0x61: return None
    # 30 bytes after header -> 15 little-endian words
    ws = [le16(b[i:i+2]) for i in range(2, 32, 2)]
    return ws

async def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--mac"); g.add_argument("--name", default="WTVB01")
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--notify", default="0000ffe4-0000-1000-8000-00805f9a34fb")
    ap.add_argument("--secs", type=float, default=120)
    args = ap.parse_args()

    if args.mac:
        dev = await BleakScanner.find_device_by_address(args.mac, cb=dict(use_bdaddr=False))
    else:
        dev = None
        for d in await BleakScanner.discover(adapter=args.adapter, timeout=6.0):
            if (d.name or "").lower().startswith(args.name.lower()):
                dev = d; break
    if not dev: raise SystemExit("device not found")

    print("[version] wtvb_live_words v0.1")
    print(f"[ble] connect {dev.address} ({dev.name}) …")

    last = None
    async with BleakClient(dev, timeout=20.0, device=args.adapter) as client:
        print(f"[sub] {args.notify} (notify)")
        def on_data(_, data:bytearray):
            nonlocal last
            h = data.hex()
            ws = words_from_hex(h)
            if not ws: return
            # build a compact diff string
            diffs=[]
            if last:
                for i,(a,b) in enumerate(zip(last,ws)):
                    if a!=b: diffs.append(f"w{i} {a}->{b}")
            last = ws
            diff_s = (" | " + ", ".join(diffs)) if diffs else ""
            print(f"{now()}  w0..w14={ws}{diff_s}")
        await client.start_notify(args.notify, on_data)
        print("[live] printing 55 61 frames as 15 LE-words… (Ctrl+C to stop)")
        try:
            await asyncio.sleep(args.secs)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    asyncio.run(main())
