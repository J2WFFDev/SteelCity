
from __future__ import annotations
import asyncio, time
from typing import Optional, Callable
from bleak import BleakScanner, BleakClient

class AmgClient:
    def __init__(self, adapter: str, mac_or_name: Optional[str], start_uuid: str):
        self.adapter = adapter
        self.target = mac_or_name
        self.start_uuid = start_uuid
        self.client: Optional[BleakClient] = None
        self._on_t0: Optional[Callable[[int, bytes], None]] = None

    def on_t0(self, fn: Callable[[int, bytes], None]):
        self._on_t0 = fn

    async def start(self):
        dev = None
        async with BleakScanner(adapter=self.adapter) as scanner:
            for _ in range(20):
                await asyncio.sleep(0.5)
                for d in await scanner.get_discovered_devices():
                    name = (d.name or "").lower()
                    if self.target:
                        if self.target.lower() in (name, d.address.lower()):
                            dev = d; break
                    if "amg" in name or "commander" in name:
                        dev = d; break
                if dev: break
        if not dev:
            raise RuntimeError("AMG Commander not found")

        self.client = BleakClient(dev, adapter=self.adapter)
        await self.client.connect()

        async def cb(_, data: bytearray):
            if self._on_t0:
                self._on_t0(time.monotonic_ns(), bytes(data))

        await self.client.start_notify(self.start_uuid, cb)

    async def stop(self):
        if self.client:
            try:
                await self.client.disconnect()
            finally:
                self.client = None
