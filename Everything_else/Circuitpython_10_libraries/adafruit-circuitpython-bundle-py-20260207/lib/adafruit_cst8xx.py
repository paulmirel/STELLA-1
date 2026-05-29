# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_cst8xx`
================================================================================

CST8xx capacitive touch driver for CircuitPython


* Author(s): Melissa LeBlanc-Williams, ladyada

Implementation Notes
--------------------

**Hardware:**

* Round RGB 666 TTL TFT Display - 2.1" 480x480 - Capacitive Touch - TL021WVC02CT-B1323
  <http://www.adafruit.com/product/5792>`_ (Product ID: 5792)

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

# * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

# imports
import struct

from adafruit_bus_device.i2c_device import I2CDevice
from micropython import const

try:
    from typing import List
except ImportError:
    pass

__version__ = "1.1.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_CST8XX.git"


_CST_DEFAULT_I2C_ADDR = 0x15
_CST_REG_NUMTOUCHES = const(0x02)
_CST_REG_TOUCHDATA = const(0x03)
_CST_REG_SLEEP = const(0xA5)
_CST_REG_FIRMVERS = const(0xA6)
_CST_REG_CHIPID_816 = const(0xA7)
_CST_REG_MODID = const(0xA8)
_CST_REG_PROJID = const(0xA9)
_CST_REG_CHIPTYPE = const(0xAA)

_CHIP_ID_CST826 = const(0x11)
_CHIP_ID_CST836 = const(0x13)

# Untested Chip IDs which may use different registers
# If future chips do use different registers, it would be best to
# subclass each one and override the register constants
_CHIP_ID_CST816S = const(0xB4)
_CHIP_ID_CST816T = const(0xB5)
_CHIP_ID_CST816D = const(0xB6)
_CHIP_ID_CST820 = const(0xB7)

EVENTS = ("PRESS", "RELEASE", "TOUCHING")


class Adafruit_CST8XX:
    """
    A driver for the CST8XX Series capacitive touch sensors.
    """

    def __init__(self, i2c, address=_CST_DEFAULT_I2C_ADDR, debug=False, irq_pin=None):
        self._i2c = I2CDevice(i2c, address)
        self._debug = debug
        self._irq_pin = irq_pin

        chip_data = self._read(_CST_REG_FIRMVERS, 6)  # don't wait for IRQ
        # print("chip_data: {%x}".format(chip_data))
        if debug:
            fw_version, _, _, chip_type = struct.unpack("<HBBH", chip_data)
            print(f"fw_version: {fw_version:02X}, chip_type: {chip_type:02X}")

        if chip_data[1] in {_CHIP_ID_CST816S, _CHIP_ID_CST816T, _CHIP_ID_CST816D}:
            # this is a CST816x
            if debug:
                print("CST816 chip found")
        elif chip_data[5] in {_CHIP_ID_CST826}:
            # this is a CST826
            if debug:
                print("CST826 chip found")
        elif chip_data[5] in {_CHIP_ID_CST836}:
            # this is a CST826
            if debug:
                print("CST836 chip found")
        else:
            raise RuntimeError("Did not find supported CST8XX chip")

    @property
    def touched(self) -> int:
        """Returns the number of touches currently detected"""
        return self._read(_CST_REG_NUMTOUCHES, 1, irq_pin=self._irq_pin)[0]

    @property
    def touches(self) -> List[dict]:
        """
        Returns a list of touchpoint dicts, with 'x' and 'y' containing the
        touch coordinates, and 'id' as the touch # for multitouch tracking
        """
        touchpoints = []
        touchcount = self.touched

        if touchcount:
            data = self._read(_CST_REG_TOUCHDATA, touchcount * 6, irq_pin=self._irq_pin)

            if self._debug:
                print(f"touchcount: {touchcount}")

            for i in range(touchcount):
                point_data = data[i * 6 : i * 6 + 6]
                if all(i == 255 for i in point_data):
                    continue
                # print([hex(i) for i in point_data])
                x, y, _weight, _misc = struct.unpack(">HHBB", point_data)
                # Weight/misc might be for gesture info
                # print(x, y, _weight, _misc)
                event_id = x >> 14
                touch_id = y >> 12
                x &= 0x0FFF
                y &= 0x0FFF
                point = {"x": x, "y": y, "touch_id": touch_id, "event_id": event_id}
                if self._debug:
                    print(f"touch_id: {touch_id}, x: {x}, y: {y}, event: {EVENTS[event_id]}")
                touchpoints.append(point)
        return touchpoints

    def _read(self, register, length, irq_pin=None) -> bytearray:
        """Returns an array of 'length' bytes from the 'register'"""
        with self._i2c as i2c:
            if irq_pin is not None:
                while irq_pin.value:
                    pass

            i2c.write(bytes([register & 0xFF]))
            result = bytearray(length)

            i2c.readinto(result)
            if self._debug:
                print(f"\t${register:02X} => {[hex(i) for i in result]}")
            return result

    def _write(self, register, values) -> None:
        """Writes an array of 'length' bytes to the 'register'"""
        with self._i2c as i2c:
            values = [(v & 0xFF) for v in [register] + values]
            print(f"register: {values[0]:02X}, value: {values[1]:02X}")
            i2c.write(bytes(values))

            if self._debug:
                print(f"\t${values[0]:02X} <= {[hex(i) for i in values[1:]]}")
