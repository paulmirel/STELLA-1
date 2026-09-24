# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Print three channel measurements from the TSL2585."""

import time

import board

import adafruit_tsl2585

i2c = board.I2C()
sensor = adafruit_tsl2585.TSL2585(i2c)

print(f"Found TSL2585, revision {sensor.revision_id}")

while True:
    if sensor.data_ready:
        data = sensor.measurement
        print(f"Photopic: {data.photopic}, IR: {data.infrared}, UVA: {data.uva}")
        if data.photopic_saturated or data.infrared_saturated or data.uva_saturated:
            print("Warning: at least one channel saturated")
        print()
    time.sleep(0.5)
