# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT

"""Basic test for TCS3430 XYZ Tristimulus Color Sensor."""

import time

import board

from adafruit_tcs3430 import TCS3430, ALSGain, InterruptPersistence

i2c = board.I2C()
tcs = TCS3430(i2c)

print("TCS3430 Basic Test")
print("TCS3430 found!")

# --- Tweak these settings for your environment ---
tcs.als_gain = ALSGain.GAIN_64X  # 1X, 4X, 16X, 64X, or 128X
tcs.integration_time = 100.0  # 2.78ms to 711ms

while True:
    x, y, z, ir1 = tcs.channels
    print(f"X: {x}  Y: {y}  Z: {z}  IR1: {ir1}")

    time.sleep(1.0)
