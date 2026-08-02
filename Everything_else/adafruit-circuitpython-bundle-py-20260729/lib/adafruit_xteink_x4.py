# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_xteink_x4`
================================================================================

CircuitPython helper library to interface with the Xteink X4 eReader


* Author(s): Liz Clark

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Based on the OpenX4 E-Paper Community SDK:
  https://github.com/open-x4-epaper/community-sdk

"""

import time

import board
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction, Pull

__version__ = "1.0.2"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Xteink_X4.git"


class BatteryMonitor:
    """Monitor battery voltage and percentage via an ADC pin with a
    voltage divider.

    :param ~microcontroller.Pin adc_pin: The ADC pin connected to the
        battery voltage divider. Defaults to ``board.A0``.
    :param float divider_multiplier: The voltage divider multiplier.
        Defaults to ``2.0``.
    """

    def __init__(self, adc_pin=None, divider_multiplier=2.0):
        if adc_pin is None:
            adc_pin = board.A0
        self._adc = AnalogIn(adc_pin)
        self._divider_multiplier = divider_multiplier

    def deinit(self):
        """Release the underlying ADC resource."""
        self._adc.deinit()

    @property
    def millivolts(self):
        """Battery voltage in millivolts, accounting for the voltage divider."""
        raw = self._adc.value
        ref = self._adc.reference_voltage
        mv = (raw / 65535) * ref * 1000
        return int(mv * self._divider_multiplier)

    @property
    def volts(self):
        """Battery voltage in volts."""
        return self.millivolts / 1000.0

    @property
    def percentage(self):
        """Estimated battery percentage (0-100) using a cubic fit curve
        for a typical Li-Ion discharge profile."""
        v = self.millivolts / 1000.0
        y = -144.9390 * v * v * v + 1655.8629 * v * v - 6158.8520 * v + 7501.3202
        return int(max(0.0, min(100.0, round(y))))


class InputManager:
    """Manage button input from two ADC channels and a digital power button.

    Buttons are read from two ADC pins using resistor-ladder thresholds
    and a dedicated digital pin for the power button. Call :meth:`update`
    once per main-loop iteration to poll and debounce.

    :param ~microcontroller.Pin adc_pin_1: First ADC pin
        (Back, Confirm, Left, Right). Defaults to ``board.BUTTON_ADC_1``.
    :param ~microcontroller.Pin adc_pin_2: Second ADC pin
        (Up, Down). Defaults to ``board.BUTTON_ADC_2``.
    :param ~microcontroller.Pin power_pin: Digital pin for the power button
        (active-low). Defaults to ``board.BUTTON``.
    :param float debounce: Debounce delay in seconds.
        Defaults to ``0.05`` (50 ms).
    """

    # Button indices
    BTN_BACK = 0
    BTN_CONFIRM = 1
    BTN_LEFT = 2
    BTN_RIGHT = 3
    BTN_UP = 4
    BTN_DOWN = 5
    BTN_POWER = 6

    _BUTTON_NAMES = ("Back", "Confirm", "Left", "Right", "Up", "Down", "Power")

    # Raw 16-bit ADC thresholds (0-65535).
    # Calibrated from hardware:
    #   ADC1: idle ~58107, Back ~50972, Confirm ~39531, Left ~22083, Right ~63
    #   ADC2: idle ~58107, Up ~32985, Down ~61
    _ADC_RANGES_1 = (54000, 45000, 30000, 11000, -1)
    _ADC_RANGES_2 = (45000, 16000, -1)

    _NUM_BUTTONS_1 = 4
    _NUM_BUTTONS_2 = 2

    def __init__(self, adc_pin_1=None, adc_pin_2=None, power_pin=None, debounce=0.05):
        if adc_pin_1 is None:
            adc_pin_1 = board.BUTTON_ADC_1
        if adc_pin_2 is None:
            adc_pin_2 = board.BUTTON_ADC_2
        if power_pin is None:
            power_pin = board.BUTTON

        self._adc1 = AnalogIn(adc_pin_1)
        self._adc2 = AnalogIn(adc_pin_2)

        self._power = DigitalInOut(power_pin)
        self._power.direction = Direction.INPUT
        self._power.pull = Pull.UP

        self._debounce_delay = debounce
        self._current_state = 0
        self._last_state = 0
        self._pressed_events = 0
        self._released_events = 0
        self._last_debounce_time = 0.0
        self._button_press_start = 0.0
        self._button_press_finish = 0.0

    def deinit(self):
        """Release all underlying pin resources."""
        self._adc1.deinit()
        self._adc2.deinit()
        self._power.deinit()

    @property
    def current_state(self):
        """Bitmask of currently held buttons (after debounce)."""
        return self._current_state

    @property
    def pressed_events(self):
        """Bitmask of buttons that became pressed since the last
        :meth:`update`."""
        return self._pressed_events

    @property
    def released_events(self):
        """Bitmask of buttons that were released since the last
        :meth:`update`."""
        return self._released_events

    @property
    def any_pressed(self):
        """``True`` if any button was just pressed this update cycle."""
        return self._pressed_events > 0

    @property
    def any_released(self):
        """``True`` if any button was just released this update cycle."""
        return self._released_events > 0

    @property
    def held_time(self):
        """Duration in seconds a button has been or was held."""
        if self._current_state > 0:
            return time.monotonic() - self._button_press_start
        return self._button_press_finish - self._button_press_start

    @property
    def power_button_pressed(self):
        """``True`` if the power button is currently held."""
        return self.is_pressed(self.BTN_POWER)

    @property
    def back_pressed(self):
        """``True`` if the Back button is currently held."""
        return self.is_pressed(self.BTN_BACK)

    @property
    def confirm_pressed(self):
        """``True`` if the Confirm button is currently held."""
        return self.is_pressed(self.BTN_CONFIRM)

    @property
    def left_pressed(self):
        """``True`` if the Left button is currently held."""
        return self.is_pressed(self.BTN_LEFT)

    @property
    def right_pressed(self):
        """``True`` if the Right button is currently held."""
        return self.is_pressed(self.BTN_RIGHT)

    @property
    def up_pressed(self):
        """``True`` if the Up button is currently held."""
        return self.is_pressed(self.BTN_UP)

    @property
    def down_pressed(self):
        """``True`` if the Down button is currently held."""
        return self.is_pressed(self.BTN_DOWN)

    def is_pressed(self, button_index):
        """Return ``True`` if the given button is currently held.

        :param int button_index: A button index constant (e.g. ``BTN_BACK``).
        """
        return bool(self._current_state & (1 << button_index))

    def was_pressed(self, button_index):
        """Return ``True`` if the given button was just pressed this cycle.

        :param int button_index: A button index constant.
        """
        return bool(self._pressed_events & (1 << button_index))

    def was_released(self, button_index):
        """Return ``True`` if the given button was just released this cycle.

        :param int button_index: A button index constant.
        """
        return bool(self._released_events & (1 << button_index))

    @staticmethod
    def button_name(button_index):
        """Return a human-readable name for a button index.

        :param int button_index: A button index constant.
        """
        if 0 <= button_index <= InputManager.BTN_POWER:
            return InputManager._BUTTON_NAMES[button_index]
        return "Unknown"

    def update(self):
        """Poll buttons, debounce, and compute pressed/released events.

        Call this once per main-loop iteration.
        """
        now = time.monotonic()
        state = self._read_raw_state()

        self._pressed_events = 0
        self._released_events = 0

        if state != self._last_state:
            self._last_debounce_time = now
            self._last_state = state

        if (now - self._last_debounce_time) > self._debounce_delay:
            if state != self._current_state:
                self._pressed_events = state & ~self._current_state
                self._released_events = self._current_state & ~state

                if self._pressed_events and self._current_state == 0:
                    self._button_press_start = now

                if self._released_events and state == 0:
                    self._button_press_finish = now

                self._current_state = state

    @staticmethod
    def _button_from_adc(raw, ranges, num_buttons):
        """Map a raw ADC reading to a button index using threshold ranges."""
        for i in range(num_buttons):
            if ranges[i + 1] < raw <= ranges[i]:
                return i
        return -1

    def _read_raw_state(self):
        """Read all button inputs and return a combined bitmask."""
        state = 0

        raw1 = self._adc1.value
        btn1 = self._button_from_adc(raw1, self._ADC_RANGES_1, self._NUM_BUTTONS_1)
        if btn1 >= 0:
            state |= 1 << btn1

        raw2 = self._adc2.value
        btn2 = self._button_from_adc(raw2, self._ADC_RANGES_2, self._NUM_BUTTONS_2)
        if btn2 >= 0:
            state |= 1 << (btn2 + 4)

        if not self._power.value:
            state |= 1 << self.BTN_POWER

        return state
