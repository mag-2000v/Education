# How to connect everything

GPIO numbers below are the `GPn` names used in `config.py`; the number in
brackets is the physical pin on the Pico board (1 = top-left, next to the USB
connector, counting anticlockwise).

## 1. Power and ground - do this first

```
motor supply (+)  --------> H-bridge VM / VMOT / +V
motor supply (-)  --------+
                          |
Pico GND [3,8,13,...] ----+---- H-bridge GND ---- encoder GND ---- analyser GND
```

Rules that save hardware:

- **One common ground.** The Pico, the driver, the encoder and the logic
  analyser must share it, or every measurement is noise.
- **Never** power motors from the Pico's `3V3(OUT)` [36]. That rail is good for
  ~300 mA and is the same rail the RP2040 runs on; a motor brown-out resets the
  Pico mid-measurement.
- Power the Pico from USB while bench testing, or from `VSYS` [39] through a
  regulator (`VSYS` accepts 1.8-5.5 V). Do not back-feed `VBUS` [40] while USB
  is plugged in.
- 100 µF or more of electrolytic capacitance across the H-bridge's motor
  supply, right at the driver, plus 100 nF ceramic. Brushed motors also want
  three 100 nF ceramics at the motor terminals (each terminal to case, and
  across the pair).

## 2. Encoder -> Pico

The Pico's GPIOs are **3.3 V and not 5 V tolerant**. Check the encoder's output
voltage before connecting anything.

**Encoder with 3.3 V push-pull outputs** - direct:

```
encoder A  -> GP2  [4]      motor 0
encoder B  -> GP3  [5]
encoder A  -> GP4  [6]      motor 1
encoder B  -> GP5  [7]
encoder Vcc -> 3V3(OUT) [36]      (only if it draws < ~50 mA)
encoder GND -> GND [3]
```

**Encoder with 5 V outputs** - level shift each channel. Cheapest correct
option is a resistor divider per channel (good to a few hundred kHz):

```
5V signal ---[ 1k ]---+--- GPn
                      |
                    [ 1.5k ]
                      |
                     GND           gives 5.0 V * 1.5/2.5 = 3.0 V
```

Prefer 1k/1.5k over the more common 10k/15k: the lower source impedance drives
the analyser's probe capacitance cleanly past 100 kHz, at a cost of 2 mA per
channel. Use 10k/15k only if the encoder's drive is too weak for that.

Better above ~200 kHz, or with long cables: a 74LVC245 or 74AHCT-family buffer
powered from 3V3, or a dedicated bidirectional level-shifter board.

**Open-collector / open-drain encoder** (very common on industrial units): the
output only pulls low, so add a 2.2k-10k pull-up **to 3V3, not to 5 V**. The
internal pull-ups that `encoder.py` enables (~50-80 k) work at low speed but
are too weak for long cables - fit external ones.

**Line-driver / differential encoder (A, /A, B, /B, RS-422)**: do not connect
the pairs straight to the Pico. Use an AM26LS32 / SN75175 / DS26C32 receiver
(120 Ω across each pair at the receiver) and take the single-ended outputs to
the GPIOs. Power the receiver from 3V3, not 5 V, and its outputs land at 3.3 V
with no divider needed. Ignoring `/A` and `/B` and using only `A` and `B` sometimes works on
a short bench cable, but that throws away the entire point of a differential
encoder next to a switching motor drive.

**Index / Z channel**: not needed for speed. Wire it if you later want
once-per-revolution position.

Wiring hygiene: twist A with GND and B with GND, keep encoder wires away from
the motor leads, and use shielded cable grounded at the Pico end only. Encoder
glitches caused by motor noise look exactly like a firmware bug.

## 3. Motor driver -> Pico

### TB6612FNG (up to ~1.2 A/channel) - `DRIVER = "pwm_dir"`

```
PWMA  <- GP6  [9]        AIN1 <- GP7  [10]      AIN2 <- GP8  [11]     motor 0
PWMB  <- GP9  [12]       BIN1 <- GP10 [14]      BIN2 <- GP11 [15]     motor 1
STBY  <- 3V3 [36], or a GPIO set as STANDBY_PIN in config.py
VCC   <- 3V3 [36]        (logic supply)
VM    <- motor supply    GND -> common ground
AO1/AO2 -> motor 0 terminals    BO1/BO2 -> motor 1 terminals
```

### DRV8833 (up to ~1.5 A/channel) - `DRIVER = "two_pwm"`

```
AIN1 <- GP6 [9]    AIN2 <- GP7 [10]     -> MOTOR_PINS[0] = (6, 7, 0)
BIN1 <- GP9 [12]   BIN2 <- GP10 [14]    -> MOTOR_PINS[1] = (9, 10, 0)
nSLEEP <- 3V3 or a GPIO;  VM <- motor supply;  GND common
```

### L298N module (up to ~2 A/channel, drops ~2 V) - `DRIVER = "pwm_dir"`

Remove the ENA/ENB jumpers, then `ENA <- GP6`, `IN1 <- GP7`, `IN2 <- GP8`,
`ENB <- GP9`, `IN3 <- GP10`, `IN4 <- GP11`. Keep `PWM_FREQ_HZ` at 1-5 kHz -
the L298N's bipolar transistors are too slow for 20 kHz.

### BTS7960 / IBT-2 (up to ~40 A) - for a real industrial motor

```
RPWM <- GP6 [9]     LPWM <- GP7 [10]     -> DRIVER = "two_pwm", pins (6, 7, 0)
R_EN + L_EN <- 3V3 [36]
B+ / B- <- motor supply,  M+ / M- <- motor
```

If the Tamagawa motor is a 24-100 V industrial DC servo drawing several amps,
none of the first three drivers will survive it - that class of motor needs a
BTS7960-style bridge or a proper servo amplifier, and the Pico then produces
only the PWM/direction signals into that amplifier's opto-isolated inputs.

## 4. Logic analyser

```
CH0 -> GP2  [4]   encoder A, motor 0
CH1 -> GP3  [5]   encoder B, motor 0
CH2 -> GP4  [6]   encoder A, motor 1
CH3 -> GP5  [7]   encoder B, motor 1
CH4 -> GP15 [20]  LA_LOOP_PIN - high while a control tick runs
CH5 -> GP14 [19]  LA_REV_PINS[0] - one cycle per revolution, motor 0
CH6 -> GP13 [17]  LA_REV_PINS[1] - one cycle per revolution, motor 1
CH7 -> GP6  [9]   motor 0 PWM
GND -> Pico GND [8]    <- not optional
```

Analyser settings: sample at 10x the fastest edge rate you expect
(`f_A = rpm/60 * PPR * gear_ratio`), so 2 MS/s covers a 50 kHz channel. In
sigrok/PulseView or Saleae Logic, add the built-in **quadrature decoder** on
CH0/CH1 to get counts and direction, and a **frequency/period measurement** on
CH5 - that frequency times 60 is the rpm, measured independently of anything
the firmware prints. The two numbers agreeing is the proof that the maths in
`config.py` is right.

If the analyser has a probe to spare, put one on the motor supply's ground at
the driver: a ground that bounces on PWM edges explains most "impossible"
encoder readings.

## 5. Bring-up order

1. Pico alone, no motor supply: `import measure_speed` must import cleanly.
2. Turn each motor shaft by hand and check `encoders[0].read()` changes sign
   with direction. If it counts the wrong way, set `ENC_INVERT` in `config.py`.
3. Motor supply on, motors clamped down or wheels off the ground. Run
   `measure_speed.run()` and watch that a positive duty gives a positive rpm.
   If not, flip `MOTOR_INVERT`.
4. Only then run `sync_two_motors.run()`.
