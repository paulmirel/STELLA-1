# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Print a message whenever something is plugged into or unplugged from the jack.

Pin names are the Teenage Engineering SP-1's, the only board this driver has
been run on. The SP-1 holds the codec RESET line low at the start of every VM
run, and a codec in reset does not ACK, so the pin goes to the driver as
``reset_pin``: ``__init__`` pulses it before it touches the bus. No clocks are
set up here. Tip sense runs off the codec's internal oscillator, so detection
works without an audio path.
"""

import time

import board
import digitalio

import adafruit_cs42l42

reset = digitalio.DigitalInOut(board.CS42_RESET)
reset.direction = digitalio.Direction.OUTPUT
reset.value = False  # active low: the driver releases it

codec = adafruit_cs42l42.CS42L42(board.I2C(), reset_pin=reset)

# 200 ms is the shortest debounce worth using on a jack.
codec.enable_tip_sense(debounce_ms=200)

plugged = None

while True:
    if codec.headphone_detected != plugged:
        plugged = codec.headphone_detected
        print("headphones", "in" if plugged else "out")
    time.sleep(0.1)
