
from __future__ import annotations
import asyncio, time
from asyncio.subprocess import PIPE
from .util import scan_lock, bluez_scan_off
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
        # tuneables
        self.scan_timeout_s: float = 8.0
        self.find_timeout_s: float = 10.0
        self.scan_attempts: int = 3

        # connection/disconnect event
        self._disconnected_evt: Optional[asyncio.Event] = None

        # Idle/keepalive management
        self._last_packet_ns: int = 0
        self.idle_reconnect_sec: float = 15.0  # if no data for this long, force reconnect
        self.keepalive_batt_sec: float = 60.0  # periodic benign battery read as keepalive
        self._watchdog_task: Optional[asyncio.Task] = None

    def on_packet(self, fn: Callable[[int, bytes], None]):
        self._on_packet = fn

    async def _bluetoothctl(self, *args: str) -> int:
        """Best-effort call to bluetoothctl to manage scan state.

        Returns process return code; ignores failures.
        """
        try:
            proc = await asyncio.create_subprocess_exec("bluetoothctl", *args, stdout=PIPE, stderr=PIPE)
            await proc.communicate()
            return proc.returncode or 0
        except Exception:
            return 0

    async def _ensure_scan_off(self):
        # Try to stop any lingering discovery that can cause org.bluez.Error.InProgress
        await bluez_scan_off()

    async def _discover_device(self):
        """
        Try hard to locate the BT50 advertising on the desired adapter.
        Returns a Bleak device object if found, else None.
        """
        target = self.mac.lower()
        dev = None
        # try a couple of strategies over a few attempts
        for attempt in range(1, self.scan_attempts + 1):
            # Proactively stop any existing discovery before we start our own
            await self._ensure_scan_off()
            # 1) find_device_by_address with bdaddr setting off (BlueZ canonical)
            try:
                async with scan_lock:
                    dev = await BleakScanner.find_device_by_address(self.mac, cb=dict(use_bdaddr=False), timeout=self.find_timeout_s)  # type: ignore[arg-type]
            except TypeError:
                async with scan_lock:
                    dev = await BleakScanner.find_device_by_address(self.mac, timeout=self.find_timeout_s)
            except Exception as e:
                # Handle BlueZ InProgress by backing off longer
                if "InProgress" in str(e):
                    await self._ensure_scan_off()
                    await asyncio.sleep(3.0)
                    dev = None
                else:
                    dev = None
            if dev:
                return dev

            # 2) flip bdaddr flag, some stacks expose different addr forms
            try:
                async with scan_lock:
                    dev = await BleakScanner.find_device_by_address(self.mac, cb=dict(use_bdaddr=True), timeout=3.0)  # type: ignore[arg-type]
            except TypeError:
                dev = None
            except Exception as e:
                if "InProgress" in str(e):
                    await self._ensure_scan_off()
                    await asyncio.sleep(3.0)
                    dev = None
                else:
                    dev = None
            if dev:
                return dev

            # 3) full discovery pass on the requested adapter
            try:
                async with scan_lock:
                    discovered = await BleakScanner.discover(adapter=self.adapter, timeout=self.scan_timeout_s)
            except TypeError:
                try:
                    async with scan_lock:
                        discovered = await BleakScanner.discover(device=self.adapter, timeout=self.scan_timeout_s)  # type: ignore[call-arg]
                except TypeError:
                    async with scan_lock:
                        discovered = await BleakScanner.discover(timeout=self.scan_timeout_s)
            except Exception as e:
                if "InProgress" in str(e):
                    await self._ensure_scan_off()
                    await asyncio.sleep(3.0)
                    discovered = []
                else:
                    discovered = []
            for d in discovered:
                if (d.address or "").lower() == target:
                    return d

            # brief backoff before retrying
            await asyncio.sleep(2.0)
        return None

    async def start(self):
        # First, try a direct connect by MAC to avoid triggering scans on BlueZ
        tried_direct = False
        try:
            self.client = BleakClient(self.mac, device=self.adapter)
            await self.client.connect(timeout=20.0)
            tried_direct = True
        except Exception:
            # Ensure we close any half-open state before falling back to discovery
            try:
                await self.client.disconnect()  # type: ignore[func-returns-value]
            except Exception:
                pass
            self.client = None

        if self.client is None:
            # Resolve device presence before connecting to avoid BleakDeviceNotFoundError
            dev = await self._discover_device()
            if not dev:
                raise RuntimeError(
                    f"BT50 device {self.mac} not found advertising on {self.adapter}. "
                    "Ensure it's powered, not connected elsewhere, and near the Pi."
                )

            # Connect using Linux/BlueZ device kwarg for adapter consistency
            self.client = BleakClient(dev, device=self.adapter)
            await self.client.connect(timeout=20.0)
        # track disconnection to allow reconnect loops upstream
        self._disconnected_evt = asyncio.Event()
        try:
            self.client.set_disconnected_callback(lambda _client: self._disconnected_evt and self._disconnected_evt.set())  # type: ignore[attr-defined]
        except Exception:
            # older Bleak may not have set_disconnected_callback
            pass
        # Optionally set detection cycle to 100 Hz via vendor config UUID (payload TBD).
        if self.config_uuid:
            try:
                await self.client.write_gatt_char(self.config_uuid, b"")  # placeholder safe no-op
            except Exception:
                pass

        def cb(_, data: bytearray):
            if self._on_packet:
                ts = time.monotonic_ns()
                self._last_packet_ns = ts
                self._on_packet(ts, bytes(data))

        await self.client.start_notify(self.notify_uuid, cb)

        async def _watchdog():
            last_batt = 0.0
            try:
                while self.client is not None:
                    await asyncio.sleep(1.0)
                    now_s = time.monotonic()
                    # periodic battery read
                    if self.keepalive_batt_sec > 0 and (now_s - last_batt) > self.keepalive_batt_sec:
                        try:
                            _ = await self.read_battery_level()
                        except Exception:
                            pass
                        last_batt = now_s
                    # idle reconnect
                    if self.idle_reconnect_sec > 0 and self._last_packet_ns:
                        idle_s = (time.monotonic_ns() - self._last_packet_ns) / 1e9
                        if idle_s > self.idle_reconnect_sec:
                            try:
                                await self.client.disconnect()
                            except Exception:
                                pass
                            return
            except asyncio.CancelledError:
                return

        self._watchdog_task = asyncio.create_task(_watchdog())

    async def stop(self):
        # stop watchdog first
        if self._watchdog_task:
            try:
                self._watchdog_task.cancel()
            except Exception:
                pass
            self._watchdog_task = None
        if self.client:
            try:
                await self.client.disconnect()
            finally:
                self.client = None

    async def wait_disconnect(self):
        if self._disconnected_evt is None:
            # if not connected, simulate immediate disconnection
            return
        await self._disconnected_evt.wait()

    # --- Diagnostics helpers ---
    async def read_battery_level(self) -> Optional[int]:
        """Try to read Battery Level (0x180F/0x2A19). Returns percent or None."""
        if not self.client:
            return None
        try:
            # Standard Battery Service
            bsu = "0000180f-0000-1000-8000-00805f9b34fb"
            blu = "00002a19-0000-1000-8000-00805f9b34fb"
            # Some devices don't expose the service in advertisement but still implement it
            data = await self.client.read_gatt_char(blu)
            if data:
                return int(data[0])
        except Exception:
            return None
        return None

    async def list_services(self) -> List[str]:
        """Return a human-readable summary of primary services and a few characteristic UUIDs."""
        out: List[str] = []
        if not self.client:
            return out
        try:
            svcs = await self.client.get_services()  # may be cached by bleak
            for s in svcs:
                # show up to 3 chars per service
                cuuids = [c.uuid for c in list(s.characteristics)[:3]] if getattr(s, 'characteristics', None) else []
                out.append(f"{s.uuid}  chars={len(getattr(s, 'characteristics', []))} sample={','.join(cuuids)}")
        except Exception:
            pass
        return out

    @staticmethod
    async def discover(adapter: str, name_filter: Optional[str] = None) -> List[str]:
        devs: List[str] = []
        try:
            discovered = await BleakScanner.discover(adapter=adapter, timeout=6.0)
        except TypeError:
            try:
                discovered = await BleakScanner.discover(device=adapter, timeout=6.0)  # type: ignore[call-arg]
            except TypeError:
                discovered = await BleakScanner.discover(timeout=6.0)
        for d in discovered:
            if name_filter is None or (d.name and name_filter.lower() in d.name.lower()):
                devs.append(f"{d.address}  {d.name}  RSSI={d.rssi}")
        return devs
