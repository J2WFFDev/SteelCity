from __future__ import annotations
import asyncio
from asyncio.subprocess import PIPE

# Global lock to serialize BlueZ discovery/scanning across modules
scan_lock = asyncio.Lock()

async def bluez_scan_off():
    """Best-effort: stop any bluetoothctl discovery to avoid BlueZ InProgress.

    This is intentionally fire-and-forget; ignore failures.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "bluetoothctl", "--timeout", "1", "scan", "off", stdout=PIPE, stderr=PIPE
        )
        await proc.communicate()
    except Exception:
        pass
