"""
Central configuration - EDIT THIS FILE ONLY.

Every number here is something you must fill in from your own hardware
datasheet / measurement. Everything else in this project reads from here.
"""

# ---------------------------------------------------------------- encoders --
# GPIO numbers (not physical pin numbers) on the Raspberry Pi Pico.
ENC_A_PINS = (2, 4)      # channel A of motor 0, channel A of motor 1
ENC_B_PINS = (3, 5)      # channel B of motor 0, channel B of motor 1

# Encoder pulses per revolution, per channel, BEFORE the gearbox,
# as printed in the motor datasheet (e.g. 11 for a typical hall encoder,
# 500 for an optical one).
ENC_PPR = 11

# Gearbox reduction. 1.0 if the encoder sits on the output shaft.
GEAR_RATIO = 30.0

# Decoding mode: 4 = count both edges of both channels (x4, best resolution)
#                2 = both edges of channel A only
#                1 = rising edges of channel A only (no direction from encoder)
DECODE_MODE = 4

# Counts per revolution of the OUTPUT shaft. Derived - do not edit.
CPR_OUTPUT = ENC_PPR * DECODE_MODE * GEAR_RATIO

# Flip if a motor reports negative speed while driving forward.
ENC_INVERT = (False, False)

# ----------------------------------------------------------------- motors ---
# Driver style:
#   "pwm_dir"  -> one PWM pin + two direction pins (TB6612FNG, L298N)
#   "two_pwm"  -> two PWM pins, no separate direction pin (DRV8833, TB6612 in
#                 locked-antiphase-free mode, most cheap dual H-bridges)
DRIVER = "pwm_dir"

# For "pwm_dir": (PWM, IN1, IN2) per motor.
# For "two_pwm": (IN1, IN2) per motor - the third entry is ignored.
MOTOR_PINS = (
    (6, 7, 8),      # motor 0
    (9, 10, 11),    # motor 1
)

# Optional shared enable / standby pin (TB6612 STBY). None if unused.
STANDBY_PIN = None

PWM_FREQ_HZ = 20_000     # 20 kHz = above audible range, fine for most drivers
MIN_DUTY = 0.06          # below this the motor just buzzes; deadband compensation
MAX_DUTY = 1.0

# Flip if a motor spins backwards when commanded forwards.
MOTOR_INVERT = (False, False)

# ------------------------------------------------------------ control loop --
LOOP_HZ = 100            # control/sample rate; 50-200 Hz is sensible
SPEED_FILTER = 0.25      # 0..1 low-pass on measured rpm (1 = no filtering)

# Per-motor velocity PI gains. Units: duty per rpm.
KP = 0.0018
KI = 0.0090             # per second
KFF = 0.0               # feed-forward duty per rpm; set from the calibration run

# Cross-coupling gain: pulls the two motors back into step by comparing the
# accumulated revolutions of each. Units: duty per revolution of mismatch.
KSYNC = 0.30

INTEGRAL_LIMIT = 0.8     # anti-windup clamp on the integral term (duty)

# ---------------------------------------------------- logic analyser probes --
# GPIOs toggled purely so a logic analyser can see what the firmware is doing.
# Set any of them to None to disable.
LA_LOOP_PIN = 15         # goes high for the duration of each control tick
LA_REV_PINS = (14, 13)   # one short pulse per output-shaft revolution, per motor
LA_REV_PULSE_US = 50
