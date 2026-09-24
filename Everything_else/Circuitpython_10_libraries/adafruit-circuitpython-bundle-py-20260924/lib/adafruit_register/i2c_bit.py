# SPDX-FileCopyrightText: 2016 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_register.i2c_bit`
====================================================

Single bit registers

* Author(s): Scott Shawcroft
"""

__version__ = "1.13.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Register.git"

try:
    from typing import NoReturn, Optional, Type

    from circuitpython_typing.device_drivers import I2CDeviceDriver
except ImportError:
    pass

from adafruit_register import _BUFFER, _fit


class RWBit:
    """
    Single bit register that is readable and writeable.

    Values are `bool`

    :param int register_address: The register address to read the bit from
    :param int bit: The bit index within the byte at ``register_address``
    :param int register_width: The number of bytes in the register. Defaults to 1.
    :param bool lsb_first: Is the first byte we read from I2C the LSB? Defaults to true

    """

    def __init__(
        self,
        register_address: int,
        bit: int,
        register_width: int = 1,
        lsb_first: bool = True,
    ) -> None:
        self.bit_mask = 1 << (bit % 8)  # the bitmask *within* the byte!
        self.address = register_address
        self.register_width = register_width
        _fit(register_width)
        if lsb_first:
            self.byte = bit // 8 + 1  # the byte number within the buffer
        else:
            self.byte = register_width - (bit // 8)  # the byte number within the buffer

    def __get__(
        self,
        obj: Optional[I2CDeviceDriver],
        objtype: Optional[Type[I2CDeviceDriver]] = None,
    ) -> bool:
        _BUFFER[0] = self.address
        with obj.i2c_device as i2c:
            i2c.write_then_readinto(
                _BUFFER, _BUFFER, out_end=1, in_start=1, in_end=1 + self.register_width
            )
        return bool(_BUFFER[self.byte] & self.bit_mask)

    def __set__(self, obj: I2CDeviceDriver, value: bool) -> None:
        _BUFFER[0] = self.address
        with obj.i2c_device as i2c:
            i2c.write_then_readinto(
                _BUFFER, _BUFFER, out_end=1, in_start=1, in_end=1 + self.register_width
            )
            if value:
                _BUFFER[self.byte] |= self.bit_mask
            else:
                _BUFFER[self.byte] &= ~self.bit_mask
            i2c.write(_BUFFER, end=1 + self.register_width)


class ROBit(RWBit):
    """Single bit register that is read only. Subclass of `RWBit`.

    Values are `bool`

    :param int register_address: The register address to read the bit from
    :param type bit: The bit index within the byte at ``register_address``
    :param int register_width: The number of bytes in the register. Defaults to 1.

    """

    def __set__(self, obj: I2CDeviceDriver, value: bool) -> NoReturn:
        raise AttributeError()
