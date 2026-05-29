# SPDX-FileCopyrightText: Copyright (c) 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_dacx578`
================================================================================

CircuitPython driver for the Adafruit DAC7578 - 8 x Channel 12-bit I2C DAC - STEMMA QT / Qwiic


* Author(s): Liz Clark
* With assistance from Claude AI 3.5 Sonnet

Implementation Notes
--------------------

**Hardware:**

* `Adafruit DAC7578 - 8 x Channel 12-bit I2C DAC <https://www.adafruit.com/product/6223>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

import time

from adafruit_bus_device.i2c_device import I2CDevice
from micropython import const

try:
    from typing import Literal, Union

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_DAC7578.git"

_DAC7578_DEFAULT_ADDRESS: int = const(0x4C)

# Command registers (pre-shifted)
_REG_WRITE: int = const(0x00)
_REG_UPDATE: int = const(0x10)
_REG_WRITE_UPDATE: int = const(0x30)
_REG_WRITE_GLOBAL_UPDATE: int = const(0x20)
_REG_RESET: int = const(0x50)
_REG_LDAC_MASK: int = const(0x60)
_REG_WRITE_CLEAR: int = const(0x50)
_REG_READ_CLEAR: int = const(0x50)

# Other constants
_CHANNEL_BROADCAST: int = const(0xF)


class Channel:
    """
    Represents a single channel for the DAC7578.

    :param DACx578 dac_instance: The parent DAC instance
    :param int index: The channel index (0-7)
    """

    def __init__(self, dac_instance: "DACx578", index: int) -> None:
        self._dac: DACx578 = dac_instance
        self._channel_index: int = index
        self._value: int = 0

    @property
    def normalized_value(self) -> float:
        """The DAC value as a floating point number in the range 0.0 to 1.0."""
        max_value: int = (1 << self._dac.resolution) - 1
        return self._value / max_value

    @normalized_value.setter
    def normalized_value(self, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("Value must be between 0.0 and 1.0")
        max_value: int = (1 << self._dac.resolution) - 1
        self.raw_value = int(value * max_value)

    @property
    def value(self) -> int:
        """The 16-bit scaled value for the channel."""
        return int(self.normalized_value * 65535)

    @value.setter
    def value(self, value: int) -> None:
        if not 0 <= value <= 65535:
            raise ValueError("Value must be between 0 and 65535")
        max_raw: int = (1 << self._dac.resolution) - 1
        self.raw_value = (value * max_raw) // 65535

    @property
    def raw_value(self) -> int:
        """The raw value used by the DAC based on current resolution."""
        return self._value

    @raw_value.setter
    def raw_value(self, value: int) -> None:
        max_value: int = (1 << self._dac.resolution) - 1
        if not 0 <= value <= max_value:
            raise ValueError(f"Value must be between 0 and {max_value}")
        self._value = value
        self._dac._write_channel(self._channel_index, value)

    @property
    def ldac(self) -> bool:
        """LDAC setting for an individual channel"""
        current_mask: int = self._dac.ldac_mask
        return not bool(current_mask & (1 << self._channel_index))

    @ldac.setter
    def ldac(self, enable: bool) -> None:
        current_mask: int = self._dac.ldac_mask
        if enable:
            new_mask: int = current_mask & ~(1 << self._channel_index)
        else:
            new_mask: int = current_mask | (1 << self._channel_index)
        self._dac.ldac_mask = new_mask


class DACx578:
    """
    Driver for the DAC7578 12/10/8-bit 8-channel DAC.

    :param I2C i2c_bus: The I2C bus the DAC is connected to
    :param int address: The I2C device address. Defaults to 0x47
    :param int resolution: The DAC resolution in bits (8, 10, or 12). Defaults to 12
    """

    clear_codes: list[str] = ["ZERO", "MID", "FULL", "NOP"]

    def __init__(
        self,
        i2c_bus: I2C,
        address: int = _DAC7578_DEFAULT_ADDRESS,
        resolution: Literal[8, 10, 12] = 12,
    ) -> None:
        if resolution not in {8, 10, 12}:
            raise ValueError("Resolution must be 8, 10, or 12 bits")
        self._resolution: int = resolution
        self.i2c_device: I2CDevice = I2CDevice(i2c_bus, address)
        self._buffer: bytearray = bytearray(3)

        self.channels: list[Channel] = [Channel(self, i) for i in range(8)]
        self.reset()

    @property
    def resolution(self) -> int:
        """DAC resolution in bits (8, 10, or 12)."""
        return self._resolution

    def reset(self) -> None:
        """Resets the device to its default state."""
        self._buffer[0] = _REG_RESET
        self._buffer[1] = 0
        self._buffer[2] = 0
        with self.i2c_device as i2c:
            i2c.write(self._buffer)

    def _write_channel(self, channel: int, value: int) -> None:
        shift_amount: int = 16 - self._resolution
        value <<= shift_amount
        self._buffer[0] = _REG_WRITE_UPDATE | (channel & 0xF)
        self._buffer[1] = (value >> 8) & 0xFF
        self._buffer[2] = value & 0xFF
        with self.i2c_device as i2c:
            i2c.write(self._buffer)

    @property
    def clear_code(self) -> str:
        """
        Current clear code setting.

        :return: One of "ZERO", "MID", "FULL", or "NOP"
        :rtype: str
        """
        self._buffer[0] = _REG_RESET
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([_REG_RESET]), self._buffer)
        value: int = self._buffer[2] & 0x03
        return self.clear_codes[value]

    @clear_code.setter
    def clear_code(self, code: str) -> None:
        """
        :param str code: One of "ZERO", "MID", "FULL", or "NOP"
        :raises ValueError: If code is not a valid option
        """
        code = code.upper()
        if code not in self.clear_codes:
            raise ValueError(f"Clear code must be one of: {', '.join(self.clear_codes)}")
        value: int = self.clear_codes.index(code)
        self._buffer[0] = _REG_RESET
        self._buffer[1] = 0x00
        self._buffer[2] = value & 0x03
        with self.i2c_device as i2c:
            i2c.write(self._buffer)

    @property
    def ldac_mask(self) -> int:
        """
        The 8-bit LDAC mask.

        :return: The LDAC mask value.
        :rtype: int
        """
        return self._buffer[1]

    @ldac_mask.setter
    def ldac_mask(self, value: int) -> None:
        """
        :param int value: The LDAC mask value (0-255)
        :raises ValueError: If the value is out of range
        """
        if not 0 <= value <= 255:
            raise ValueError("LDAC mask must be between 0 and 255")
        self._buffer[1] = value
        with self.i2c_device as i2c:
            i2c.write(self._buffer)
