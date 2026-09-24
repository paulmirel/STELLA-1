# SPDX-FileCopyrightText: 2016 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_register.i2c_struct`
====================================================

Generic structured registers based on `struct`

* Author(s): Scott Shawcroft
"""

__version__ = "1.13.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Register.git"

import struct

try:
    from typing import Any, NoReturn, Optional, Tuple, Type

    from circuitpython_typing.device_drivers import I2CDeviceDriver
except ImportError:
    pass

from adafruit_register import _BUFFER, _fit


class Struct:
    """
    Arbitrary structure register that is readable and writeable.

    Values are tuples that map to the values in the defined struct.  See struct
    module documentation for struct format string and its possible value types.

    :param int register_address: The register address to read the bit from
    :param str struct_format: The struct format string for this register.
    """

    def __init__(self, register_address: int, struct_format: str) -> None:
        self.format = struct_format
        self.address = register_address
        self.size = struct.calcsize(self.format)
        _fit(self.size)

    def __get__(
        self,
        obj: Optional[I2CDeviceDriver],
        objtype: Optional[Type[I2CDeviceDriver]] = None,
    ) -> Tuple:
        _BUFFER[0] = self.address
        with obj.i2c_device as i2c:
            i2c.write_then_readinto(_BUFFER, _BUFFER, out_end=1, in_start=1, in_end=1 + self.size)
        return struct.unpack_from(self.format, memoryview(_BUFFER)[1:])

    def __set__(self, obj: I2CDeviceDriver, value: Tuple) -> None:
        _BUFFER[0] = self.address
        struct.pack_into(self.format, _BUFFER, 1, *value)
        with obj.i2c_device as i2c:
            i2c.write(_BUFFER, end=1 + self.size)


class UnaryStruct:
    """
    Arbitrary single value structure register that is readable and writeable.

    Values map to the first value in the defined struct.  See struct
    module documentation for struct format string and its possible value types.

    :param int register_address: The register address to read the bit from
    :param str struct_format: The struct format string for this register.
    """

    def __init__(self, register_address: int, struct_format: str) -> None:
        self.format = struct_format
        self.address = register_address
        self.size = struct.calcsize(self.format)
        _fit(self.size)

    def __get__(
        self,
        obj: Optional[I2CDeviceDriver],
        objtype: Optional[Type[I2CDeviceDriver]] = None,
    ) -> Any:
        _BUFFER[0] = self.address
        with obj.i2c_device as i2c:
            i2c.write_then_readinto(_BUFFER, _BUFFER, out_end=1, in_start=1, in_end=1 + self.size)
        return struct.unpack_from(self.format, _BUFFER, 1)[0]

    def __set__(self, obj: I2CDeviceDriver, value: Any) -> None:
        _BUFFER[0] = self.address
        struct.pack_into(self.format, _BUFFER, 1, value)
        with obj.i2c_device as i2c:
            i2c.write(_BUFFER, end=1 + self.size)


class ROUnaryStruct(UnaryStruct):
    """
    Arbitrary single value structure register that is read-only.

    Values map to the first value in the defined struct.  See struct
    module documentation for struct format string and its possible value types.

    :param int register_address: The register address to read the bit from
    :param type struct_format: The struct format string for this register.
    """

    def __set__(self, obj: I2CDeviceDriver, value: Any) -> NoReturn:
        raise AttributeError()
