from steelcity_impact_bridge.ble.amg_signals import classify_signals


def hexs(s: str) -> bytes:
    s = s.replace(" ", "").replace("-", ":").replace(",", ":")
    parts = [p for p in s.split(":") if p]
    return bytes(int(p, 16) for p in parts)


def test_classify_t0_patterns():
    # Explicit subtype 0x01 0x05
    assert "T0" in classify_signals(hexs("01 05 00 00"))
    # Legacy 14-byte with zero mid
    legacy = hexs("01 00 00 00 00 00 00 00 00 00 00 00 00 01")
    assert "T0" in classify_signals(legacy)


def test_classify_arrow_and_timeout():
    # Experimental mappings based on subtype
    assert "ARROW_END" in classify_signals(hexs("01 09 00 00 00 00"))
    assert "TIMEOUT_END" in classify_signals(hexs("01 08 00 00 00 00"))
