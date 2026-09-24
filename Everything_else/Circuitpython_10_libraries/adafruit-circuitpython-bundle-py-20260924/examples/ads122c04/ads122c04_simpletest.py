# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import board

from adafruit_ads122c04.ads122c04 import ADS122C04, VREF_EXTERNAL
from adafruit_ads122c04.analog_in import AnalogIn

i2c = board.I2C()
adc = ADS122C04(i2c)

chan0 = AnalogIn(adc, 0)
chan1 = AnalogIn(adc, 1)
chan2 = AnalogIn(adc, 2)
chan3 = AnalogIn(adc, 3)

channels = (chan0, chan1, chan2, chan3)

adc.vref_input = VREF_EXTERNAL
adc.reference_voltage = 3.3

while True:
    for i, chan in enumerate(channels):
        print(f"A{i}: {chan.value:5d}  ({chan.voltage:.4f} V)")
    print("-" * 30)
    time.sleep(1)
