"""
Step 1: measure the speed of each motor, open loop.

Run this first. It ramps the duty cycle up and down, prints a CSV of
duty vs. rpm for both motors, and at the end suggests values for
MIN_DUTY and KFF in config.py.

While it runs, the logic analyser sees:
  LA_LOOP_PIN    - high for the duration of every sample tick
  LA_REV_PINS[i] - a square wave, one full cycle per output-shaft revolution
  the encoder A/B pins and the motor PWM/direction pins, if you probe them

    >>> import measure_speed
    >>> measure_speed.run()
"""

from time import sleep_ms, ticks_ms, ticks_diff
import config
import hardware


def _dwell(speeds, motors, duty, ms, probe):
    """Hold a duty cycle for `ms`, return the mean rpm of the last half."""
    for m in motors:
        m.set(duty)
    period = 1000 // config.LOOP_HZ
    t0 = ticks_ms()
    acc = [0.0, 0.0]
    n = 0
    while ticks_diff(ticks_ms(), t0) < ms:
        if probe:
            probe.value(1)
        for s in speeds:
            s.update()
        if probe:
            probe.value(0)
        if ticks_diff(ticks_ms(), t0) > ms // 2:
            acc[0] += speeds[0].rpm
            acc[1] += speeds[1].rpm
            n += 1
        sleep_ms(period)
    if n == 0:
        return speeds[0].rpm, speeds[1].rpm
    return acc[0] / n, acc[1] / n


def run(steps=10, dwell_ms=1200, reverse=True):
    encoders, speeds, motors = hardware.build()
    probe = hardware.loop_probe()

    print("# counts per output revolution:", config.CPR_OUTPUT)
    print("duty,rpm0,rpm1")
    samples = []
    duties = [i / steps for i in range(0, steps + 1)]
    if reverse:
        duties += [-d for d in duties[1:]]

    try:
        for d in duties:
            r0, r1 = _dwell(speeds, motors, d, dwell_ms, probe)
            print("%.3f,%.2f,%.2f" % (d, r0, r1))
            if d > 0:
                samples.append((d, r0, r1))
    finally:
        for m in motors:
            m.stop()

    _suggest(samples)
    return samples


def _suggest(samples):
    moving = [s for s in samples if abs(s[1]) > 5.0 and abs(s[2]) > 5.0]
    if len(moving) < 2:
        print("# not enough movement to fit - check wiring and supply voltage")
        return
    print("# MIN_DUTY  ~ %.3f   (lowest duty at which both motors turned)"
          % moving[0][0])
    top = moving[-1]
    rpm = (abs(top[1]) + abs(top[2])) / 2.0
    print("# max rpm   ~ %.1f at duty %.2f" % (rpm, top[0]))
    if rpm > 1.0:
        print("# KFF       ~ %.6f   (duty per rpm)" % (top[0] / rpm))
    d0, r0 = moving[0][0], (abs(moving[0][1]) + abs(moving[0][2])) / 2.0
    span = rpm - r0
    if span > 1.0:
        print("# KP        ~ %.6f   (start at 1/10 of the open-loop slope)"
              % ((top[0] - d0) / span / 10.0))
