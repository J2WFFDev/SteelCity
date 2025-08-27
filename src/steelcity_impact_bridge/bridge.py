
from __future__ import annotations
import asyncio, time
from typing import List, Optional
from .config import AppCfg, load_config, DetectorCfg
from .logs import NdjsonLogger
from .detector import HitDetector, DetectorParams
from .ble.amg import AmgClient
from .ble.witmotion_bt50 import Bt50Client

class Bridge:
    def __init__(self, cfg: AppCfg):
        self.cfg = cfg
        self.logger = NdjsonLogger(cfg.logging.dir, cfg.logging.file_prefix)
        self.t0_ns: Optional[int] = None
        self.amg: Optional[AmgClient] = None
        self.bt_clients: List[Bt50Client] = []
        self.detectors = {}

    async def start(self):
        # Start AMG listener
        self.amg = AmgClient(self.cfg.amg.adapter, self.cfg.amg.mac or self.cfg.amg.name, self.cfg.amg.start_uuid)
        self.amg.on_t0(self._on_t0)
        await self.amg.start()

        # Start BT50 sensors
        for s in self.cfg.sensors:
            cli = Bt50Client(s.adapter, s.mac, s.notify_uuid, s.config_uuid)
            cli.on_packet(lambda ts, data, plate=s.plate: self._on_bt50_packet(plate, ts, data))
            await cli.start()
            self.bt_clients.append(cli)
            self.detectors[s.plate] = HitDetector(DetectorParams(**self.cfg.detector.__dict__))

        # Periodic status
        asyncio.create_task(self._status_task())

    async def _status_task(self):
        while True:
            self.logger.write({
                "type":"status",
                "t_rel_ms": None if self.t0_ns is None else (time.monotonic_ns()-self.t0_ns)/1e6,
                "msg":"alive",
                "data":{"plates": list(self.detectors.keys())}
            })
            await asyncio.sleep(5)

    def _on_t0(self, t0_ns: int, raw: bytes):
        self.t0_ns = t0_ns
        self.logger.write({"type":"event","t_rel_ms":0.0,"msg":"T0","data":{"raw": raw.hex()}})

    def _on_bt50_packet(self, plate: str, ts_ns: int, payload: bytes):
        # Reduce payload to a scalar 'amplitude'. Without vendor docs, use a stable heuristic:
        #  - treat bytes as unsigned and compute a simple energy proxy
        #  - this is just for PoC plumbing; replace with real field extraction later
        if not payload:
            return
        s = sum(b*b for b in payload) / len(payload)
        amp = float(s**0.5)  # pseudo-RMS of payload bytes

        det = self.detectors[plate]
        hit = det.update(amp, dt_ms=10.0)  # BT50 at 100 Hz
        if hit and self.t0_ns is not None:
            t_rel_ms = (ts_ns - self.t0_ns)/1e6
            self.logger.write({"type":"event","plate":plate,"t_rel_ms":t_rel_ms,"msg":"HIT","data":hit})

    async def stop(self):
        for cli in self.bt_clients:
            try:
                await cli.stop()
            except Exception:
                pass
        if self.amg:
            try:
                await self.amg.stop()
            except Exception:
                pass

async def run(config_path: str):
    cfg = load_config(config_path)
    br = Bridge(cfg)
    await br.start()
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await br.stop()
