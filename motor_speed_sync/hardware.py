"""Builds the encoders, speed estimators and motors described in config.py."""

import config
from encoder import QuadratureEncoder
from motor import Motor
from speed import SpeedEstimator
from machine import Pin


def build():
    if config.STANDBY_PIN is not None:
        Pin(config.STANDBY_PIN, Pin.OUT, value=1)   # TB6612 STBY = run

    encoders, speeds, motors = [], [], []
    for i in range(2):
        la = None
        if config.LA_REV_PINS and config.LA_REV_PINS[i] is not None:
            la = config.LA_REV_PINS[i]
        enc = QuadratureEncoder(
            config.ENC_A_PINS[i], config.ENC_B_PINS[i],
            mode=config.DECODE_MODE,
            invert=config.ENC_INVERT[i],
            counts_per_rev=config.CPR_OUTPUT,
            la_pin=la,
        )
        encoders.append(enc)
        speeds.append(SpeedEstimator(enc, config.CPR_OUTPUT, config.SPEED_FILTER))
        motors.append(Motor(
            config.MOTOR_PINS[i],
            driver=config.DRIVER,
            freq=config.PWM_FREQ_HZ,
            invert=config.MOTOR_INVERT[i],
            min_duty=config.MIN_DUTY,
            max_duty=config.MAX_DUTY,
        ))
    return encoders, speeds, motors


def loop_probe():
    """GPIO that is high while the control loop body runs (for the analyser)."""
    if config.LA_LOOP_PIN is None:
        return None
    return Pin(config.LA_LOOP_PIN, Pin.OUT, value=0)
