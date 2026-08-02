# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Adafruit VCNL4030 Simple Test

Basic example for the Adafruit VCNL4030 library.
Reads proximity, ambient light, and white channel values.
"""

import time

import board

from adafruit_vcnl4030 import VCNL4030

print("Adafruit VCNL4030 Simple Test")

sensor = VCNL4030(board.I2C())

print("VCNL4030 Found!")
print()

while True:
    print(f"Proximity: {sensor.proximity}  Lux: {sensor.lux:.2f}  White: {sensor.white}")
    time.sleep(1.0)
