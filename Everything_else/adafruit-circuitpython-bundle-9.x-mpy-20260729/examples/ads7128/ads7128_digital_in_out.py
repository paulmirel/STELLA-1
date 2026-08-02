# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Digital I/O example for the ADS7128: a button controls an LED.

Wiring:
  * Channel 0 -> a button (digital input)
  * Channel 1 -> an LED (digital output)

The ADS7128 has no internal pull resistors, so the button needs an external
one. This example assumes an external pull-UP resistor on the button, so the
input reads ``False`` (low) while the button is pressed and ``True`` when it
is released.
"""

import time

import board

from adafruit_ads7128.ads7128 import ADS7128
from adafruit_ads7128.digital_inout import DigitalInOut

BUTTON_PIN = 0
LED_PIN = 1

i2c = board.I2C()
adc = ADS7128(i2c)

# Channel 0 as a digital input. pull must be None; the ADS7128 has no
# internal pull resistors, so use an external pull-down on the button.
button = DigitalInOut(adc, BUTTON_PIN)
button.switch_to_input()

# Channel 1 as a digital output, starting low (LED off).
led = DigitalInOut(adc, LED_PIN)
led.switch_to_output(value=False)

while True:
    if not button.value:
        led.value = True  # LED on while the button is pressed
    else:
        led.value = False
    time.sleep(0.01)
