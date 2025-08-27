
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class DetectorParams:
    triggerHigh: float = 8.0
    triggerLow: float = 2.0
    ring_min_ms: int = 30
    dead_time_ms: int = 100

class HitDetector:
    """Simple envelope + hysteresis + ring-min + dead-time detector.
    Feed scalar 'amplitude' samples around 100 Hz (10 ms steps).
    """
    def __init__(self, p: DetectorParams):
        self.p = p
        self.state = "idle"
        self.idle_rms = 1e-6  # track baseline power
        self.since_last_hit_ms = 1e9
        self.elapsed_ms = 0.0
        self.peak = 0.0
        self.sum_sq = 0.0
        self.count = 0

    def update(self, amp: float, dt_ms: float):
        self.elapsed_ms += dt_ms
        self.since_last_hit_ms += dt_ms
        # update baseline
        self.idle_rms = 0.99 * self.idle_rms + 0.01 * (amp * amp)
        env = abs(amp)
        pow_ratio = (env * env) / (self.idle_rms + 1e-9)

        if self.state == "idle":
            if pow_ratio >= self.p.triggerHigh and self.since_last_hit_ms >= self.p.dead_time_ms:
                # start ring
                self.state = "ring"
                self.peak = env
                self.sum_sq = env * env
                self.count = 1
            return None

        if self.state == "ring":
            self.peak = max(self.peak, env)
            self.sum_sq += env * env
            self.count += 1
            if pow_ratio <= self.p.triggerLow and self.count * dt_ms >= self.p.ring_min_ms:
                rms = (self.sum_sq / max(1, self.count)) ** 0.5
                hit = {"peak": float(self.peak), "rms": float(rms), "dur_ms": float(self.count * dt_ms)}
                self.state = "idle"
                self.since_last_hit_ms = 0.0
                return hit
            return None
