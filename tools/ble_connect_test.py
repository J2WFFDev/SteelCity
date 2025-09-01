#!/usr/bin/env python3
import asyncio
import argparse
from typing import Optional
from bleak import BleakClient

DEFAULT_ADAPTER = 'hci0'
DEFAULT_BT50_MAC = 'F8:FE:92:31:12:E3'
DEFAULT_AMG_MAC = '60:09:C3:1F:DC:1A'


async def try_connect(mac: str, label: str, adapter: str, timeout: float = 15.0) -> None:
    print(f"[test] connecting to {label} {mac} on {adapter} ...", flush=True)
    try:
        async with BleakClient(mac, device=adapter, timeout=timeout) as client:
            print(f"[ok] {label} connected: {client.is_connected}", flush=True)
            # Try to ensure services are available across Bleak versions
            services_count: Optional[int] = None
            try:
                # Newer Bleak may not have get_services; older ones do.
                get_services = getattr(client, 'get_services', None)
                if callable(get_services):
                    await get_services()
                if getattr(client, 'services', None) is not None:
                    services_count = len(client.services)
            except Exception as e:
                print(f"[warn] {label} service fetch failed: {e}", flush=True)
            if services_count is not None:
                print(f"[ok] {label} services loaded ({services_count})", flush=True)
            else:
                print(f"[ok] {label} services not reported (proceeding)", flush=True)
    except Exception as e:
        print(f"[err] {label} connect failed: {e}", flush=True)


async def main() -> None:
    parser = argparse.ArgumentParser(description='Minimal direct MAC BLE connect test for BT50 and AMG')
    parser.add_argument('--adapter', default=DEFAULT_ADAPTER, help='BlueZ adapter (default: hci0)')
    parser.add_argument('--bt50', default=DEFAULT_BT50_MAC, help='BT50 MAC address')
    parser.add_argument('--amg', default=DEFAULT_AMG_MAC, help='AMG MAC address')
    args = parser.parse_args()

    await try_connect(args.bt50, 'BT50', args.adapter)
    await try_connect(args.amg, 'AMG', args.adapter)


if __name__ == '__main__':
    asyncio.run(main())
