# SPDX-FileCopyrightText: 2020 Bryan Siepert, written for Adafruit Industries
# SPDX-License-Identifier: MIT
from time import sleep

import board

from adafruit_ms8607 import MS8607

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
sensor = MS8607(i2c)

while True:
    print(f"Pressure: {sensor.pressure:.2f} hPa")
    print(f"Temperature: {sensor.temperature:.2f} C")
    print(f"Humidity: {sensor.relative_humidity:.2f} rH")
    print("\n------------------------------------------------\n")
    sleep(1)
