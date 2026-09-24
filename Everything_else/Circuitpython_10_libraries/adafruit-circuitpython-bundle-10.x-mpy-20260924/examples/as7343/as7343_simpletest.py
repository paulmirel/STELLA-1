# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import time

import board

from adafruit_as7343 import AS7343

i2c = board.I2C()
sensor = AS7343(i2c)

CHANNEL_LABELS = [
    "FZ (450nm blue)",
    "FY (555nm yellow-green)",
    "FXL (600nm orange)",
    "NIR (855nm near-IR)",
    "VIS_TL_0 (clear top-left, cycle 1)",
    "VIS_BR_0 (clear btm-right, cycle 1)",
    "F2 (425nm violet-blue)",
    "F3 (475nm blue-cyan)",
    "F4 (515nm green)",
    "F6 (640nm red)",
    "VIS_TL_1 (clear top-left, cycle 2)",
    "VIS_BR_1 (clear btm-right, cycle 2)",
    "F1 (405nm violet)",
    "F7 (690nm deep red)",
    "F8 (745nm near-IR edge)",
    "F5 (550nm green-yellow)",
    "VIS_TL_2 (clear top-left, cycle 3)",
    "VIS_BR_2 (clear btm-right, cycle 3)",
]

while True:
    readings = sensor.all_channels
    print("--- AS7343 Channel Readings ---")
    for label, value in zip(CHANNEL_LABELS, readings):
        print(f"  {label}: {value}")
    print()
    time.sleep(1)
