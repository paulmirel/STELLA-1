# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
VCNL4030 Proximity Interrupt Example

Automatically calibrates a threshold from ambient readings,
then uses the INT pin to detect when a hand is nearby.

Connect VCNL4030 INT pin to D8.
"""

import time

import board
from digitalio import DigitalInOut, Direction, Pull

from adafruit_vcnl4030 import (
    VCNL4030,
    VCNL4030_PROX_IF_AWAY,
    VCNL4030_PROX_IF_CLOSE,
    ProxInterruptMode,
    ProxPersistence,
)

INT_PIN = board.D8

print("VCNL4030 Proximity Interrupt Example")
print("====================================")

int_pin = DigitalInOut(INT_PIN)
int_pin.direction = Direction.INPUT
int_pin.pull = Pull.UP

sensor = VCNL4030(board.I2C())
print("VCNL4030 Found!")

# Calibrate: sample ambient proximity with nothing nearby
print("\nCalibrating... keep sensor clear")
time.sleep(0.5)

total = 0
for _ in range(10):
    total += sensor.proximity
    time.sleep(0.05)
ambient = total // 10
threshold = max(ambient * 2, 50)

print(f"Ambient: {ambient}  Threshold: {threshold}")

# Set up proximity interrupt for close/away detection.
# IMPORTANT: Interrupts fire on TRANSITIONS. The sensor must be below
# the low threshold (far state) before it can trigger CLOSE by crossing
# above the high threshold. Set low threshold above ambient so the
# sensor starts in the "far" state.
low_threshold = (ambient + threshold) // 2  # midpoint
sensor.proximity_threshold_low = low_threshold
sensor.proximity_threshold_high = threshold
print(f"Low threshold: {low_threshold}")
sensor.proximity_persistence = ProxPersistence.CYCLES_1
sensor.proximity_interrupt_mode = ProxInterruptMode.BOTH

# Clear any pending flags
sensor.interrupt_flags

print("\nReady! Wave your hand near the sensor.")
print()

while True:
    prox = sensor.proximity
    out = f"Prox: {prox}"

    if not int_pin.value:  # INT pin pulled LOW = interrupt fired
        flags = sensor.interrupt_flags  # read and clear
        if flags & VCNL4030_PROX_IF_CLOSE:
            out += "  *** IRQ CLOSE ***"
        if flags & VCNL4030_PROX_IF_AWAY:
            out += "  *** IRQ AWAY ***"

    print(out)
    time.sleep(0.1)
