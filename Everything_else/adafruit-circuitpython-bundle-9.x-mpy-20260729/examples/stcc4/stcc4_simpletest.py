# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import board

import adafruit_stcc4

i2c = board.I2C()
sensor = adafruit_stcc4.STCC4(i2c)
print("Starting continuous measurement...")
sensor.continuous_measurement = True

while True:
    co2 = sensor.CO2
    print(
        f"CO2: {co2} ppm | "
        f"Temperature: {sensor.temperature:.1f} °C | "
        f"Humidity: {sensor.relative_humidity:.1f} %"
    )
    time.sleep(1)
