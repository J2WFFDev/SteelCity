#!/usr/bin/env python3
"""
AMG UUID Probe — discover services/characteristics and sniff notifications (Bleak 1.x–friendly)

Usage
-----
# Fast path: known MAC
python amg_uuid_probe.py --adapter hci0 --mac 60:09:C3:1F:DC:1A

# Scan by name substring
python amg_uuid_probe.py --adapter hci0 --name AMG

What it does
------------
- Connects to the device.
- Prints all services and characteristics with properties (read/write/notify/indicate).
- Subscribes to every NOTIFY/INDICATE characteristic for a window you choose and dumps
  any incoming packets (hex + best‑effort utf‑8). The UUID(s) that fire are your control
  characteristic(s) to use in the Commander.
"""

import argparse
import asyncio
from typing import Optional, List

from bleak import BleakClient, BleakScanner


def maybe_text(b: bytes) -> str:
    """Return a printable text best‑effort view of bytes."""
    try:
        s = b.decode("utf-8", errors="replace")
        return ''.join(ch if 32 <= ord(ch) < 127 else '.' for ch in s)
    except Exception:
        return ""


async def find_device(adapter: str, mac: Optional[str], name: Optional[str]):
    if mac:
        dev = await BleakScanner.find_device_by_address(mac, cb=dict(use_bdaddr=False))
        if not dev:
            raise SystemExit("Device with that MAC not found. Is it on and advertising?")
        return dev
    print(f"[scan] Searching for name contains: {name!r} (adapter={adapter})")
    found = await BleakScanner.discover(adapter=adapter, timeout=8.0)
    for d in found:
        if name and name.lower() in (d.name or "").lower():
            return d
    raise SystemExit("No device matched by name. Try --mac or widen --name.")


async def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--mac")
    g.add_argument("--name", default="AMG")
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--sniff-secs", type=float, default=20.0, help="How long to listen for notifications")
    ap.add_argument("--only", dest="only_uuid", help="If set, only subscribe to this characteristic UUID")
    args = ap.parse_args()

    dev = await find_device(args.adapter, args.mac, args.name)
    print(f"[ble] Connecting to {dev.address} ({dev.name}) …")

    async with BleakClient(dev, timeout=20.0, device=args.adapter) as client:
        # Bleak >=1.0 exposes services at client.services (no get_services())
        svcs = client.services
        if svcs is None:
            # Fallback for older Bleak (rare)
            try:
                svcs = await client.get_services()  # type: ignore[attr-defined]
            except AttributeError:
                svcs = []

        print("[services]")
        for s in svcs:
            desc = getattr(s, "description", "") or ""
            print(f"  svc {s.uuid}  ({desc})")
            for c in s.characteristics:
                props = getattr(c, "properties", {})
                if isinstance(props, (set, list)):
                    propdict = {p: True for p in props}
                else:
                    propdict = dict(props)
                def has(p: str) -> bool: return bool(propdict.get(p))
                prop_str = ",".join([
                    p for p in [
                        "read" if has("read") else None,
                        "write" if has("write") else None,
                        "write-no-rsp" if has("write_without_response") else None,
                        "notify" if has("notify") else None,
                        "indicate" if has("indicate") else None,
                    ] if p
                ]) or "-"
                handle = getattr(c, "handle", "?")
                print(f"    ch  {c.uuid}  props=[{prop_str}]  handle={handle}")
        
        # Build subscribe list robustly across Bleak versions
        subs: List[str] = []
        for s in svcs:
            for c in s.characteristics:
                cuuid = str(c.uuid)
                if args.only_uuid and cuuid.lower() != args.only_uuid.lower():
                    continue
                props = getattr(c, "properties", {})
                if isinstance(props, (set, list)):
                    has_notify = ("notify" in props) or ("indicate" in props)
                else:
                    has_notify = bool(props.get("notify") or props.get("indicate"))
                if has_notify:
                    subs.append(cuuid)
        if not subs:
            print("[warn] No NOTIFY/INDICATE characteristics found (or filtered out).")
            return

        print("[subscribing] to:")
        for u in subs:
            print("  ", u)

        # Notification callback factory
        def on_data(uuid: str):
            def _inner(_, data: bytearray):
                b = bytes(data)
                print(f"[notify] {uuid}  len={len(b)}  hex={b.hex()}  text={maybe_text(b)!r}")
            return _inner

        # Start notifications
        for u in subs:
            try:
                await client.start_notify(u, on_data(u))
            except Exception as e:
                print(f"[skip] {u}: {e}")

        print(f"[sniffing] Press AMG controls now… listening for {args.sniff_secs}s")
        try:
            await asyncio.sleep(args.sniff_secs)
        finally:
            for u in subs:
                try:
                    await client.stop_notify(u)
                except Exception:
                    pass
        print("[done] Review above notifications. The UUID(s) that fired are your control char(s).")


if __name__ == "__main__":
    asyncio.run(main())
