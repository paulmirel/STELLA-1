# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time

import board

import adafruit_lps2x

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
# uncomment and comment out the line after to use with the LPS22
# lps = adafruit_lps2x.LPS22(i2c)
lps = adafruit_lps2x.LPS25(i2c)

while True:
    print(f"Pressure: {lps.pressure:.2f} hPa")
    print(f"Temperature: {lps.temperature:.2f} C")
    time.sleep(1)
