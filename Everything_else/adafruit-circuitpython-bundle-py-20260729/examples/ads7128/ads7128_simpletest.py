# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Simple analog read example for the ADS7128.

Reads a single channel and prints the 16-bit value and the voltage.
"""

import time

import board

from adafruit_ads7128.ads7128 import ADS7128
from adafruit_ads7128.analog_in import AnalogIn

# Reference voltage
REFERENCE_VOLTAGE = 3.3

i2c = board.I2C()
adc = ADS7128(i2c)

# analog input on channel 0
channel = AnalogIn(adc, 0)

while True:
    print(f"value: {channel.value}  voltage: {channel.voltage(REFERENCE_VOLTAGE):.3f} V")
    time.sleep(1.0)
