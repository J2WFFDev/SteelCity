
from __future__ import annotations
import dataclasses, yaml
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class AmgCfg:
    adapter: str = "hci0"
    mac: Optional[str] = None
    name: Optional[str] = None
    start_uuid: str = ""

@dataclass
class SensorCfg:
    plate: str = "P1"
    adapter: str = "hci0"
    mac: str = ""
    notify_uuid: str = ""
    config_uuid: Optional[str] = None

@dataclass
class DetectorCfg:
    triggerHigh: float = 8.0
    triggerLow: float = 2.0
    ring_min_ms: int = 30
    dead_time_ms: int = 100

@dataclass
class LoggingCfg:
    dir: str = "./logs"
    file_prefix: str = "bridge"

@dataclass
class AppCfg:
    amg: AmgCfg
    sensors: List[SensorCfg]
    detector: DetectorCfg
    logging: LoggingCfg

def load_config(path: str) -> AppCfg:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    amg = AmgCfg(**raw.get("amg", {}))
    sensors = [SensorCfg(**s) for s in raw.get("sensors", [])]
    det = DetectorCfg(**raw.get("detector", {}))
    log = LoggingCfg(**raw.get("logging", {}))
    return AppCfg(amg=amg, sensors=sensors, detector=det, logging=log)
