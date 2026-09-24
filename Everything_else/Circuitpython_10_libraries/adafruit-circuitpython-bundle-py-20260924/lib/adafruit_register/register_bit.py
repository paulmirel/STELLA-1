# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_register.register_bit`
====================================================

Single bit registers that use RegisterAccessor

* Author(s): Tim Cocks

"""

__version__ = "1.13.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Register.git"

from adafruit_register import _BUFFER, _fit


class RWBit:
    """
    Single bit register that is readable and writeable.

    Values are `bool`

    :param int register_address: The register address to read the bit from
    :param int bit: The bit index within the byte at ``register_address``
    :param int register_width: The number of bytes in the register. Defaults to 1.
    :param bool lsb_first: Is the first byte we read from spi the LSB? Defaults to true

    """

    def __init__(
        self, register_address: int, bit: int, register_width: int = 1, lsb_first: bool = True
    ):
        self.bit_mask = 1 << (bit % 8)  # the bitmask *within* the byte!
        self.address = register_address
        self.register_width = register_width  # replaces the per-instance self.buffer
        self.lsb_first = lsb_first
        self.bit_index = bit
        if lsb_first:
            self.byte = bit // 8  # Little-endian: bit 0 in first register byte
        else:
            self.byte = register_width - 1 - (bit // 8)  # Big-endian: bit 0 in last register byte
        _fit(register_width)

    def __get__(self, obj, objtype=None):
        # read data from register (memoryview bounds the transfer to this register's width)
        data = memoryview(_BUFFER)[: self.register_width]
        obj.register_accessor.read_register(self.address, data)
        # check specified bit and return boolean
        return bool(data[self.byte] & self.bit_mask)

    def __set__(self, obj, value):
        # read current data from register
        data = memoryview(_BUFFER)[: self.register_width]
        obj.register_accessor.read_register(self.address, data)
        # update current data with new value
        if value:
            data[self.byte] |= self.bit_mask
        else:
            data[self.byte] &= ~self.bit_mask
        # write updated data to register
        obj.register_accessor.write_register(self.address, data)


class ROBit(RWBit):
    """Single bit register that is read only. Subclass of `RWBit`.

    Values are `bool`

    :param int register_address: The register address to read the bit from
    :param type bit: The bit index within the byte at ``register_address``
    :param int register_width: The number of bytes in the register. Defaults to 1.

    """

    def __set__(self, obj, value):
        raise AttributeError()
