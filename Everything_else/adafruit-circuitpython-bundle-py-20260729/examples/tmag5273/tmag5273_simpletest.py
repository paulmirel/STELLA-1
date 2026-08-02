# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import board

import adafruit_tmag5273

i2c = board.I2C()
sensor = adafruit_tmag5273.TMAG5273(i2c)

while True:
    mag_x, mag_y, mag_z = sensor.magnetic
    temp = sensor.temperature
    print(f"X: {mag_x:.2f} uT  Y: {mag_y:.2f} uT  Z: {mag_z:.2f} uT  Temp: {temp:.1f} °C")
    time.sleep(1)
