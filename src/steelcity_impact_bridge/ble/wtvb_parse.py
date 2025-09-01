from __future__ import annotations
import struct
from typing import Optional, Dict

# WTVB01-BT50 notify frames (0xFFE4) use a 28-byte payload starting with 0x55,0x61
_HDR = 0x55
_FLAG = 0x61
_FRAME_LEN = 28

def _s16(u: int) -> int:
    return struct.unpack('<h', struct.pack('<H', u & 0xFFFF))[0]

def parse_5561(payload: bytes) -> Optional[Dict[str, float]]:
    """Parse a single BT50 notification frame.

    Accepts 28..32 bytes, decodes the first 28. Returns None if header doesn't match.

    Fields (units):
      - VX,VY,VZ: velocity mm/s (signed)
      - ADX,ADY,ADZ: angle degrees (float)
      - TEMP: Celsius (float)
      - DX,DY,DZ: displacement micrometers (signed)
      - HZX,HZY,HZZ: frequency Hz (signed)
    """
    if len(payload) < _FRAME_LEN:
        return None
    b = payload[:_FRAME_LEN]
    if b[0] != _HDR or b[1] != _FLAG:
        return None
    vals = struct.unpack_from('<' + 'H'*13, b, 2)
    (VXL,VYL,VZL, ADXL,ADYL,ADZL, TEMPL,
     DXL,DYL,DZL, HZXL,HZYL,HZZL) = vals

    VX,VY,VZ = _s16(VXL), _s16(VYL), _s16(VZL)                  # mm/s
    ADX,ADY,ADZ = (_s16(ADXL)/32768*180.0,
                   _s16(ADYL)/32768*180.0,
                   _s16(ADZL)/32768*180.0)                     # degrees
    TEMP = _s16(TEMPL)/100.0                                    # °C
    DX,DY,DZ = _s16(DXL), _s16(DYL), _s16(DZL)                  # µm
    HZX,HZY,HZZ = _s16(HZXL), _s16(HZYL), _s16(HZZL)            # Hz (per docs)

    return {
        'VX': float(VX), 'VY': float(VY), 'VZ': float(VZ),
        'ADX': float(ADX), 'ADY': float(ADY), 'ADZ': float(ADZ),
        'TEMP': float(TEMP), 'DX': float(DX), 'DY': float(DY), 'DZ': float(DZ),
        'HZX': float(HZX), 'HZY': float(HZY), 'HZZ': float(HZZ),
    }
