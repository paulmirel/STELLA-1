# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

from time import sleep

import board
from analogio import AnalogIn

import adafruit_ds3502

####### NOTE ################
# this example will not work with Blinka/rasberry Pi due to the lack of analog pins.
# Blinka and Raspberry Pi users should run the "ds3502_blinka_simpletest.py" example

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
ds3502 = adafruit_ds3502.DS3502(i2c)
wiper_output = AnalogIn(board.A0)

while True:
    ds3502.wiper = 127
    print(f"Wiper set to {ds3502.wiper:d}")
    voltage = wiper_output.value
    voltage *= 3.3
    voltage /= 65535
    print(f"Wiper voltage: {voltage:.2f} V")
    print("")
    sleep(1.0)

    ds3502.wiper = 0
    print(f"Wiper set to {ds3502.wiper:d}")
    voltage = wiper_output.value
    voltage *= 3.3
    voltage /= 65535
    print(f"Wiper voltage: {voltage:.2f} V")
    print("")
    sleep(1.0)

    ds3502.wiper = 63
    print(f"Wiper set to {ds3502.wiper:d}")
    voltage = wiper_output.value
    voltage *= 3.3
    voltage /= 65535
    print(f"Wiper voltage: {voltage:.2f} V")
    print("")
    sleep(1.0)
