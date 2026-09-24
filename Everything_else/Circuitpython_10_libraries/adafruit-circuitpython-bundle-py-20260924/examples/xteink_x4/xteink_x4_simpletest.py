# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Xteink X4 Helper Demo

Uses button inputs and battery monitor
"""

from adafruit_xteink_x4 import BatteryMonitor, InputManager

battery = BatteryMonitor()
buttons = InputManager()

print(f"Battery: {battery.percentage}% ({battery.volts:.2f}V)")
print()

while True:
    buttons.update()

    if buttons.any_pressed:
        for i in range(7):
            if buttons.was_pressed(i):
                print(f"Pressed:  {buttons.button_name(i)}")

    if buttons.any_released:
        for i in range(7):
            if buttons.was_released(i):
                held = buttons.held_time
                print(f"Released: {buttons.button_name(i)} (held {held:.2f}s)")
                print(f"Battery: {battery.percentage}% ({battery.volts:.2f}V)")
