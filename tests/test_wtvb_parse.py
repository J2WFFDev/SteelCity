from steelcity_impact_bridge.ble.wtvb_parse import parse_5561

def le16(u):
    return bytes((u & 0xFF, (u >> 8) & 0xFF))

def test_parse_5561_valid_frame():
    # Build a 28-byte frame: 0x55 0x61 + 13x uint16 little-endian
    # Use values that exercise signed conversions and scaling
    VXL, VYL, VZL = 100, 0xFFFF, 0  # 100, -1, 0 mm/s
    ADXL, ADYL, ADZL = 0, 0x8000, 0x4000  # 0°, -180°, +90° before scaling
    TEMPL = 2500  # 25.00 C
    DXL, DYL, DZL = 100, 0xFF38, 300  # 100, -200, 300 um
    HZXL, HZYL, HZZL = 10, 20, 30

    body = b"".join([
        le16(VXL), le16(VYL), le16(VZL),
        le16(ADXL), le16(ADYL), le16(ADZL),
        le16(TEMPL),
        le16(DXL), le16(DYL), le16(DZL),
        le16(HZXL), le16(HZYL), le16(HZZL),
    ])
    payload = bytes([0x55, 0x61]) + body
    assert len(payload) == 28

    pkt = parse_5561(payload)
    assert pkt is not None
    assert pkt['VX'] == 100.0
    assert pkt['VY'] == -1.0
    assert pkt['VZ'] == 0.0
    # Angle scaling: s16/32768*180
    assert abs(pkt['ADX'] - 0.0) < 1e-6
    assert abs(pkt['ADY'] - (-180.0)) < 1e-6
    assert abs(pkt['ADZ'] - (180.0 * (0x4000/32768.0))) < 1e-6  # ~90.0
    assert abs(pkt['TEMP'] - 25.0) < 1e-6
    assert pkt['DX'] == 100.0 and pkt['DY'] == -200.0 and pkt['DZ'] == 300.0
    assert pkt['HZX'] == 10.0 and pkt['HZY'] == 20.0 and pkt['HZZ'] == 30.0

def test_parse_5561_invalid_header():
    bad = bytes([0x00, 0x00]) + b"\x00"*26
    assert parse_5561(bad) is None
