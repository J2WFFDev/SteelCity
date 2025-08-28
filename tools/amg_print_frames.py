#!/usr/bin/env python3
# VERSION: amg_print_frames v0.2
import asyncio, argparse, datetime as dt
from bleak import BleakScanner, BleakClient

def now(): return dt.datetime.utcnow().isoformat(timespec="milliseconds")+"Z"
def le16(b): return int.from_bytes(b,"little")
def parse(b):
    if len(b)!=14: return None
    return dict(
        b0=b[0], b1=b[1], b2=b[2], b3=b[3], b4=b[4],
        p1=le16(b[5:7]), p2=le16(b[7:9]), p3=le16(b[9:11]), p4=le16(b[11:13]),
        tail=b[13], hex=b.hex()
    )

async def main():
    print("[version] amg_print_frames v0.2")
    ap=argparse.ArgumentParser()
    g=ap.add_mutually_exclusive_group(); g.add_argument("--mac"); g.add_argument("--name", default="AMG")
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--ctl", default="6e400003-b5a3-f393-e0a9-e50e24dcca9e")
    ap.add_argument("--secs", type=float, default=120)
    args=ap.parse_args()

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
        ctl = args.ctl.lower()
        print(f"[sub] {ctl} (notify)")

        def cb(_, data: bytearray):
            f = parse(bytes(data))
            if not f:
                return
            print(f"{now()} b1={f['b1']:02x} b2={f['b2']:02x} b3={f['b3']:02x} "
                  f"p1={f['p1']:>4} p2={f['p2']:>4} p3={f['p3']:>4} p4={f['p4']:>4} "
                  f"tail=0x{f['tail']:02x} {f['hex']}", flush=True)

        await client.start_notify(ctl, cb)
        print("[live] printing all frames… (Ctrl+C to stop)")
        try:
            await asyncio.sleep(args.secs)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            try:
                await client.stop_notify(ctl)
            except:
                pass

if __name__=="__main__":
    asyncio.run(main())
