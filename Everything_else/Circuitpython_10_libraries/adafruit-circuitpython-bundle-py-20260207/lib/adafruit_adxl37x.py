# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_adxl37x`
================================================================================

A CircuitPython driver for the ADXL37x family of accelerometers


* Author(s): Kattni Rembor

Implementation Notes
--------------------

**Hardware:**

* `ADXL375 - High G Accelerometer (+-200g) <https://www.adafruit.com/product/5374>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit CircuitPython ADXL34x: https://github.com/adafruit/Adafruit_CircuitPython_ADXL34x

"""

from struct import unpack

import adafruit_adxl34x
from micropython import const

try:
    from typing import Dict, Optional, Tuple

    # This is only needed for typing
    import busio
except ImportError:
    pass

__version__ = "1.2.5"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_ADXL37x.git"

_ADXL375_DEFAULT_ADDRESS = const(0x53)

_ADXL347_MULTIPLIER: float = 0.049  # 49mg per lsb
_STANDARD_GRAVITY: float = 9.80665  # earth standard gravity

_REG_DEVID: int = const(0x00)  # Device ID
_REG_THRESH_TAP: int = const(0x1D)  # Tap threshold
_REG_OFSX: int = const(0x1E)  # X-axis offset
_REG_OFSY: int = const(0x1F)  # Y-axis offset
_REG_OFSZ: int = const(0x20)  # Z-axis offset
_REG_DUR: int = const(0x21)  # Tap duration
_REG_LATENT: int = const(0x22)  # Tap latency
_REG_WINDOW: int = const(0x23)  # Tap window
_REG_THRESH_ACT: int = const(0x24)  # Activity threshold
_REG_THRESH_INACT: int = const(0x25)  # Inactivity threshold
_REG_TIME_INACT: int = const(0x26)  # Inactivity time
_REG_ACT_INACT_CTL: int = const(0x27)  # Axis enable control for [in]activity detection
_REG_THRESH_FF: int = const(0x28)  # Free-fall threshold
_REG_TIME_FF: int = const(0x29)  # Free-fall time
_REG_TAP_AXES: int = const(0x2A)  # Axis control for single/double tap
_REG_ACT_TAP_STATUS: int = const(0x2B)  # Source for single/double tap
_REG_BW_RATE: int = const(0x2C)  # Data rate and power mode control
_REG_POWER_CTL: int = const(0x2D)  # Power-saving features control
_REG_INT_ENABLE: int = const(0x2E)  # Interrupt enable control
_REG_INT_MAP: int = const(0x2F)  # Interrupt mapping control
_REG_INT_SOURCE: int = const(0x30)  # Source of interrupts
_REG_DATA_FORMAT: int = const(0x31)  # Data format control
_REG_DATAX0: int = const(0x32)  # X-axis data 0
_REG_DATAX1: int = const(0x33)  # X-axis data 1
_REG_DATAY0: int = const(0x34)  # Y-axis data 0
_REG_DATAY1: int = const(0x35)  # Y-axis data 1
_REG_DATAZ0: int = const(0x36)  # Z-axis data 0
_REG_DATAZ1: int = const(0x37)  # Z-axis data 1
_REG_FIFO_CTL: int = const(0x38)  # FIFO control
_REG_FIFO_STATUS: int = const(0x39)  # FIFO status
_INT_DATA_READY: int = const(0b10000000)  # DATA_READY bit
_INT_SINGLE_TAP: int = const(0b01000000)  # SINGLE_TAP bit
_INT_DOUBLE_TAP: int = const(0b00100000)  # DOUBLE_TAP bit
_INT_ACT: int = const(0b00010000)  # ACT bit
_INT_INACT: int = const(0b00001000)  # INACT bit


# _INT_FREE_FALL: int = const(0b00000100)  # FREE_FALL  bit, unused in ADXL375


class DataRate(adafruit_adxl34x.DataRate):
    """Stub class for data rate."""


class Range:
    """An enum-like class representing the possible measurement ranges in +/- G.

    Possible values are:

    - ``Range.RANGE_200_G``
    - ``Range.RANGE_100_G``
    - ``Range.RANGE_50_G``
    - ``Range.RANGE_25_G``

    """

    RANGE_200_G: int = const(0b11)  # +/- 200g
    RANGE_100_G: int = const(0b10)  # +/- 100g
    RANGE_50_G: int = const(0b01)  # +/- 50g
    RANGE_25_G: int = const(0b00)  # +/- 25g (default value)


class ADXL375(adafruit_adxl34x.ADXL345):
    """
    Driver for the ADXL375 accelerometer

    :param ~busio.I2C i2c: The I2C bus the ADXL375 is connected to.
    :param int address: The I2C device address for the sensor. Default is :const:`0x53`.

    **Quickstart: Importing and using the device**

        Here is an example of using the :class:`ADXL375` class.
        First you will need to import the libraries to use the sensor.

        .. code-block:: python

            import board
            import adafruit_adxl37x

        Once this is done you can define your `board.I2C` object and define your sensor object.
        If using the STEMMA QT connector built into your microcontroller,
        use ``board.STEMMA_I2C()``.

        .. code-block:: python

            i2c = board.I2C()  # uses board.SCL and board.SDA
            accelerometer = adafruit_adxl37x.ADXL375(i2c)

        Now you have access to the :attr:`acceleration` attribute.

        .. code-block:: python

            acceleration = accelerometer.acceleration

    """

    def __init__(self, i2c: busio.I2C, address: Optional[int] = None):
        super().__init__(i2c, address if address is not None else _ADXL375_DEFAULT_ADDRESS)

    @property
    def acceleration(self) -> Tuple[int, int, int]:
        """The x, y, z acceleration values returned in a 3-tuple in :math:`m / s ^ 2`"""
        x, y, z = unpack("<hhh", self._read_register(_REG_DATAX0, 6))
        x = x * _ADXL347_MULTIPLIER * _STANDARD_GRAVITY
        y = y * _ADXL347_MULTIPLIER * _STANDARD_GRAVITY
        z = z * _ADXL347_MULTIPLIER * _STANDARD_GRAVITY
        return x, y, z

    @property
    def range(self) -> int:
        """The measurement range of the sensor."""
        range_register = self._read_register_unpacked(_REG_DATA_FORMAT)
        return range_register & 0x03

    @range.setter
    def range(self, val: int) -> None:
        # read the current value of the data format register
        format_register = self._read_register_unpacked(_REG_DATA_FORMAT)

        # update the range
        format_register |= val

        # Make sure that the FULL-RES bit is enabled for range scaling
        format_register |= 0x08

        # write the updated values
        self._write_register_byte(_REG_DATA_FORMAT, format_register)

    @property
    def events(self) -> Dict[str, bool]:
        """
        :attr: `events` will return a dictionary with a key for each
        event type that has been enabled.
        The possible keys are:

        +------------+----------------------------------------------------------------------------+
        | Key        | Description                                                                |
        +============+============================================================================+
        | ``tap``      | True if a tap was detected recently. Whether it's looking for a single   |
        |              | or double tap is determined by the tap param of                          |
        |              | :meth:`adafruit_adxl34x.enable_tap_detection`                            |
        +------------+----------------------------------------------------------------------------+
        | ``motion``   | True if the sensor has seen acceleration above the threshold             |
        |              | set with :meth:`adafruit_adxl34x.enable_motion_detection`                |
        +------------+----------------------------------------------------------------------------+
        | ``data_ready`` | True if the sensor has data to be read. Can be used for more precise   |
        |                | timing if reading many samples. Set with `enable_data_ready_interrupt` |
        +------------+----------------------------------------------------------------------------+


        """

        interrupt_source_register = self._read_clear_interrupt_source()

        self._event_status.clear()

        for event_type, value in self._enabled_interrupts.items():
            if event_type == "motion":
                self._event_status[event_type] = interrupt_source_register & _INT_ACT > 0
            if event_type == "tap":
                if value == 1:
                    self._event_status[event_type] = interrupt_source_register & _INT_SINGLE_TAP > 0
                else:
                    self._event_status[event_type] = interrupt_source_register & _INT_DOUBLE_TAP > 0
            if event_type == "data_ready":
                self._event_status[event_type] = interrupt_source_register & _INT_DATA_READY > 0

        return self._event_status

    def enable_data_ready_interrupt(self):
        """
        Enable Data Ready interrupt for precise data timing
        """
        active_interrupts = self._read_register_unpacked(_REG_INT_ENABLE)

        self._write_register_byte(_REG_INT_ENABLE, 0x0)  # disable interrupts for setup

        # add DATA_READY to the active interrupts and set them to re-enable
        active_interrupts |= _INT_DATA_READY
        self._write_register_byte(_REG_INT_ENABLE, active_interrupts)
        self._enabled_interrupts["data_ready"] = True

    def disable_data_ready_interrupt(self) -> None:
        """Disable Data Ready interrupt"""
        active_interrupts = self._read_register_unpacked(_REG_INT_ENABLE)
        active_interrupts &= ~_INT_DATA_READY
        self._write_register_byte(_REG_INT_ENABLE, active_interrupts)
        self._enabled_interrupts.pop("data_ready")
