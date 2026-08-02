# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Print the VOC and NOx index from the SGP41 once per second.

The Sensirion gas index algorithm expects a 1 Hz sampling rate. Both
indices will be 0 during the first ~45 s warm-up and then settle in the range
1..500 (VOC baseline 100, NOx baseline 1). Pair with a BME280 (or similar) for
humidity-compensated readings; otherwise the default 25 C / 50 %RH is used.
"""

import time

import board

from adafruit_sgp41.sgp41 import SGP41

i2c = board.I2C()  # uses board.SCL and board.SDA
sensor = SGP41(i2c)

# Optional: use an external temp/humidity sensor for more accurate compensation
# import adafruit_bme280.basic as adafruit_bme280
# bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

for i in range(10):
    condition = sensor.conditioning()
    print(f"Conditioning the sensor, {(i + 1)} of 10 times: {condition}")
    time.sleep(1)

print("Sensor ready! Starting the loop..")
print()

while True:
    # temperature = bme280.temperature
    # humidity = bme280.relative_humidity
    # voc_index, nox_index = sensor.measure_index(humidity=humidity, temperature=temperature)
    voc_index, nox_index = sensor.measure_index()
    print(f"VOC Index: {voc_index}\tNOx Index: {nox_index}")
    time.sleep(1)
