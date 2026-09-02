# Motor speed measurement + two-motor synchronisation (Raspberry Pi Pico, MicroPython)

Measures the speed of two DC motors from their quadrature encoders and drives
both at the same speed with a per-motor PI controller plus a cross-coupling
term. Extra GPIOs are toggled so that a logic analyser can verify the firmware
independently.

## Files

| file | what it does |
|---|---|
| `config.py` | **the only file you edit** - pins, encoder resolution, gains |
| `encoder.py` | interrupt-driven x4 / x2 / x1 quadrature decoder |
| `motor.py` | H-bridge output (PWM+DIR, or two-PWM drivers) |
| `speed.py` | counts -> rpm, with a first-order filter |
| `hardware.py` | builds everything from `config.py` |
| `measure_speed.py` | step 1: open-loop ramp, prints duty vs rpm, suggests gains |
| `sync_two_motors.py` | step 2: closed-loop, both motors at one target rpm |

Copy all of them to the Pico (Thonny, `mpremote cp *.py :`, rshell, ...), then:

```python
>>> import measure_speed
>>> measure_speed.run()          # note the suggested MIN_DUTY / KFF / KP
>>> import sync_two_motors
>>> sync_two_motors.run(target_rpm=60, seconds=15)
```

## How the speed is computed

```
rpm = (delta_counts / counts_per_output_revolution) / delta_t_seconds * 60

counts_per_output_revolution = ENC_PPR * DECODE_MODE * GEAR_RATIO
```

`DECODE_MODE = 4` counts both edges of both channels, which is the highest
resolution an incremental encoder can give and also the direction-safe one.

Resolution vs. sample rate is the trade-off to be aware of: at 100 Hz sampling
and 1320 counts/rev (11 PPR x4 x30:1), one count of quantisation is
`60/1320*100 = 4.5 rpm`. If the reading is too coarse, either sample slower,
raise the encoder resolution, or switch to measuring the *time between edges*
instead of counting edges in a fixed window (worth doing below ~5 rev/s).

## Using the logic analyser

Probe these, common ground with the Pico:

| signal | why |
|---|---|
| encoder A and B of one motor | check the 90 degree phase relationship and that no edges are ringing/bouncing |
| `LA_REV_PINS[0]`, `LA_REV_PINS[1]` | one square-wave **cycle per output revolution**; the analyser's frequency measurement x 60 is the rpm, computed from the firmware's own counter |
| `LA_LOOP_PIN` | high while a control tick runs. Period = actual sample rate, width = CPU time per tick. If the width approaches the period, the loop is overrunning and the speed numbers are wrong |
| motor PWM pin | duty cycle and PWM frequency as actually emitted |
| motor IN1/IN2 | direction changes, and that both are never high while PWM is running |

Three checks worth doing with it:

1. **Encoder sanity** - measure the frequency of channel A while the motor runs
   at a known duty. Expected: `f_A = rpm/60 * ENC_PPR * GEAR_RATIO`. If the
   measured frequency and the printed rpm disagree, `ENC_PPR` or `GEAR_RATIO`
   in `config.py` is wrong.
2. **Missed edges** - if `f_A` is stable but the printed rpm reads low and
   jittery, the Python interrupts are not keeping up. Drop to
   `DECODE_MODE = 2`, or move to the PIO decoder (below).
3. **Sync quality** - put both `LA_REV_PINS` on the analyser and watch the two
   square waves. Same frequency = same speed. A phase that slowly walks apart
   is exactly the drift `KSYNC` is there to remove.

Sample rate: pick at least 10x the fastest encoder edge rate, e.g. 2 MS/s for
a 50 kHz channel. Most cheap 8-channel analysers do 24 MS/s, which is plenty.

## Making both motors run at the same speed

Two layers, both in `sync_two_motors.py`:

- **Per-motor PI on velocity.** Equal PWM duty does *not* mean equal speed -
  two "identical" motors differ by 10-20% in friction and back-EMF constant.
  Each motor gets its own feedback loop onto the same rpm target.
- **Cross-coupling on position.** Even with perfect velocity loops, a small
  steady error integrates into an ever-growing difference in revolutions
  turned. The term `KSYNC * (revs0 - revs1)` is subtracted from motor 0 and
  added to motor 1, so the two shafts stay locked to each other, not just
  close in speed. For a two-wheel robot this is the difference between
  "roughly straight" and "straight".

Tuning order:

1. `KFF` from the calibration run - it does most of the work, feedback only
   trims.
2. `KP` up until the response is fast but not oscillating, then back off ~30%.
3. `KI` up until steady-state error disappears within a second or two.
   `INTEGRAL_LIMIT` stops the integrator winding up while a motor is stalled.
4. `KSYNC` last. Too high makes the two motors fight each other and buzz;
   start at 0.1 and raise it until `sync_err` in the telemetry stops drifting.

## When the interrupt version is not enough

The Python interrupt handlers cope with roughly 5000 edges/second in total.
Above that (high-line-count optical encoders, or fast motors) the RP2040's PIO
should do the counting in hardware instead - it can decode at MHz rates with
zero CPU load. The rest of this project stays the same; only `encoder.py` is
replaced. Say the word and I'll write that version.

## Safety

Check the motor supply current against the H-bridge's rating before running.
Never power the motors from the Pico's 3V3 rail; share only ground. A flyback
capacitor across the motor terminals and a common-mode choke or short, twisted
encoder wiring will save a lot of debugging - encoder glitches from motor noise
look exactly like a software bug.

## What I still need from you

Everything below maps onto one line in `config.py`. The code runs with the
defaults, but the numbers it prints are only correct once these are right.

**Encoder / feedback device (the big one)**
1. Is the feedback an **incremental encoder** (square-wave A, B, sometimes Z),
   a **resolver** (analog sine/cosine, needs an excitation signal and an
   RDC chip - a logic analyser cannot read it and this code does not apply),
   an **absolute serial encoder** (Tamagawa's 2-wire serial / BiSS / SSI - a
   different protocol entirely), or a **tachogenerator** (a DC voltage
   proportional to speed - read with the ADC, no pulses at all)?
   The label `TS3727N83E8 / SER NO 8Z24 / TAMAGAWA SEIKI` is the *motor*
   type; what matters here is what is bolted to its rear shaft.
2. How many wires come out of the feedback connector, and their colours/labels?
3. Pulses per revolution, and its supply voltage (5 V encoder outputs must be
   level-shifted or divided down - the Pico's GPIOs are **3.3 V only and not
   5 V tolerant**).
4. Gearbox ratio, and whether the encoder is before or after the gearbox.

**Motors and driver**
5. Motor supply voltage and stall/no-load current. Tamagawa industrial DC
   servo motors are typically 24-100 V and several amps; hobby drivers like
   the TB6612/DRV8833 will not survive that, so tell me the driver you have.
6. Driver type and its control inputs (PWM+DIR, IN1/IN2, or PWM+enable),
   and its maximum PWM frequency.
7. Which Pico GPIOs you have actually wired, for the motors and the encoders.

**What "the same speed" has to mean**
8. A fixed target rpm, or "follow whatever motor 0 does" (master/slave)?
9. Speed-matched only, or position-locked (must not drift apart over minutes)?
10. Expected speed range and how fast it has to reach the setpoint.

**Logic analyser**
11. Model and maximum sample rate, and how many channels you can spare.
12. Is it there to debug the encoder wiring, to validate the firmware's speed
    number against an independent measurement, or to be the actual measuring
    instrument for a report?
