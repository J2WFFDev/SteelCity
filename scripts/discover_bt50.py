#!/usr/bin/env python3
import argparse
import asyncio
from typing import Dict, Tuple, List, Optional

from bleak import BleakScanner

async def scan_with_meta(adapter: Optional[str], duration: float = 6.0):
    latest: Dict[str, Tuple[object, int, object]] = {}

    def cb(device, adv):
        rssi = adv.rssi if getattr(adv, "rssi", None) is not None else -999
        latest[device.address] = (device, rssi, adv)

    scanner = BleakScanner(detection_callback=cb, adapter=adapter)
    await scanner.start()
    await asyncio.sleep(duration)
    await scanner.stop()

    out = []
    for addr, (dev, rssi, adv) in latest.items():
        out.append((addr, dev, rssi, adv))
    out.sort(key=lambda t: t[2], reverse=True)
    return out

async def main():
    ap = argparse.ArgumentParser(description="Discover BT5.0 (with adv hints)")
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--name", default=None)
    ap.add_argument("--mac", default=None)
    ap.add_argument("--scan", type=float, default=6.0)
    args = ap.parse_args()

    print(f"[i] Scanning ~{int(args.scan)} s…\n")
    rows = await scan_with_meta(args.adapter, args.scan)

    def match(addr, dev):
        if args.mac:
            return addr.lower() == args.mac.lower()
        if args.name:
            return args.name.lower() in (dev.name or "").lower()
        return True

    hits = [r for r in rows if match(r[0], r[1])]
    show = hits if (args.mac or args.name) else rows

    if not hits and (args.mac or args.name):
        print("[!] No matching device. Nearby candidates:\n")

    for addr, dev, rssi, adv in show[:20]:
        uuids = getattr(adv, "service_uuids", []) or []
        mfg = getattr(adv, "manufacturer_data", {}) or {}
        mfg_keys = ",".join(f"0x{k:04X}" for k in sorted(mfg.keys()))
        print(f"  RSSI {rssi:>4} | {dev.name or '(no name)'} [{addr}]  uuids={len(uuids)}  mfg=[{mfg_keys}]")
        if uuids:
            print(f"           uuids: {', '.join(uuids[:6])}{'…' if len(uuids)>6 else ''}")

if __name__ == "__main__":
    asyncio.run(main())
