#!/usr/bin/env python3
# VERSION: wtvb_live_watch v0.1
import asyncio, argparse, datetime as dt, math
from bleak import BleakClient

def now(): return dt.datetime.utcnow().isoformat(timespec="milliseconds")+"Z"

def parse_words(b: bytes):
    if len(b)!=32: return None
    return [int.from_bytes(b[i:i+2], "little", signed=False) for i in range(0,32,2)]

async def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--mac", default="F8:FE:92:31:12:E3")
    ap.add_argument("--ctl", default="0000ffe4-0000-1000-8000-00805f9a34fb")
    ap.add_argument("--warm_ms", type=int, default=2000, help="baseline warmup")
    args=ap.parse_args()

    base=None
    t0=None

    async with BleakClient(args.mac, timeout=20.0, device=args.adapter) as client:
        print(f"[sub] {args.ctl} (notify)")
        async def cb(_, data:bytearray):
            nonlocal base,t0
            w = parse_words(bytes(data))
            if not w: return
            if t0 is None: t0 = dt.datetime.utcnow()
            dt_ms = (dt.datetime.utcnow()-t0).total_seconds()*1000

            # build baseline over warm_ms
            if base is None: base = [0]*16
            if dt_ms < args.warm_ms:
                for i in range(16): base[i] = w[i] if dt_ms<10 else (base[i]*0.98 + w[i]*0.02)
                return

            # focus on the movers we saw in analysis
            a,b,c = w[8], w[9], w[10]
            ab,bb,cb = int(base[8]), int(base[9]), int(base[10])
            da,db,dc = a-ab, b-bb, c-cb
            mag = math.sqrt(da*da + db*db + dc*dc)

            print(f"{now()} type=0x{w[1]:04x} w08={a:4d}({da:+4d}) w09={b:4d}({db:+4d}) "
                  f"w10={c:4d}({dc:+4d}) | |Δ|={mag:7.1f}")

        await client.start_notify(args.ctl, cb)
        print("[watch] warming baseline… then printing deltas (Ctrl+C to stop)")
        try:
            while True: await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    asyncio.run(main())
