# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_s35710`
================================================================================

CircuitPython driver for the S-35710 low-power wake up timer


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit S-35710 Low-Power Wake Up Timer Breakout <https://www.adafruit.com/product/5959>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

import adafruit_bus_device.i2c_device as i2cdevice
from micropython import const

try:
    import typing

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.6"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_S35710.git"


_DEFAULT_I2C_ADDR = const(0x32)


class Adafruit_S35710:
    """
    A driver for the S-35710 Low-Power Wake Up Timer
    """

    def __init__(self, i2c: typing.Type[I2C], address: int = _DEFAULT_I2C_ADDR):
        """Initialize the S-35710 Wake-Up Timer IC over I2C.

        :param i2c: The I2C bus object.
        :type i2c: Type[I2C]
        :param address: The I2C address of the S-35710, defaults to 0x32.
        :type i2c_address: int
        """
        self.i2c_device = i2cdevice.I2CDevice(i2c, address)

    @property
    def alarm(self):
        """Wake-up alarm time register value."""
        try:
            buffer = bytearray(3)
            with self.i2c_device as device:
                device.write_then_readinto(bytearray([0x01]), buffer)
            value = (buffer[0] << 16) | (buffer[1] << 8) | buffer[2]
            return value
        except Exception as error:
            raise ValueError("Failed to read wake-up time register: ", error) from error

    @alarm.setter
    def alarm(self, value: int):
        """Wake-up alarm time register value.

        :param value: the alarm time in seconds
        :type value: int
        """
        try:
            buffer = bytearray([0x81, (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF])
            with self.i2c_device as device:
                device.write(buffer)
        except Exception as error:
            raise ValueError("Failed to write wake-up time register: ", error) from error

    @property
    def clock(self):
        """Current time register value."""
        try:
            buffer = bytearray(3)
            with self.i2c_device as device:
                device.readinto(buffer)
            value = (buffer[0] << 16) | (buffer[1] << 8) | buffer[2]
            return value
        except Exception as error:
            raise ValueError("Failed to read time register: ", error) from error
