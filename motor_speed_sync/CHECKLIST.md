# What is still unknown, and how to find each answer

Four gaps remain. Three you can close yourself at a bench; one needs
Tamagawa. Work top to bottom - each step depends on the one above it.

**Tools:** multimeter, a current-limited bench power supply (or any 12 V
supply with a fuse), your logic analyser, masking tape, phone camera.

---

## Step 1 - Which feedback device is on the back of the motor

The single most important unknown: it decides whether the code in this repo
applies at all. Do not skip to wiring before this is settled.

### 1a. Photograph the rear housing

The feedback device carries its own nameplate, separate from the motor's.
Prefix guide:

| prefix on the rear plate | device |
|---|---|
| `TS20xx`, `TS26xx`, `TS56xx`, "Smartsyn", "BRX", "BRT" | resolver |
| `TS51xx`, `TS52xx`, `OIH`, `OME`, "FA-CODER" | incremental encoder |
| no separate plate, only two terminals | tachogenerator |

If there is a plate, this step alone answers Step 1 and you can go to Step 2.

### 1b. Count the wires and write down the colours

| wires | most likely |
|---|---|
| 2 | tachogenerator |
| 4 | resolver, or a bare A/B encoder |
| 5-6 | incremental encoder, single-ended (Vcc, GND, A, B, Z) |
| 6-7 | resolver (R1 R2 excitation, S1 S3, S2 S4) |
| 8-10 | incremental encoder, differential (A /A B /B Z /Z Vcc GND) |

### 1c. Ohmmeter, motor unpowered and disconnected from everything

Probe every pair of feedback pins and note the readings.

- **Every pair reads 10-200 Ω** -> resolver. Windings are continuous copper.
- **Signal pins read open circuit** (only Vcc-GND shows anything) -> encoder.
  Its outputs are transistors, not coils.
- **One pair reads a few ohms, nothing else exists** -> tachogenerator.

### 1d. The decisive test: spin the shaft by hand

Multimeter on **DC volts**, across the pair you suspect, feedback device
unpowered. Turn the shaft steadily by hand.

- **A voltage appears, grows with speed, and flips sign when you reverse
  direction** -> **tachogenerator**. Typically 3-10 V per 1000 rpm.
- **Nothing at all, in any pairing** -> encoder or resolver (both need
  power/excitation). 1c already told you which.

Write the answer down. Everything below branches on it.

---

## Step 2 - Encoder details (only if Step 1 said "incremental encoder")

### 2a. Supply voltage

Read it off the plate. If there is no plate, try 5 V first - almost all
industrial encoders accept 5 V, many accept 5-24 V. Current draw should be
well under 100 mA.

### 2b. Output voltage - do this before touching the Pico

With the encoder powered and the shaft parked, measure DC volts from each
signal pin to encoder GND, then turn the shaft slightly and measure again.
The higher of the two readings is the output high level.

- **3.3 V** -> connect straight to the Pico.
- **5 V** -> level shift. The Pico is **not 5 V tolerant**; the 10k/15k
  divider in `WIRING.md` is the cheap correct fix.
- **Reads ~0 V in both positions** -> open-collector output. Add a 2.2k-10k
  pull-up to **3.3 V** and measure again.
- **12 V or 24 V** -> divider mandatory, and recheck under load.

### 2c. Pulses per revolution

Put a strip of masking tape on the shaft as a reference mark. Analyser on
channel A and channel B, sampling at 1 MS/s, capture while you turn the shaft
by hand through **exactly one revolution**, slowly.

- Count the rising edges on channel A. That number is `ENC_PPR`.
- Check A and B are offset by a quarter period, not aligned and not inverted.
  If they are aligned, one of them is not what you think it is.
- Reverse the direction and confirm the lead/lag swaps.

Alternative with no analyser, once wired to the Pico:

```python
>>> from encoder import QuadratureEncoder
>>> e = QuadratureEncoder(2, 3, mode=4)
>>> e.reset()          # now turn the shaft exactly one revolution
>>> e.read()           # this value / 4 = ENC_PPR
```

### 2d. Encoder before or after the gearbox

If the motor has no gearbox, `GEAR_RATIO = 1.0`. If it has one and the
encoder is bolted to the motor's rear shaft (the usual arrangement), the
gearbox ratio goes in `GEAR_RATIO` and rpm is then reported at the output
shaft.

### 2e. Fill in `config.py`

```python
ENC_PPR      = <from 2c>
GEAR_RATIO   = <from 2d, or 1.0>
DECODE_MODE  = 4
ENC_A_PINS   = (<your GPIO>, <your GPIO>)
ENC_B_PINS   = (<your GPIO>, <your GPIO>)
```

**If Step 1 said tachogenerator instead:** there are no pulses and the logic
analyser cannot help - it is an analog signal needing an oscilloscope. What
you need instead is the tacho constant in V/1000 rpm (from the plate, or
calibrate it against a hand tachometer or a strobe). `speed.py` gets replaced
by an `machine.ADC` read through a divider; the PI and cross-coupling in
`sync_two_motors.py` stay exactly as they are. Tell me and I will write it.

**If Step 1 said resolver:** the Pico cannot read it directly. You need an
AD2S1210 or AD2S1200 resolver-to-digital converter, which generates the
~7 kHz excitation and gives you either SPI position or emulated A/B pulses.
With A/B emulation selected, this repo then works unchanged.

---

## Step 3 - The motor's electrical rating

### 3a. Armature resistance

Multimeter on the lowest ohms range, across the two power terminals, motor
disconnected. Turn the shaft a little and measure again, several times - the
brushes make the reading vary with position. Take the average; expect a few
ohms.

### 3b. Stall current, and therefore the driver you need

```
stall current = supply voltage / armature resistance
```

This is the number the H-bridge must survive, not the running current. At
12 V into 2 Ω that is already 6 A - beyond a TB6612 or L298N. Size the driver
for the stall figure, and pick from `WIRING.md`.

### 3c. Safe first power-up

Current-limited bench supply, limit set to roughly the expected no-load
current (a few hundred mA), starting at **12 V, not the rated voltage**. The
motor will turn slowly. You do not need its rated voltage to develop or tune
the speed loop - do all of the software work at 12 V and raise it later only
if the application needs the torque.

Record at 12 V: no-load current, and no-load rpm (from the encoder, once
Step 2 is done). Those two numbers let you sanity-check everything else.

---

## Step 4 - The second motor

Everything above assumes two motors. Confirm and note:

- Is the second one the same type, or a different motor?
- Does it have the same feedback device? If one has an encoder and the other
  a tacho, the two speed measurements must be made comparable before they can
  be synchronised.
- Are both mechanically free, or are they coupled to a load that will fight
  the sync loop (a belt, a shared axle)?

If you only have one motor right now, `measure_speed.py` still works - it just
reports zero for the missing channel - and `sync_two_motors.py` waits until
the second arrives.

---

## Step 5 - Questions only you can answer

1. What is this driving? Two robot wheels, a conveyor, a test rig?
2. Fixed target rpm, or should motor 1 follow whatever motor 0 does?
3. Speed-matched only, or **position-locked** - must they still be in step
   after ten minutes of running? (This sets `KSYNC`; for anything driving in
   a straight line, the answer is yes.)
4. Working speed range, and how quickly it must reach the setpoint.
5. Which Pico GPIOs you have actually wired.

---

## Step 6 - The one thing you cannot measure

The rated voltage, rated current and torque constant of `TS3727N83E8`.
Tamagawa never published a decode for the `N83E8` suffix. Email
**McLennan Servo Supplies** (mclennan.co.uk, the UK distributor for legacy
Tamagawa DC servos) or Tamagawa Seiki directly, quoting:

```
Type:  TS3727N83E8
Ser:   8Z24
```

and ask for the datasheet or the rating plate values. You can complete Steps
1-5 and have working synchronised motors without this - you need it only to
run the motor at its real rating, or to size torque for a load.

---

## Order of operations, condensed

1. Identify the feedback device (Step 1) - photo, wire count, ohmmeter,
   hand-spin.
2. If encoder: supply voltage, output voltage, PPR (Step 2). Fill in
   `config.py`.
3. Armature resistance -> stall current -> pick the driver (Step 3).
4. Wire it per `WIRING.md`, then follow the bring-up order at the bottom of
   that file: encoder direction first, motor direction second, closed loop
   last.
5. `measure_speed.run()` for the duty/rpm curve and suggested gains.
6. `sync_two_motors.run(target_rpm=..., seconds=...)` and tune `KSYNC`.

Send me the answers from Steps 1, 2 and 5 and I will fill in `config.py` and
adapt the code to whatever the feedback device turns out to be.
