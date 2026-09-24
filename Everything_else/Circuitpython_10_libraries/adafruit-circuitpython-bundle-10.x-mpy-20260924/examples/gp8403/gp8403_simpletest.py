# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import board

import adafruit_gp8403

i2c = board.I2C()
# default 0-5V range:
dac = adafruit_gp8403.GP8403(i2c)
# for 0-10V range:
# dac = adafruit_gp8403.GP8403(i2c, output_range=adafruit_gp8403.Range.RANGE_10V)

dac.channel_0.voltage = 2.5  # set channel 0 to 2.5V
dac.channel_1.voltage = 3.5  # set channel 0 to 3.5V
while True:
    # can access voltages as a tuple too (dac.voltages):
    print(f"Channel 0: {dac.voltages[0]:.01f}V")
    print(f"Channel 1: {dac.voltages[1]:.01f}V")
    time.sleep(1)
