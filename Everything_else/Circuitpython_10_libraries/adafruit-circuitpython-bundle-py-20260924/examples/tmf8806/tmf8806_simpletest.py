# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board

from adafruit_tmf8806 import tmf8806

i2c = board.I2C()
sensor = tmf8806.TMF8806(i2c)

print(f"Firmware version: {'.'.join(str(part) for part in sensor.firmware_version)}")
print(f"Serial number: {sensor.serial_number:#06x}")

sensor.start_measuring()
while True:
    if sensor.data_ready:
        distance = sensor.distance
        if distance is not None:
            print(f"Distance: {distance} mm")
