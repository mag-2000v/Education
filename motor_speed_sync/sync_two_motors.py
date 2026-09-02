"""
Step 2: make both motors run at the same speed.

Two things happen every control tick:

  1. Each motor gets its own PI velocity controller, so it tracks the
     target rpm regardless of load, friction or supply sag.
  2. A cross-coupling term compares the total revolutions turned by each
     motor and pushes the one that is ahead down and the one that is behind
     up. PI alone makes both motors *about* the right speed; the coupling
     term is what stops a slow drift apart from accumulating.

    >>> import sync_two_motors
    >>> sync_two_motors.run(target_rpm=60, seconds=10)
"""

from time import sleep_ms, ticks_ms, ticks_diff
import config
import hardware


class PI:
    def __init__(self, kp, ki, kff, limit):
        self.kp = kp
        self.ki = ki
        self.kff = kff
        self.limit = limit
        self.i = 0.0

    def step(self, target, measured, dt):
        e = target - measured
        self.i += self.ki * e * dt
        if self.i > self.limit:
            self.i = self.limit
        elif self.i < -self.limit:
            self.i = -self.limit
        return self.kff * target + self.kp * e + self.i

    def reset(self):
        self.i = 0.0


def run(target_rpm=60.0, seconds=10.0, telemetry_hz=10):
    encoders, speeds, motors = hardware.build()
    probe = hardware.loop_probe()
    pids = [PI(config.KP, config.KI, config.KFF, config.INTEGRAL_LIMIT)
            for _ in range(2)]
    for s in speeds:
        s.reset()

    period_ms = 1000 // config.LOOP_HZ
    dt = 1.0 / config.LOOP_HZ
    tel_every = max(1, int(config.LOOP_HZ / telemetry_hz))
    t_end = ticks_ms() + int(seconds * 1000)
    n = 0

    print("ms,target,rpm0,rpm1,duty0,duty1,revs0,revs1,sync_err")
    try:
        t0 = ticks_ms()
        next_tick = t0
        while ticks_diff(t_end, ticks_ms()) > 0:
            if probe:
                probe.value(1)

            speeds[0].update()
            speeds[1].update()

            # position-level synchronisation: revolutions turned so far
            sync_err = speeds[0].revs - speeds[1].revs
            corr = config.KSYNC * sync_err

            u0 = pids[0].step(target_rpm, speeds[0].rpm, dt) - corr
            u1 = pids[1].step(target_rpm, speeds[1].rpm, dt) + corr
            motors[0].set(u0)
            motors[1].set(u1)

            if probe:
                probe.value(0)

            n += 1
            if n % tel_every == 0:
                print("%d,%.1f,%.1f,%.1f,%.3f,%.3f,%.2f,%.2f,%.3f" % (
                    ticks_diff(ticks_ms(), t0), target_rpm,
                    speeds[0].rpm, speeds[1].rpm,
                    motors[0].duty, motors[1].duty,
                    speeds[0].revs, speeds[1].revs, sync_err))

            next_tick += period_ms
            slack = ticks_diff(next_tick, ticks_ms())
            if slack > 0:
                sleep_ms(slack)
            else:
                next_tick = ticks_ms()   # loop is overrunning; resynchronise
    finally:
        for m in motors:
            m.stop()
    return speeds


if __name__ == "__main__":
    run()
