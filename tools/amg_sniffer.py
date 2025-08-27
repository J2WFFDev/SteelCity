#!/usr/bin/env python3
import argparse, asyncio, binascii, datetime as dt
from typing import Dict, Tuple, List, Optional
from bleak import BleakScanner, BleakClient

# --- scan helpers (Bleak 1.x: RSSI via adv_data) ---
async def scan_with_rssi(adapter: Optional[str], duration: float = 6.0):
    latest_dev: Dict[str, object] = {}
    latest_rssi: Dict[str, int] = {}
    latest_adv: Dict[str, object] = {}
    def cb(device, adv):
        latest_dev[device.address] = device
        latest_adv[device.address] = adv
        if adv and adv.rssi is not None:
            latest_rssi[device.address] = int(adv.rssi)
    scanner = BleakScanner(detection_callback=cb, adapter=adapter)
    await scanner.start(); await asyncio.sleep(duration); await scanner.stop()
    rows = []
    for addr, dev in latest_dev.items():
        rows.append((addr, dev, latest_rssi.get(addr, -999), latest_adv.get(addr)))
    rows.sort(key=lambda t: t[2], reverse=True)
    return rows

async def pick_device(adapter, mac, name, duration=6.0):
    print(f"[i] Scanning ~{int(duration)} s…")
    rows = await scan_with_rssi(adapter, duration)
    if mac:
        for addr, dev, *_ in rows:
            if addr.lower() == mac.lower():
                return dev
        print(f"[!] No device with MAC {mac}")
    elif name:
        for addr, dev, *_ in rows:
            if name.lower() in (dev.name or "").lower():
                return dev
        print(f"[!] No device with name containing {name!r}")
    if not rows:
        print("[!] No Bluetooth devices found."); return None
    print("[!] No obvious match. Top nearby devices:")
    for addr, dev, rssi, adv in rows[:10]:
        hint = ""
        if adv and getattr(adv, "service_uuids", None):
            hint = f"  uuids={len(adv.service_uuids)}"
        print(f"    RSSI {rssi:>4}  | {dev.name or '(no name)'}  [{addr}]{hint}")
    return None

# --- pretty helpers ---
def now_iso(): return dt.datetime.now().isoformat(timespec="milliseconds")
def fmt_props(props: List[str]): return ",".join(sorted(set(props or [])))
def printable_utf8(b: bytes):
    try:
        s = b.decode("utf-8")
        if all((31 < ord(ch) < 127) or ch in "\r\n\t" for ch in s): return s
    except Exception:
        pass
    return None

# --- main ---
async def main():
    ap = argparse.ArgumentParser(description="AMG sniffer: discover GATT and subscribe to notify chars (Bleak 1.x)")
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--mac", default=None)
    ap.add_argument("--name", default=None)
    ap.add_argument("--scan", type=float, default=6.0)
    ap.add_argument("--svc", default=None, help="only this service UUID")
    ap.add_argument("--ch",  default=None, help="only this characteristic UUID")
    args = ap.parse_args()

    dev = await pick_device(args.adapter, args.mac, args.name, duration=args.scan)
    if not dev: return

    print(f"[i] Connecting to {dev.name or '(no name)'} [{dev.address}] …")
    async with BleakClient(dev.address, adapter=args.adapter) as client:
        print("[i] Connected:", client.is_connected)

        # >>> CHANGED: use property, not get_services()
        services = client.services   # Bleak 1.x: services are auto-enumerated

        print("\n[i] Services & characteristics:")
        for svc in services:
            if args.svc and svc.uuid.lower() != args.svc.lower(): continue
            print(f"  Service {svc.uuid} ({svc.description})")
            for ch in svc.characteristics:
                print(f"    Char   {ch.uuid}  props=[{fmt_props(ch.properties)}]  desc={ch.description}")

        async def handle_notify(uuid: str, data: bytearray):
            b = bytes(data)
            hexstr = binascii.hexlify(b).decode()
            s = printable_utf8(b)
            print(f"[{now_iso()}] {uuid}  {len(b)}B  hex={hexstr}" + (f"  text={s}" if s else ""))

        to_sub: List[str] = []
        for svc in services:
            if args.svc and svc.uuid.lower() != args.svc.lower(): continue
            for ch in svc.characteristics:
                if "notify" in (ch.properties or []):
                    if args.ch and ch.uuid.lower() != args.ch.lower(): continue
                    to_sub.append(ch.uuid)

        if not to_sub:
            print("\n[!] No notify characteristics found with current filters.")
            print("    Tip: re-run without --svc/--ch to see everything, then narrow.")
            return

        print("\n[i] Subscribing to notify characteristics:")
        for cuuid in to_sub:
            print(f"    - {cuuid}")
            await client.start_notify(cuuid, lambda c, d, cuuid=cuuid: asyncio.create_task(handle_notify(cuuid, d)))

        print("[i] Listening…  (Ctrl+C to stop)")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n[i] Stopping notifications…")
            for cuuid in to_sub:
                try: await client.stop_notify(cuuid)
                except Exception: pass

if __name__ == "__main__":
    asyncio.run(main())
