from __future__ import annotations
from typing import List


def classify_signals(b: bytes) -> List[str]:
    """Return a list of recognized AMG signal names for a notification frame.

    Initial implementation recognizes only T0 (beep/start). Additional
    patterns can be appended as we learn the protocol.
    """
    if not b:
        return []
    out: List[str] = []
    # T0: explicit subtype 0x01 0x05, or legacy 14-byte pattern
    if b[0] == 0x01 and ((len(b) >= 2 and b[1] == 0x05) or (len(b) == 14 and b[5:13] == b"\x00" * 8)):
        out.append("T0")
    # Heuristic mappings (experimental):
    # Many observed frames begin with 0x01 followed by a subtype. Based on field logs,
    # we tentatively map 0x09 to ARROW_END and 0x08 to TIMEOUT_END.
    # These will be tuned as we gather more labeled captures.
    if len(b) >= 2 and b[0] == 0x01:
        if b[1] == 0x03:
            out.append("SHOT_RAW")  # Individual shot detection
        elif b[1] == 0x09:
            out.append("ARROW_END")
        elif b[1] == 0x08:
            out.append("TIMEOUT_END")
    # Power-off is not yet confidently identified; handle via disconnect in bridge for now.
    return out
