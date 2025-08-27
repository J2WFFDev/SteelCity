
from steelcity_impact_bridge.detector import HitDetector, DetectorParams

def run_stream(samples, dt_ms=10.0):
    d = HitDetector(DetectorParams(triggerHigh=8.0, triggerLow=2.0, ring_min_ms=30, dead_time_ms=100))
    hits = []
    for a in samples:
        h = d.update(a, dt_ms)
        if h:
            hits.append(h)
    return hits

def test_no_hit_noise():
    import random
    samples = [random.uniform(-0.5, 0.5) for _ in range(200)]
    assert run_stream(samples) == []

def test_single_hit_with_ring():
    # Step then ring decay
    samples = [0.2]*10 + [5.0] + [4.0,3.0,2.0,1.0] + [0.3]*50
    hits = run_stream(samples)
    assert len(hits) == 1
    assert hits[0]["dur_ms"] >= 30

def test_two_hits_within_deadtime():
    samples = [0.2]*10 + [5.0,4.0,3.0,2.0] + [0.3]*5 + [5.0,4.0,3.0,2.0] + [0.3]*50
    hits = run_stream(samples)
    assert len(hits) == 1
