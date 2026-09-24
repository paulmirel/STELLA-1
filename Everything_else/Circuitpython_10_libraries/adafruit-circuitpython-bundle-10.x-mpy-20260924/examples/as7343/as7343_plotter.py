# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Serial Plotter example for AS7343 14-Channel Multi-Spectral Sensor.

Outputs spectral data in a CSV format suitable for CircuitPython
web-editor plotter. Channels are ordered by wavelength:
violet → blue → green → yellow → orange → red → NIR

# Plotter data index reference:
# 0: F1  (405nm)  | 1: F2  (425nm) - Violet/UV
# 2: FZ  (450nm)  | 3: F3  (475nm) - Blue
# 4: F4  (515nm)  | 5: F5  (550nm)  | 6: FY (555nm) - Green
# 7: FXL (600nm) - Yellow/Orange
# 8: F6  (640nm)  | 9: F7  (690nm) - Red
# 10: F8 (745nm)  | 11: NIR (855nm) - Near-IR
# 12: VIS_TL_0 (Clear/broadband)

Written by Tim Cocks with assistance from Claude Code for Adafruit Industries.
"""

import time

import board

from adafruit_as7343 import AS7343, Channel, Gain, SmuxMode

# Initialise sensor
i2c = board.I2C()

try:
    sensor = AS7343(i2c)
except RuntimeError as e:
    print(f"AS7343 not found: {e}")
    raise SystemExit

sensor.gain = Gain.X64
sensor.atime = 29
sensor.astep = 599
sensor.smux_mode = SmuxMode.CH18

# Continuous plotter output
while True:
    try:
        readings = sensor.all_channels
    except TimeoutError:
        time.sleep(0.5)
        continue

    # Output in wavelength order for spectrum visualisation.
    print(f"{readings[Channel.F1]}", end=",")
    print(f"{readings[Channel.F2]}", end=",")

    # Blue (450–475 nm)
    print(f"{readings[Channel.FZ]}", end=",")
    print(f"{readings[Channel.F3]}", end=",")

    # Green (515–555 nm)
    print(f"{readings[Channel.F4]}", end=",")
    print(f"{readings[Channel.F5]}", end=",")
    print(f"{readings[Channel.FY]}", end=",")

    # Yellow/Orange (600 nm)
    print(f"{readings[Channel.FXL]}", end=",")

    # Red (640–690 nm)
    print(f"{readings[Channel.F6]}", end=",")
    print(f"{readings[Channel.F7]}", end=",")

    # Near-IR (745–855 nm)
    print(f"{readings[Channel.F8]}", end=",")
    print(f"{readings[Channel.NIR]}", end=",")

    # Clear/broadband
    print(f"{readings[Channel.VIS_TL_0]}")

    time.sleep(1.0)
