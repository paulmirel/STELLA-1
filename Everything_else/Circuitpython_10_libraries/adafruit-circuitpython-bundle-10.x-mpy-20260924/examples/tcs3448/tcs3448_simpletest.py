# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import time

import board

from adafruit_tcs3448 import TCS3448

i2c = board.I2C()
sensor = TCS3448(i2c)

CHANNEL_LABELS = [
    "FZ (450nm blue)",
    "FY (560nm yellow-green)",
    "FXL (596nm orange)",
    "NIR (855nm near-IR)",
    "VIS_TL_0 (clear top-left, cycle 1)",
    "VIS_BR_0 (clear btm-right, cycle 1)",
    "F2 (424nm violet-blue)",
    "F3 (473nm blue-cyan)",
    "F4 (516nm green)",
    "F6 (636nm red)",
    "VIS_TL_1 (clear top-left, cycle 2)",
    "VIS_BR_1 (clear btm-right, cycle 2)",
    "F1 (407nm violet)",
    "F7 (687nm deep red)",
    "F8 (748nm near-IR edge)",
    "F5 (546nm green-yellow)",
    "VIS_TL_2 (clear top-left, cycle 3)",
    "VIS_BR_2 (clear btm-right, cycle 3)",
]

while True:
    readings = sensor.all_channels
    print("--- TCS3448 Channel Readings ---")
    for label, value in zip(CHANNEL_LABELS, readings):
        print(f"  {label}: {value}")
    print()
    time.sleep(1)
