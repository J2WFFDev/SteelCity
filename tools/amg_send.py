#!/usr/bin/env python3
"""
Send a command to AMG over Nordic UART write characteristic.

Examples:
  python tools/amg_send.py --adapter hci0 --mac 60:09:C3:1F:DC:1A --text "START\n"
  python tools/amg_send.py --name AMG --hex 01-02-03-04

Notes:
- We don't yet know the exact payloads to trigger beep or set sensitivity.
  This tool provides a minimal path to send and experiment once payloads are known.
"""
import argparse, asyncio, re
from typing import Optional
from bleak import BleakClient, BleakScanner

NUS_WRITE = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"


def parse_hex(s: str) -> bytes:
    s = s.strip().replace(" ", "").replace("-", ":").replace(",", ":")
    parts = [p for p in s.split(":") if p]
    return bytes(int(p, 16) for p in parts)


async def find_device(adapter: str, mac: Optional[str], name: Optional[str]):
    if mac:
        # Prefer direct connect by address; some stacks don't require discovery
        return mac
    print(f"[scan] Searching for name contains: {name!r} (adapter={adapter})")
    for d in await BleakScanner.discover(adapter=adapter, timeout=8.0):
        if name and name.lower() in (d.name or "").lower():
            return d
    raise SystemExit("No device matched by name. Try --mac or widen --name.")


async def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--mac")
    g.add_argument("--name", default="AMG")
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--uuid", default=NUS_WRITE)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text")
    src.add_argument("--hex")
    args = ap.parse_args()

    dev = await find_device(args.adapter, args.mac, args.name)
    # dev can be a MAC string or a Bleak device
    target_desc = dev if isinstance(dev, str) else getattr(dev, 'address', None)
    print(f"[ble] Connecting to {target_desc} …")
    async with BleakClient(dev, timeout=20.0, device=args.adapter) as client:
        payload = args.text.encode("utf-8") if args.text is not None else parse_hex(args.hex)
        print(f"[write] {args.uuid}  len={len(payload)}  hex={payload.hex()}")
        await client.write_gatt_char(args.uuid, payload, response=True)
        print("[ok] write done")


if __name__ == "__main__":
    asyncio.run(main())
