# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Simple test for the SGP41 sensor"""

import time

import board

from adafruit_sgp41.sgp41 import SGP41

i2c = board.I2C()
sensor = SGP41(i2c)

# set ambient temperature and relative humidity
# for more accurate readings from the sensor
# can be used in conjunction with an external
# temp and humidity sensor
# sensor.temperature = 22.2 # Celsius
# sensor.relative_humidity = 30.9

for i in range(10):
    condition = sensor.conditioning()
    print(f"Conditioning the sensor, {(i + 1)} of 10 times: {condition}")
    time.sleep(1)

print("Sensor ready! Starting the loop..")
print()

while True:
    print(f"Raw VOC: {sensor.raw_voc}")
    print(f"Raw NOx: {sensor.raw_nox}")
    print()
    time.sleep(1)
