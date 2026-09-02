# Identifying the TS3727N83E8 and its feedback device

## What the type number tells us

`TS3727N83E8` is a **Tamagawa TS3000-series brushed DC servo motor**. The
converging evidence from distributor and repair listings:

- Servo repair houses list the siblings `TS3727N-B5` and `TS3727N75E5` as
  "TAMAGAWA SEIKI Servo Motor".
- A Tamagawa distributor catalogue places `TS3727` in the DC motor
  (brush type) lineup.
- The nearby `TS3053` is described on CNCZone as a "brushed servo motor".
- The naming pattern matches other Tamagawa DC servo motors, e.g.
  `TS907N25E137` ("DC SERVO MOTOR") and `1906N122E13`
  ("DC Servomotor-Encoder 43 V 5.1 A 200 W").

`SER NO 8Z24` is a production/date code and carries no specification.

## What is *not* published

The `N83E8` suffix encodes the winding and the fitted options - and Tamagawa
has never published a public decode table for the TS3000 series. Neither the
voltage/current/torque rating nor the feedback type can be recovered from the
type number alone. (The CNCZone thread on the sibling TS3053 is someone
hitting exactly this wall.)

So two things must be established from the motor itself.

## 1. Electrical rating - before applying power

This is an industrial servo motor, not a hobby gearmotor. Comparable models in
the family run **40-100 V at several amps, 100-750 W**. Consequences:

- The TB6612FNG, DRV8833 and L298N in `WIRING.md` are all far too small.
  Use a BTS7960/IBT-2 class bridge, or a proper DC servo amplifier that the
  Pico feeds PWM+DIR into.
- Measure the armature resistance across the two power terminals first. A
  brushed servo of this class typically reads a few ohms; stall current is
  `V_supply / R_armature`, and that is the number the driver must survive.
- Start on a current-limited bench supply at a low voltage. If it turns at
  12 V, it will turn at 12 V for testing - you do not need its rated voltage
  to develop and tune the control loop.

## 2. Which feedback device is fitted

Tamagawa offered these motors with a **tachogenerator**, an **incremental
encoder**, or a **resolver**, and only one of the three works with the code in
this repo. Determine it like this, in order:

**a. Look at the rear housing.** The feedback device carries its own nameplate
with its own Tamagawa part number. Roughly: `TS20xx`, `TS26xx`, `TS56xx`
(Smartsyn/BRX/BRT) = resolver; `TS51xx`, `TS52xx`, `OIH`/`OME` = incremental
encoder; no separate plate, just two terminals = tachogenerator.

**b. Count the wires** on the feedback connector:

| wires | almost certainly |
|---|---|
| 2 | tachogenerator |
| 4 (two pairs) | resolver, or a bare A/B encoder |
| 5-6 | incremental encoder, single-ended (Vcc, GND, A, B, Z) |
| 6-7 | resolver (R1 R2 excitation + S1 S3 + S2 S4) |
| 8-10 | incremental encoder, differential (A /A B /B Z /Z Vcc GND) |

**c. Measure, with the motor unpowered:**

- **Ohmmeter across each candidate pair.** A resolver winding reads roughly
  10-200 Ω and every pair reads *something*. An encoder reads open circuit
  between signal pins. A tachogenerator reads a few ohms on its single pair.
- **Spin the shaft by hand with a multimeter on DC volts.** A tachogenerator
  outputs a DC voltage proportional to speed that reverses sign with
  direction - typically 3-10 V per 1000 rpm. An encoder outputs nothing at
  all until you power it. A resolver outputs nothing without an excitation
  carrier.
- **Power a suspected encoder** (check 5 V vs 12 V first) and put the logic
  analyser on the signal pins while turning the shaft slowly by hand. Two
  square waves 90 degrees apart = incremental encoder, and everything in this
  repo applies.

## What each outcome means for this project

| fitted device | what to do |
|---|---|
| **incremental encoder** | Use this repo as written. Set `ENC_PPR` from the count of edges per hand-turned revolution on the analyser, `GEAR_RATIO = 1.0` if it is direct on the motor shaft. Level-shift if its outputs are 5 V. |
| **tachogenerator** | No pulses exist. Speed comes from `machine.ADC` reading the tacho voltage through a divider (and a clamp), scaled by the tacho constant in V/1000 rpm. The PI and cross-coupling logic in `sync_two_motors.py` is unchanged - only the measurement is swapped. A logic analyser cannot see an analog signal; you would need a scope. |
| **resolver** | Needs a ~7 kHz excitation source and an RDC chip (AD2S1210 / AD2S1200) to convert to digital. The Pico can read the RDC's SPI or A/B emulation output, but the resolver itself is not directly readable. Substantially more hardware. |

## Getting the authoritative answer

**McLennan Servo Supplies** (mclennan.co.uk) is the UK distributor for Tamagawa
and handles legacy DC servo enquiries; Tamagawa Seiki's own sales will decode
`TS3727N83E8` plus `SER NO 8Z24` if you send them both. That is the only route
to the real rated voltage, current and torque constant - and the torque
constant is what you need if this ever has to hold a load rather than just
spin at a set speed.
