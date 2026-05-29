# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_adg72x`
================================================================================

CircuitPython driver for the ADG728 and ADG729 analog matrix switches.


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit ADG729 1-to-4 Analog Matrix Switch <https://www.adafruit.com/product/5932>`_"
* `Adafruit ADG728 1-to-8 Analog Matrix Switch <https://www.adafruit.com/product/5899>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

import adafruit_bus_device.i2c_device as i2cdevice

try:
    import typing

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.5"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_ADG72x.git"

ADG728_DEFAULT_ADDR = 0x4C
ADG729_DEFAULT_ADDR = 0x44


class ADG72x:
    """
    A driver for the ADG728/ADG729 analog multiplexers.
    """

    def __init__(self, i2c: typing.Type[I2C], i2c_address: int = ADG728_DEFAULT_ADDR):
        """
        Initializes the ADG72x.

        :param i2c: The I2C bus connected to the device.
        :type i2c: Type[I2C]
        :param i2c_address: The I2C address of the device. Defaults to 0x4C (ADG728).
        :type i2c_address: int
        """
        self.i2c_device = i2cdevice.I2CDevice(i2c, i2c_address)
        self._channels = []

    @property
    def channel(self):
        """
        Gets the list of currently set channels. Returns an empty list if no channels are active.
        """
        return self._channels[0] if len(self._channels) == 1 else self._channels

    @channel.setter
    def channel(self, channel: int):
        """
        Selects a single channel on the ADG72x chip. Channel numbering starts at 0.

        :param bits: 8-bit value representing the channels to be selected/deselected.
        :type bits: int
        """
        bits = 1 << channel
        try:
            with self.i2c_device as i2c:
                i2c.write(bytes([bits]))
        except Exception as error:
            raise OSError("Failed to select channel on the ADG72x") from error
        self.channels = [channel]

    @property
    def channels(self):
        """
        Gets the list of currently set channels. Returns an empty list if no channels are active.
        """
        return self._channels

    @channels.setter
    def channels(self, channels: typing.List[int]):
        """
        Selects multiple channels on the ADG72x chip.

        :param channels: A list of channel numbers to be selected. Channel numbering starts at 0.
        :type channels: List[int]
        """
        bits = 0
        for channel in channels:
            bits |= 1 << channel
        try:
            with self.i2c_device as i2c:
                i2c.write(bytes([bits]))
        except Exception as error:
            raise OSError("Failed to select channels on the ADG72x") from error
        self._channels = channels  # Update the cached list of active channels

    def channels_off(self):
        """
        Turns all channels off.
        """
        try:
            with self.i2c_device as i2c:
                i2c.write(bytes([0]))  # Write a byte with all bits cleared
        except Exception as error:
            raise OSError("Failed to turn off channels on the ADG72x") from error
        self._channels = []  # Update the cached list to reflect that no channels are active
