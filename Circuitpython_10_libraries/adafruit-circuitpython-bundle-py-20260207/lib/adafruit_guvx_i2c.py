# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_guvx_i2c`
================================================================================

Python drivers for the GUVA-C32SM and GUVB-C31SM I2C UV sensors


* Author(s): ladyada

Implementation Notes
--------------------

**Hardware:**

* `GUVx UV light sensor <http://www.adafruit.com/products/5609>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import time

from adafruit_bus_device import i2c_device
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from micropython import const

try:
    import typing

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.12"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_GUVX_I2C.git"


_GUVXI2C_I2CADDR_DEFAULT: int = const(0x39)  # Default I2C address
_GUVXI2C_CHIP_ID = const(0x62)

_GUVXI2C_REG_CHIPID = const(0x00)
_GUVXI2C_REG_MODE = const(0x01)
_GUVXI2C_REG_RESUV = const(0x04)
_GUVXI2C_REG_RANGEUVA = const(0x05)
_GUVXI2C_REG_RANGEUVB = const(0x07)
_GUVXI2C_REG_MODECTL = const(0x0A)
_GUVXI2C_REG_RESET = const(0x0B)
_GUVXI2C_REG_UVALSB = const(0x15)
_GUVXI2C_REG_UVBLSB = const(0x17)
_GUVXI2C_REG_NVMCTRL = const(0x30)
_GUVXI2C_REG_NVMMSB = const(0x31)
_GUVXI2C_REG_NVMLSB = const(0x32)

# four power modes!
GUVXI2C_PMODE_NORMAL = const(0x00)
GUVXI2C_PMODE_LOWPOWER = const(0x01)
GUVXI2C_PMODE_AUTOSHUT = const(0x02)
GUVXI2C_PMODE_SHUTDOWN = const(0x03)

# valid measure periods
_measure_periods = (800, 400, 200, 100)

# valid measure ranges
_measure_ranges = (1, 2, 4, 8, 16, 32, 64, 128)

# valid sleep durations
_sleep_durations = (2, 4, 8, 16, 32, 64, 128, 256)


class GUVX_I2C:
    """Base driver for the GUVA or GUVB I2C UV light sensor.

    :param ~busio.I2C i2c_bus: The I2C bus the  GUVX is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x39`
    """

    _chip_id = ROUnaryStruct(_GUVXI2C_REG_CHIPID, "<B")
    _reset = UnaryStruct(_GUVXI2C_REG_RESET, "<B")
    _oper = RWBits(2, _GUVXI2C_REG_MODE, 4)
    _pmode = RWBits(2, _GUVXI2C_REG_MODE, 0)
    _period = RWBits(2, _GUVXI2C_REG_RESUV, 0)  # only 2 bottom bits used!!!
    _sleep_duration = RWBits(2, _GUVXI2C_REG_MODECTL, 4)
    _range_uvb = RWBits(3, _GUVXI2C_REG_RANGEUVB, 0)
    _range_uva = RWBits(3, _GUVXI2C_REG_RANGEUVA, 0)
    _nvm_ctrl = UnaryStruct(_GUVXI2C_REG_NVMCTRL, "<B")
    _nvm_data = ROUnaryStruct(_GUVXI2C_REG_NVMMSB, ">H")  # note endianness

    _uvb = ROUnaryStruct(_GUVXI2C_REG_UVBLSB, "<H")
    _uva = ROUnaryStruct(_GUVXI2C_REG_UVALSB, "<H")

    def __init__(self, i2c_bus: I2C, address: int = _GUVXI2C_I2CADDR_DEFAULT) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
        if self._chip_id != _GUVXI2C_CHIP_ID:
            raise RuntimeError("Failed to find GUVX I2C sensor - check your wiring!")

        self.reset()

        self.uv_mode = True  # turn on UV reading!
        self.power_mode = GUVXI2C_PMODE_NORMAL  # put into normal power
        self.measure_period = 100  # set default measure period 100ms
        self.range = 8  # set default range 8x

        self._nvm_ctrl = 0x0A  # read offset first
        self._offset = self._nvm_data
        self._nvm_ctrl = 0x0B  # read B_Scale second
        self._scale = self._nvm_data

    def reset(self) -> None:
        """Perform a soft reset"""
        # It should be noted that applying SOFT_RESET should be done only
        # when POWER_MODE=��00��.
        self.power_mode = GUVXI2C_PMODE_NORMAL
        self._reset = 0xA5  # special reset signal
        time.sleep(0.05)

    @property
    def uv_mode(self) -> bool:
        """Whether or not UV-reading mode is enabled"""
        return self._oper == 2  # see datasheet table 7.2

    @uv_mode.setter
    def uv_mode(self, enabled: bool) -> None:
        # see datasheet table 7.2
        if enabled:
            self._oper = 2
        else:
            self._oper = 0

    @property
    def power_mode(self) -> int:
        """One of four power modes available:

        GUVXI2C_PMODE_NORMAL, GUVXI2C_PMODE_LOWPOWER, GUVXI2C_PMODE_AUTOSHUT,
        or GUVXI2C_PMODE_SHUTDOWN
        """
        return self._pmode

    @power_mode.setter
    def power_mode(self, mode: int) -> None:
        # see datasheet table 7.3
        if mode not in {
            GUVXI2C_PMODE_NORMAL,
            GUVXI2C_PMODE_LOWPOWER,
            GUVXI2C_PMODE_AUTOSHUT,
            GUVXI2C_PMODE_SHUTDOWN,
        }:
            raise RuntimeError("Invalid power mode")
        self._pmode = mode

    @property
    def measure_period(self) -> int:
        """One of four measuring periods in milliseconds:

        100, 200, 400 or 800ms
        """
        return _measure_periods[self._period]

    @measure_period.setter
    def measure_period(self, period: int) -> None:
        # see datasheet table 7.4
        if period not in _measure_periods:
            raise RuntimeError("Invalid period: must be 100, 200, 400 or 800 (ms)")
        self._period = _measure_periods.index(period)

    @property
    def sleep_duration(self) -> int:
        """Sleep duration in low power mode, can be:

        2, 4, 8, 16, 32, 64, 128, or 256 times
        """
        return _sleep_durations[self._sleep_duration]

    @sleep_duration.setter
    def sleep_duration(self, duration: int) -> None:
        # see datasheet table 7.7
        if duration not in _sleep_durations:
            raise RuntimeError("Invalid range: must be 2, 4, 8, 16, 32, 64, 128 or 256 x")
        self._sleep_duration = _sleep_durations.index(duration)


class GUVB_C31SM(GUVX_I2C):
    """Driver for the GUVB-C31SM sensor"""

    @property
    def range(self) -> int:
        """UVB range, can be: 1, 2, 4, 8, 16, 32, 64, or 128 times"""
        return _measure_ranges[self._range_uvb]

    @range.setter
    def range(self, multiple: int) -> None:
        # see datasheet table 7.6
        if multiple not in _measure_ranges:
            raise RuntimeError("Invalid range: must be 1, 2, 4, 8, 16, 32, 64, or 128 x")
        self._range_uvb = _measure_ranges.index(multiple)

    @property
    def uvb(self) -> int:
        """The raw UV B 16-bit data"""
        return self._uvb

    @property
    def uv_index(self) -> float:
        """Calculated using offset and b-scale"""
        # GUVB-C31SM UVI = (B value *0.8 )/(B_scale) in app note
        return (self.uvb / self.range * 0.8) / self._scale


class GUVA_C32SM(GUVX_I2C):
    """Driver for the GUVA-C32SM sensor

    Note: untested!
    """

    @property
    def range(self) -> int:
        """UVB range, can be: 1, 2, 4, 8, 16, 32, 64, or 128 times"""
        return _measure_ranges[self._range_uva]

    @range.setter
    def range(self, multiple: int) -> None:
        # see datasheet table 7.6
        if multiple not in _measure_ranges:
            raise RuntimeError("Invalid range: must be 1, 2, 4, 8, 16, 32, 64, or 128 x")
        self._range_uva = _measure_ranges.index(multiple)

    @property
    def uva(self) -> int:
        """The raw UV A 16-bit data"""
        return self._uva

    @property
    def uv_index(self) -> float:
        """Calculated using offset and b-scale"""
        # GUVA-C32SM UVI = (A value * 2.5 - self._offset )/(A_scale)
        # in app note
        return ((self.uva / self.range * 2.5) - self._offset) / self._scale
