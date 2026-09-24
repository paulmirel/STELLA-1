# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Adafruit MAX44009 Simple Test

Basic example for the Adafruit MAX44009 library.
Reads ambient light lux values.
"""

import time

import board

from adafruit_max44009 import MAX44009

print("Adafruit MAX44009 Simple Test")

sensor = MAX44009(board.I2C())

print("MAX44009 Found!")
print()

while True:
    print(f"Lux: {sensor.lux:.2f}")
    time.sleep(1.0)
