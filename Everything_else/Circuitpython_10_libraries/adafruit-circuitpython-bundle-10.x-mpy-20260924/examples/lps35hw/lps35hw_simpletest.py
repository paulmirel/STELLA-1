# SPDX-FileCopyrightText: 2019 Bryan Siepert, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time

import board

import adafruit_lps35hw

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
lps = adafruit_lps35hw.LPS35HW(i2c)

while True:
    print(f"Pressure: {lps.pressure:.2f} hPa")
    print(f"Temperature: {lps.temperature:.2f} C")
    print("")
    time.sleep(1)
