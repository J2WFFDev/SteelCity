
from __future__ import annotations
import os, json, time, pathlib
from typing import Optional, IO

class NdjsonLogger:
    def __init__(self, directory: str, file_prefix: str):
        self.dir = pathlib.Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.prefix = file_prefix
        self.seq = 0
        self._fh: Optional[IO[str]] = None
        self._rot_day = None
        self.rotate()

    def rotate(self):
        day = time.strftime("%Y%m%d")
        if self._fh:
            self._fh.close()
        path = self.dir / f"{self.prefix}_{day}.ndjson"
        self._fh = open(path, "a", buffering=1, encoding="utf-8")
        self._rot_day = day

    def write(self, obj: dict):
        self.seq += 1
        obj.setdefault("seq", self.seq)
        obj.setdefault("ts_ms", time.monotonic() * 1000.0)
        if time.strftime("%Y%m%d") != self._rot_day:
            self.rotate()
        self._fh.write(json.dumps(obj) + "\n")
