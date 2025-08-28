#!/usr/bin/env python3
import asyncio, argparse
from bleak import BleakScanner, BleakClient

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--mac")
    ap.add_argument("--name")
    args = ap.parse_args()

    if not args.mac:
        print("[scan] looking for devices…")
        devs = await BleakScanner.discover(adapter=args.adapter, timeout=8.0)
        for d in devs:
            print(f"{d.address:>17}  {d.name}")
        if not args.name:
            return
        dev = next((d for d in devs if (args.name or "").lower() in (d.name or "").lower()), None)
        if not dev:
            raise SystemExit("[err] name not found; rerun with --mac from the list above")
        args.mac = dev.address

    print(f"[connect] {args.mac} …")
    async with BleakClient(args.mac, timeout=20.0, device=args.adapter) as client:
        for svc in client.services:
            print(f"[service] {svc.uuid}")
            for ch in svc.characteristics:
                props=",".join(ch.properties or [])
                print(f"  [char] {ch.uuid}  ({props})")
    print("[done]")
asyncio.run(main())
