"""H-bridge motor output for the Raspberry Pi Pico (MicroPython)."""

from machine import Pin, PWM

_FULL = 65535


class Motor:
    """
    driver="pwm_dir": pins = (PWM, IN1, IN2)   e.g. TB6612FNG, L298N
    driver="two_pwm": pins = (IN1, IN2)        e.g. DRV8833, cheap dual bridges
    """

    def __init__(self, pins, driver="pwm_dir", freq=20_000,
                 invert=False, min_duty=0.0, max_duty=1.0):
        self._driver = driver
        self._sign = -1 if invert else 1
        self._min = min_duty
        self._max = max_duty
        self.duty = 0.0

        if driver == "pwm_dir":
            self._pwm = PWM(Pin(pins[0]))
            self._pwm.freq(freq)
            self._in1 = Pin(pins[1], Pin.OUT, value=0)
            self._in2 = Pin(pins[2], Pin.OUT, value=0)
        elif driver == "two_pwm":
            self._p1 = PWM(Pin(pins[0]))
            self._p2 = PWM(Pin(pins[1]))
            self._p1.freq(freq)
            self._p2.freq(freq)
        else:
            raise ValueError("driver must be 'pwm_dir' or 'two_pwm'")
        self.set(0.0)

    def set(self, u):
        """u in [-1.0, 1.0]; sign is direction, magnitude is duty cycle."""
        u *= self._sign
        if u > self._max:
            u = self._max
        elif u < -self._max:
            u = -self._max

        mag = u if u >= 0 else -u
        if mag < 1e-4:
            mag = 0.0
        elif mag < self._min:
            # Deadband compensation: below min_duty the motor only buzzes, so
            # push it up to the smallest duty that actually turns the shaft.
            mag = self._min
        self.duty = mag if u >= 0 else -mag

        d = int(mag * _FULL)
        if self._driver == "pwm_dir":
            if mag == 0.0:
                self._in1.value(0)
                self._in2.value(0)
            elif u > 0:
                self._in1.value(1)
                self._in2.value(0)
            else:
                self._in1.value(0)
                self._in2.value(1)
            self._pwm.duty_u16(d)
        else:
            if u >= 0:
                self._p1.duty_u16(d)
                self._p2.duty_u16(0)
            else:
                self._p1.duty_u16(0)
                self._p2.duty_u16(d)

    def brake(self):
        if self._driver == "pwm_dir":
            self._in1.value(1)
            self._in2.value(1)
            self._pwm.duty_u16(_FULL)
        else:
            self._p1.duty_u16(_FULL)
            self._p2.duty_u16(_FULL)
        self.duty = 0.0

    def stop(self):
        self.set(0.0)
