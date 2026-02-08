# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
:py:class:`~adafruit_hx711.hx711.HX711`
================================================================================

CircuitPython driver for the HX711 24-bit ADC for Load Cells / Strain Gauges


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Link Text <https://www.adafruit.com/product/5974>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""

import time

import microcontroller

try:
    from typing import Union

    import digitalio
except ImportError:
    pass

__version__ = "1.1.0"
__repo__ = "https://github.com/your-repo/Adafruit_CircuitPython_HX711.git"


def read_fast(clock_pin: digitalio.DigitalInOut, data_pin: digitalio.DigitalInOut, size: int):
    value: int = 0  # return value
    assert not clock_pin.value
    assert size > 0
    # The first iteration of the while loop takes longer, so to cancel
    # this problem, we skip the first clock
    clock_to_skip: int = 1
    # Disable interrupts just before the loop
    microcontroller.disable_interrupts()
    while size > 0:
        if clock_to_skip <= 0:  # no more skipping
            clock_pin.value = True
            size -= 1
        microcontroller.delay_us(1)
        if clock_to_skip > 0:
            clock_to_skip -= 1  # decrement skip counter and do not read
        else:
            value = (value << 1) | data_pin.value
        clock_pin.value = False
        microcontroller.delay_us(1)
    # Re-enable interrupts as soon as possible
    microcontroller.enable_interrupts()
    return value


class HX711:
    """HX711 ADC driver"""

    CHAN_A_GAIN_128 = 25
    CHAN_A_GAIN_64 = 27
    CHAN_B_GAIN_32 = 26

    def __init__(self, data_pin: digitalio.DigitalInOut, clock_pin: digitalio.DigitalInOut) -> None:
        """
        Initialize the HX711 module.

        :param data_pin: The data pin.
        :param clock_pin: The clock pin.
        """
        self._data_pin = data_pin
        self._clock_pin = clock_pin
        self._tare_value_a = 0
        self._tare_value_b = 0
        self._initialize()

    def _initialize(self) -> None:
        """Perform a power reset and wake up the HX711."""
        self.power_down(True)  # Perform a power reset
        time.sleep(0.001)  # Hold pin high for 1 ms for reset
        self.power_down(False)  # Wake up

    def power_down(self, down: bool) -> None:
        """
        Power down or wake up the HX711.

        :param down: True to power down, False to wake up.
        """
        self._clock_pin.value = down

    def read_channel_blocking(self, chan_gain: int) -> int:
        """
        Read ADC value with specified gain in a blocking manner.

        :param chan_gain: Gain and channel configuration.
        :return: ADC value.
        """
        # First, set the desired gain and discard this read
        self._read_channel(chan_gain)
        return self._read_channel(chan_gain)  # Now perform the actual read

    def _read_channel(self, chan_gain: int) -> int:
        """
        Read ADC value with specified gain.

        :param chan_gain: Gain and channel configuration.
        :return: ADC value.
        """
        return self._read_channel_raw(chan_gain) - (
            self._tare_value_b if chan_gain == self.CHAN_B_GAIN_32 else self._tare_value_a
        )

    def _read_channel_raw(self, chan_gain: int) -> int:
        """
        Read raw ADC value with specified gain.

        :param chan_gain: Gain and channel configuration.
        :return: Raw ADC value.
        """
        while self.is_busy:
            pass  # Wait until the HX711 is ready

        self._clock_pin.value = False
        value = read_fast(self._clock_pin, self._data_pin, chan_gain) >> (chan_gain - 24)

        # Convert to 32-bit signed integer
        if value & 0x80_00_00:
            value |= 0xFF_00_00_00

        return value

    @property
    def is_busy(self) -> bool:
        """
        Check if the HX711 is busy.

        :return: True if busy, False otherwise.
        """
        return self._data_pin.value

    @property
    def tare_value_a(self) -> int:
        """
        Get the tare value for channel A.

        :return: Tare value for channel A.
        """
        return self._tare_value_a

    @tare_value_a.setter
    def tare_value_a(self, tare_value: int) -> None:
        """
        Set the tare value for channel A.

        :param tare_value: Tare value for channel A.
        """
        self._tare_value_a = tare_value

    @property
    def tare_value_b(self) -> int:
        """
        Get the tare value for channel B.

        :return: Tare value for channel B.
        """
        return self._tare_value_b

    @tare_value_b.setter
    def tare_value_b(self, tare_value: int) -> None:
        """
        Set the tare value for channel B.

        :param tare_value: Tare value for channel B.
        """
        self._tare_value_b = tare_value

    def read(self, chan_gain: int = CHAN_A_GAIN_128) -> int:
        """
        Read ADC value with specified gain.

        :param chan_gain: Gain and channel configuration.
        :return: ADC value.
        """
        return self.read_channel_blocking(chan_gain)
