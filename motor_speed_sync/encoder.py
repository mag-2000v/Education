"""
Quadrature encoder reader for the RP2040 (Raspberry Pi Pico), MicroPython.

Interrupt driven, x4 / x2 / x1 decoding. Good for roughly 5000 encoder edges
per second in total across all encoders; above that the Python interrupt
handlers start to miss edges and you need the PIO version instead (see
README, "When the interrupt version is not enough").
"""

from machine import Pin, disable_irq, enable_irq

# state = (A << 1) | B.  index = (previous_state << 2) | new_state
# +1 for the forward Gray sequence 00 -> 10 -> 11 -> 01, -1 for the reverse,
# 0 for "no change" and for illegal double transitions (a missed edge).
_TABLE = (0, -1, 1, 0,
          1, 0, 0, -1,
          -1, 0, 0, 1,
          0, 1, -1, 0)


class QuadratureEncoder:
    def __init__(self, pin_a, pin_b, mode=4, invert=False,
                 counts_per_rev=None, la_pin=None):
        self._a = Pin(pin_a, Pin.IN, Pin.PULL_UP)
        self._b = Pin(pin_b, Pin.IN, Pin.PULL_UP)
        self._mode = mode
        self._sign = -1 if invert else 1
        self.count = 0

        # Optional square wave for the logic analyser: one full cycle per
        # revolution of the output shaft, so the analyser can measure speed
        # independently of anything the firmware prints.
        self._la = Pin(la_pin, Pin.OUT, value=0) if la_pin is not None else None
        self._half = int(counts_per_rev // 2) if counts_per_rev else 0
        self._acc = 0
        self._la_level = 0

        self._state = (self._a.value() << 1) | self._b.value()

        both = Pin.IRQ_RISING | Pin.IRQ_FALLING
        if mode == 4:
            self._a.irq(handler=self._on_edge, trigger=both)
            self._b.irq(handler=self._on_edge, trigger=both)
        elif mode == 2:
            self._a.irq(handler=self._on_edge_a, trigger=both)
        elif mode == 1:
            self._a.irq(handler=self._on_edge_a, trigger=Pin.IRQ_RISING)
        else:
            raise ValueError("mode must be 1, 2 or 4")

    # -- interrupt handlers: keep these short and allocation free ------------
    def _on_edge(self, _pin):
        s = (self._a.value() << 1) | self._b.value()
        d = _TABLE[(self._state << 2) | s]
        self._state = s
        if d:
            self.count += d * self._sign
            self._mark(d * self._sign)

    def _on_edge_a(self, _pin):
        # Direction comes from channel B sampled at the edge of A.
        d = 1 if self._a.value() != self._b.value() else -1
        self.count += d * self._sign
        self._mark(d * self._sign)

    def _mark(self, d):
        if self._half:
            self._acc += d
            if self._acc >= self._half:
                self._acc -= self._half
                self._toggle()
            elif self._acc <= -self._half:
                self._acc += self._half
                self._toggle()

    def _toggle(self):
        if self._la is not None:
            self._la_level ^= 1
            self._la.value(self._la_level)

    # -- API -----------------------------------------------------------------
    def read(self):
        """Atomic read of the accumulated count."""
        s = disable_irq()
        c = self.count
        enable_irq(s)
        return c

    def reset(self):
        s = disable_irq()
        self.count = 0
        self._acc = 0
        enable_irq(s)
