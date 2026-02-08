# SPDX-FileCopyrightText: Copyright (c) 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_stspin`
================================================================================

CircuitPython driver for the Adafruit STSPIN220 Stepper Motor Driver Breakout Board


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit STSPIN220 Stepper Motor Driver Breakout Board <https://www.adafruit.com/product/6353>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""

import time

from digitalio import DigitalInOut, Direction, Pull
from micropython import const

try:
    from typing import Literal, Optional
except ImportError:
    pass

__version__ = "1.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_STSPIN.git"


# Timing characteristics
TOFF_MIN_US = const(9)  # Minimum OFF time with ROFF=10kΩ (μs)
TOFF_MAX_US = const(125)  # Maximum OFF time with ROFF=160kΩ (μs)
STCK_MIN_PULSE_NS = const(100)  # Minimum STCK pulse width (ns)
DIR_SETUP_TIME_NS = const(100)  # DIR input setup time (ns)
DIR_HOLD_TIME_NS = const(100)  # DIR input hold time (ns)
STCK_MAX_FREQ_MHZ = const(1)  # Maximum STCK frequency (MHz)


class Modes:
    """Valid microstepping modes for STSPIN220.

    Each mode value encodes the state of MODE1-MODE4 pins:
    - Bits 0-1: MODE1, MODE2 (physical pins if connected)
    - Bits 2-3: MODE3, MODE4 (multiplexed with STEP/DIR during reset)
    """

    STEP_FULL = const(0b0000)  # Full step mode
    STEP_1_2 = const(0b0101)  # 1/2 step mode
    STEP_1_4 = const(0b1010)  # 1/4 step mode
    STEP_1_8 = const(0b0111)  # 1/8 step mode
    STEP_1_16 = const(0b1111)  # 1/16 step mode (default)
    STEP_1_32 = const(0b0010)  # 1/32 step mode
    STEP_1_64 = const(0b1011)  # 1/64 step mode
    STEP_1_128 = const(0b0001)  # 1/128 step mode
    STEP_1_256 = const(0b0011)  # 1/256 step mode

    _MICROSTEPS = {
        STEP_FULL: 1,
        STEP_1_2: 2,
        STEP_1_4: 4,
        STEP_1_8: 8,
        STEP_1_16: 16,
        STEP_1_32: 32,
        STEP_1_64: 64,
        STEP_1_128: 128,
        STEP_1_256: 256,
    }

    @classmethod
    def microsteps(cls, mode: int) -> int:
        """Get number of microsteps for a given mode.

        :param int mode: Step mode constant
        :return: Number of microsteps per full step
        :rtype: int
        """
        return cls._MICROSTEPS.get(mode, 16)  # Default to 16

    @classmethod
    def is_valid(cls, mode: int) -> bool:
        """Check if a mode value is valid.

        :param int mode: Mode value to check
        :return: True if valid mode
        :rtype: bool
        """
        return mode in cls._MICROSTEPS


class STSPIN:
    """Driver for the STSPIN220 Low Voltage Stepper Motor Driver.

    :param ~microcontroller.Pin step_pin: The pin connected to STEP (step clock) input
    :param ~microcontroller.Pin dir_pin: The pin connected to DIR (direction) input
    :param int steps_per_revolution: Number of steps per full motor revolution
    :param ~microcontroller.Pin mode1_pin: The pin connected to MODE1 input (optional)
    :param ~microcontroller.Pin mode2_pin: The pin connected to MODE2 input (optional)
    :param ~microcontroller.Pin en_fault_pin: The pin connected to EN/FAULT pin (optional)
    :param ~microcontroller.Pin stby_reset_pin: The pin connected to STBY/RESET pin (optional)
    """

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        step_pin,
        dir_pin,
        steps_per_revolution: int = 200,
        mode1_pin=None,
        mode2_pin=None,
        en_fault_pin=None,
        stby_reset_pin=None,
    ) -> None:
        # Initialize pins
        self._step_pin = DigitalInOut(step_pin)
        self._step_pin.direction = Direction.OUTPUT
        self._step_pin.value = True

        self._dir_pin = DigitalInOut(dir_pin)
        self._dir_pin.direction = Direction.OUTPUT
        self._dir_pin.value = True

        # Optional pins
        self._mode1_pin = None
        self._mode2_pin = None
        if mode1_pin is not None:
            self._mode1_pin = DigitalInOut(mode1_pin)
            self._mode1_pin.direction = Direction.OUTPUT
            self._mode1_pin.value = True

        if mode2_pin is not None:
            self._mode2_pin = DigitalInOut(mode2_pin)
            self._mode2_pin.direction = Direction.OUTPUT
            self._mode2_pin.value = True

        self._en_fault_pin = None
        if en_fault_pin is not None:
            self._en_fault_pin = DigitalInOut(en_fault_pin)
            self._en_fault_pin.direction = Direction.INPUT
            self._en_fault_pin.pull = Pull.UP

        self._stby_reset_pin = None
        if stby_reset_pin is not None:
            self._stby_reset_pin = DigitalInOut(stby_reset_pin)
            self._stby_reset_pin.direction = Direction.OUTPUT
            self._stby_reset_pin.value = True

        # Motor parameters
        self._steps_per_revolution = steps_per_revolution
        self._step_delay = 0.001  # Default 1ms between steps
        self._step_number = 0
        self._last_step_time = 0
        self._step_mode = Modes.STEP_1_16  # Default to 1/16 microstepping
        self._enabled = True

        # Set initial step mode if mode pins are available
        if self._mode1_pin and self._mode2_pin:
            mode_bits = self._step_mode
            self._mode1_pin.value = bool(mode_bits & 0x01)
            self._mode2_pin.value = bool(mode_bits & 0x02)

    @property
    def speed(self) -> float:
        """Motor speed in revolutions per minute (RPM).

        :return: Current speed in RPM
        :rtype: float
        """
        if self._step_delay >= 1.0:
            return 0.0

        microsteps = self.microsteps_per_step
        steps_per_second = 1.0 / self._step_delay
        steps_per_minute = steps_per_second * 60.0
        rpm = steps_per_minute / (self._steps_per_revolution * microsteps)
        return rpm

    @speed.setter
    def speed(self, rpm: float) -> None:
        """Set motor speed in revolutions per minute (RPM).

        :param float rpm: Desired speed in RPM (must be positive)
        """
        if rpm <= 0:
            self._step_delay = 1.0
        else:
            # Account for microstepping
            microsteps = self.microsteps_per_step
            steps_per_minute = rpm * self._steps_per_revolution * microsteps
            steps_per_second = steps_per_minute / 60.0
            self._step_delay = 1.0 / steps_per_second

            # Enforce minimum step delay (1 MHz max frequency = 1 μs minimum)
            if self._step_delay < 0.000001:
                self._step_delay = 0.000001

    @property
    def step_mode(self) -> int:
        """Current microstepping mode.

        :return: Current step mode constant from Modes class
        :rtype: int
        """
        return self._step_mode

    @step_mode.setter
    def step_mode(self, mode: int) -> None:
        """Set the microstepping mode.

        :param int mode: Step mode constant from Modes class (e.g., Modes.STEP_1_16)
        :raises ValueError: If mode is invalid or cannot be set with available pins
        """
        if not Modes.is_valid(mode):
            raise ValueError(f"Invalid step mode: {mode}")

        if self._stby_reset_pin is None:
            raise ValueError("Cannot set step mode without STBY/RESET pin")

        mode_bits = mode

        # Check if we can set this mode with available pins
        if (self._mode1_pin is None) or (self._mode2_pin is None):
            # If mode1/mode2 pins not available, only allow modes where those bits are high
            if (mode_bits & 0x01) == 0 or (mode_bits & 0x02) == 0:
                raise ValueError(
                    "Cannot set mode requiring low MODE1/MODE2 without those pins connected"
                )

        # Put device into standby/reset
        self._stby_reset_pin.value = False
        time.sleep(0.001)  # 1 ms

        # Set all available mode pins (MODE1, MODE2, STEP/MODE3, DIR/MODE4)
        if self._mode1_pin is not None:
            self._mode1_pin.value = bool(mode_bits & 0x01)
        if self._mode2_pin is not None:
            self._mode2_pin.value = bool(mode_bits & 0x02)
        self._step_pin.value = bool(mode_bits & 0x04)
        self._dir_pin.value = bool(mode_bits & 0x08)

        # Come out of standby to latch the mode
        self._stby_reset_pin.value = True

        self._step_mode = mode

    @property
    def microsteps_per_step(self) -> int:
        """Number of microsteps per full step for current mode.

        :return: Microsteps per full step (1, 2, 4, 8, 16, 32, 64, 128, or 256)
        :rtype: int
        """
        return Modes.microsteps(self._step_mode)

    @property
    def fault(self) -> bool:
        """Check if a fault condition exists.

        :return: True if fault detected, False if normal operation
        :rtype: bool
        """
        if self._en_fault_pin is None:
            return False

        return not self._en_fault_pin.value

    @property
    def position(self) -> int:
        """Current motor position in steps (0 to steps_per_revolution-1).

        :return: Current position in steps
        :rtype: int
        """
        return self._step_number

    def step(self, steps: int) -> None:
        """Move the motor a specified number of steps.

        :param int steps: Number of steps to move (positive = forward, negative = reverse)
        """
        steps_left = abs(steps)
        self._dir_pin.value = steps > 0
        time.sleep(0.000001)  # 1 μs setup time

        start_time = time.monotonic()
        target_time = start_time

        for i in range(steps_left):
            target_time = start_time + (i * self._step_delay)

            now = time.monotonic()
            wait_time = target_time - now
            if wait_time > 0:
                time.sleep(wait_time)

            self._step()

            if steps > 0:
                self._step_number += 1
                if self._step_number >= self._steps_per_revolution:
                    self._step_number = 0
            elif self._step_number == 0:
                self._step_number = self._steps_per_revolution - 1
            else:
                self._step_number -= 1

        self._last_step_time = time.monotonic()

    def _step(self) -> None:
        """Perform a single step pulse."""
        self._step_pin.value = False
        time.sleep(0.000001)  # 1 μs pulse width
        self._step_pin.value = True

    def step_blocking(self, steps: int, delay_seconds: float = 0.001) -> None:
        """Move the motor with blocking delay between steps.

        :param int steps: Number of steps to move (positive = forward, negative = reverse)
        :param float delay_seconds: Delay between steps in seconds
        """
        steps_left = abs(steps)
        self._dir_pin.value = steps > 0
        time.sleep(0.000001)  # 1 μs setup time

        for _ in range(steps_left):
            self._step()
            time.sleep(delay_seconds)

    @property
    def enabled(self) -> bool:
        """Motor power stage enable state.

        :return: True if enabled, False if disabled
        :rtype: bool
        """
        if self._en_fault_pin is None:
            return True  # If no enable pin, assume enabled
        return self._enabled

    @enabled.setter
    def enabled(self, state: bool) -> None:
        """Enable or disable the motor power stage.

        :param bool state: True to enable, False to disable
        """
        if self._en_fault_pin is None:
            return

        # Ensure pin is configured as output
        if self._en_fault_pin.direction != Direction.OUTPUT:
            self._en_fault_pin.direction = Direction.OUTPUT

        # Set pin high to enable, low to disable
        self._en_fault_pin.value = state
        self._enabled = state

    @property
    def standby(self) -> bool:
        """Device standby state.

        :return: True if in standby mode, False if active
        :rtype: bool
        """
        if self._stby_reset_pin is None:
            return False  # If no standby pin, assume active
        return not self._stby_reset_pin.value  # Low = standby, High = active

    @standby.setter
    def standby(self, state: bool) -> None:
        """Put the device into standby mode or wake it up.

        :param bool state: True to enter standby (ultra-low power), False to wake up
        """
        if self._stby_reset_pin is None:
            return

        if state:
            # Going into standby/reset - pull pin low
            self._stby_reset_pin.value = False
        else:
            # Coming out of standby/reset - pull pin high
            self._stby_reset_pin.value = True
            # After waking up, we need to restore the step mode
            # by reconfiguring the MODE pins
            if hasattr(self, "_step_mode"):
                # Re-apply the current step mode
                self.step_mode = self._step_mode

    def clear_fault(self) -> None:
        """Clear fault condition by toggling enable pin."""
        if self._en_fault_pin is None:
            return

        # Ensure we're in output mode to control the pin
        self._en_fault_pin.direction = Direction.OUTPUT

        # Toggle the pin low then high to clear the fault
        self._en_fault_pin.value = False
        time.sleep(0.001)  # 1 ms
        self._en_fault_pin.value = True

        self._enabled = True

    def reset(self) -> None:
        """Reset the device by toggling the STBY/RESET pin."""
        if self._stby_reset_pin is None:
            return

        self.standby(True)
        time.sleep(0.001)  # 1 ms
        self.standby(False)
