# SPDX-FileCopyrightText: 2020 Bryan Siepert, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time

import board

import adafruit_tmp117

# First try the STEMMA_I2C on Feathers and QtPy among others
if hasattr(board, "STEMMA_I2C"):
    i2c = board.STEMMA_I2C()
else:
    i2c = board.I2C()  # uses board.SCL and board.SDA

tmp117 = adafruit_tmp117.TMP117(i2c)

print(f"Temperature without offset: {tmp117.temperature:.2f} degrees C")
tmp117.temperature_offset = 10.0
time.sleep(0.5)  # Let settle
while True:
    print(f"Temperature w/ offset: {tmp117.temperature:.2f} degrees C")
    time.sleep(1)
