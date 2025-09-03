from __future__ import annotations
from typing import Optional


def le16(b: bytes) -> int:
    return int.from_bytes(b, "little", signed=False)


def parse_frame_hex(h: str) -> Optional[dict]:
    """Parse a 14-byte AMG frame represented as a hex string.

    Returns a dict with raw byte fields, p1..p4 16-bit values, tail byte and original hex
    or None if parsing fails or length is unexpected.
    """
    if not isinstance(h, str):
        return None
    s = h.strip().lower()
    if s.startswith("0x"):
        s = s[2:]
    # Allow space-separated hex
    s = s.replace(" ", "")
    try:
        b = bytes.fromhex(s)
    except Exception:
        return None
    if len(b) != 14:
        return None
    return dict(
        b0=b[0], b1=b[1], b2=b[2], b3=b[3], b4=b[4],
        p1=le16(b[5:7]), p2=le16(b[7:9]), p3=le16(b[9:11]), p4=le16(b[11:13]),
        tail=b[13], hex=s,
    )


def is_shot(f: dict) -> bool:
    """Heuristic: determine whether a parsed frame represents a shot.

    From captures: shot frames have b1==0x03 and b2==b3 with p1>0.
    """
    try:
        return f.get("b1") == 0x03 and f.get("b2") == f.get("b3") and f.get("p1", 0) > 0
    except Exception:
        return False
