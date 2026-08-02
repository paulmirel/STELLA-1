# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import board

import adafruit_as7331

i2c = board.I2C()
sensor = adafruit_as7331.AS7331(i2c)

# Optional: configure gain and integration time
# sensor.gain = adafruit_as7331.GAIN_256X
# sensor.integration_time = adafruit_as7331.TIME_64MS

while True:
    uva, uvb, uvc = sensor.one_shot()
    print(f"UVA: {uva:.2f}  UVB: {uvb:.2f}  UVC: {uvc:.2f}  µW/cm²")
    print(f"Temperature: {sensor.temperature:.1f} °C")
    print()
    time.sleep(1)
