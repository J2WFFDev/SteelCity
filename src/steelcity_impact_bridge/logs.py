
from __future__ import annotations
import os, json, time, pathlib, uuid
from typing import Optional, IO

class NdjsonLogger:
    def __init__(self, directory: str, file_prefix: str):
        self.dir = pathlib.Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.prefix = file_prefix
        self.seq = 0
        self._fh: Optional[IO[str]] = None
        self._rot_day: Optional[str] = None
        self._path: Optional[pathlib.Path] = None
        # Observability: per-run identifiers
        self.session_id: str = os.getenv("SESSION_ID") or uuid.uuid4().hex[:12]
        try:
            self.pid: int = os.getpid()
        except Exception:
            self.pid = -1
        self.rotate()

    def rotate(self):
        # Close previous handle
        if self._fh:
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None

        # Create a time-coded filename, e.g., bridge_YYYYMMDD_HHMMSS.ndjson
        now = time.time()
        stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(now))
        day = stamp[:8]
        path = self.dir / f"{self.prefix}_{stamp}.ndjson"
        self._fh = open(path, "a", buffering=1, encoding="utf-8")
        self._path = path
        self._rot_day = day

        # Maintain a daily alias so existing tools (expecting prefix_YYYYMMDD.ndjson) keep working
        alias = self.dir / f"{self.prefix}_{day}.ndjson"
        try:
            if alias.exists() or alias.is_symlink():
                try:
                    alias.unlink()
                except Exception:
                    pass
            # Prefer hardlink when possible (same filesystem); fallback to symlink
            try:
                os.link(path, alias)
            except Exception:
                try:
                    os.symlink(str(path), alias)  # absolute path for safety
                except Exception:
                    # As a last resort, create/truncate alias to exist (not kept in sync)
                    with open(alias, "a", encoding="utf-8"):
                        pass
        except Exception:
            # Non-fatal if alias creation fails
            pass

    def write(self, obj: dict):
        self.seq += 1
        # Monotonic clock (ms) for stable deltas
        obj.setdefault("ts_ms", time.monotonic() * 1000.0)
        # Human-friendly local time HH:MM:SS.mmm
        now = time.time()
        lt = time.localtime(now)
        msec = int((now % 1.0) * 1000)
        hms = time.strftime("%H:%M:%S", lt) + f".{msec:03d}"
        obj.setdefault("hms", hms)
        # ISO UTC wall clock for cross-host correlation
        isoutc = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now)) + f".{msec:03d}Z"
        obj.setdefault("t_iso", isoutc)
        # Sequence and identity
        obj.setdefault("seq", self.seq)
        obj.setdefault("schema", "v1")
        obj.setdefault("session_id", self.session_id)
        obj.setdefault("pid", self.pid)
        if time.strftime("%Y%m%d") != self._rot_day:
            self.rotate()
        self._fh.write(json.dumps(obj) + "\n")
