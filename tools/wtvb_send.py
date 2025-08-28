#!/usr/bin/env python3
# VERSION: wtvb_send v0.1
import asyncio, argparse, binascii
from bleak import BleakClient

def parse_bytes(s: str):
    s = s.strip()
    if not s: return b""
    if s.startswith("0x"):  # single hex literal
        s = s[2:]
    # allow "AA BB CC" or "aa:bb:cc" or "aabbcc"
    s = s.replace(":", " ").replace(",", " ")
    parts = s.split()
    if len(parts) == 1 and all(c in "0123456789abcdefABCDEF" for c in parts[0]) and len(parts[0])%2==0:
        return binascii.unhexlify(parts[0])
    return bytes(int(p,16) for p in parts)

async def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--mac", required=True)
    ap.add_argument("--uuid", default="0000ffe9-0000-1000-8000-00805f9a34fb", help="write characteristic")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--hex", help="hex bytes to send (e.g. 'AA 55 01 00')")
    g.add_argument("--ascii", help="ASCII to send (e.g. 'AT+RATE=100')")
    args=ap.parse_args()

    payload = parse_bytes(args.hex) if args.hex else args.ascii.encode("ascii")
    print(f"[send] {len(payload)} bytes -> {args.uuid}")
    async with BleakClient(args.mac, timeout=20.0, device=args.adapter) as client:
        await client.write_gatt_char(args.uuid, payload, response=True)
    print("[ok] write done")

if __name__ == "__main__":
    asyncio.run(main())
