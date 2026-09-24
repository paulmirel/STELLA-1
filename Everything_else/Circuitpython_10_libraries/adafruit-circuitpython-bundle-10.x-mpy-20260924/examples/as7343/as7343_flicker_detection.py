# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Flicker Detection example for AS7343 14-Channel Multi-Spectral Sensor.

Enables the on-chip flicker detection engine and continuously reports
whether 100 Hz or 120 Hz mains flicker is detected in the ambient light.

Written by Tim Cocks with assistance from Claude Code for Adafruit Industries.
"""

import time

import board

from adafruit_as7343 import AS7343, FlickerFreq

#  Initialise sensor
i2c = board.I2C()

print("AS7343 Flicker Detection Demo")

try:
    sensor = AS7343(i2c)
except RuntimeError as e:
    print(f"AS7343 not found: {e}")
    raise SystemExit

# Enable flicker detection
sensor.flicker_detection_enabled = True
print("Flicker detection enabled")
print("Point sensor at light source...\n")

#  Continuous flicker polling
while True:
    flicker = sensor.flicker_frequency
    raw = sensor.flicker_status

    if flicker == FlickerFreq.HZ100:
        flicker_str = "100Hz"
    elif flicker == FlickerFreq.HZ120:
        flicker_str = "120Hz"
    else:
        flicker_str = "None"

    print(f"Flicker: {flicker_str} (raw status: 0x{raw:02X} {bin(raw)})")

    time.sleep(1.0)
