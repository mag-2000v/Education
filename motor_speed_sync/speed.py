"""Turn encoder counts into a filtered speed in rpm."""

from time import ticks_us, ticks_diff


class SpeedEstimator:
    """
    rpm = (delta_counts / counts_per_rev) / dt_seconds * 60

    `alpha` is a first order low-pass on the result: 1.0 = raw (noisy),
    0.2 = heavily smoothed (adds lag to the control loop).
    """

    def __init__(self, encoder, counts_per_rev, alpha=1.0):
        self._enc = encoder
        self._cpr = float(counts_per_rev)
        self._alpha = alpha
        self._last_count = encoder.read()
        self._last_us = ticks_us()
        self.rpm = 0.0
        self.raw_rpm = 0.0
        self.revs = 0.0          # signed, accumulated since start/reset

    def update(self):
        now = ticks_us()
        c = self._enc.read()
        dt = ticks_diff(now, self._last_us)
        if dt <= 0:
            return self.rpm
        d = c - self._last_count
        self._last_count = c
        self._last_us = now

        self.raw_rpm = (d / self._cpr) * (60_000_000.0 / dt)
        self.rpm += self._alpha * (self.raw_rpm - self.rpm)
        self.revs = c / self._cpr
        return self.rpm

    def reset(self):
        self._enc.reset()
        self._last_count = 0
        self._last_us = ticks_us()
        self.rpm = 0.0
        self.raw_rpm = 0.0
        self.revs = 0.0
