
from __future__ import annotations
import asyncio, time
from typing import Optional, Callable, List
from bleak import BleakScanner, BleakClient

class Bt50Client:
    def __init__(self, adapter: str, mac: str, notify_uuid: str, config_uuid: Optional[str] = None):
        self.adapter = adapter
        self.mac = mac
        self.notify_uuid = notify_uuid
        self.config_uuid = config_uuid
        self.client: Optional[BleakClient] = None
        self._on_packet: Optional[Callable[[int, bytes], None]] = None

    def on_packet(self, fn: Callable[[int, bytes], None]):
        self._on_packet = fn

    async def start(self):
        self.client = BleakClient(self.mac, adapter=self.adapter)
        await self.client.connect()
        # Optionally set detection cycle to 100 Hz via vendor config UUID (payload TBD).
        if self.config_uuid:
            try:
                await self.client.write_gatt_char(self.config_uuid, b"")  # placeholder safe no-op
            except Exception:
                pass

        async def cb(_, data: bytearray):
            if self._on_packet:
                self._on_packet(time.monotonic_ns(), bytes(data))

        await self.client.start_notify(self.notify_uuid, cb)

    async def stop(self):
        if self.client:
            try:
                await self.client.disconnect()
            finally:
                self.client = None

    @staticmethod
    async def discover(adapter: str, name_filter: Optional[str] = None) -> List[str]:
        devs = []
        async with BleakScanner(adapter=adapter) as scanner:
            await asyncio.sleep(6.0)
            for d in await scanner.get_discovered_devices():
                if name_filter is None or (d.name and name_filter.lower() in d.name.lower()):
                    devs.append(f"{d.address}  {d.name}  RSSI={d.rssi}")
        return devs
