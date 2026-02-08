# SPDX-FileCopyrightText: Copyright (c) 2022 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_ltr329_ltr303`
================================================================================

Python driver for LTR-329 and LTR-303 ight sensor


* Author(s): ladyada

Implementation Notes
--------------------

**Hardware:**

* `LTR-329/303 <http://www.adafruit.com/products/5591>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import time

from adafruit_bus_device import i2c_device
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from micropython import const

try:
    from typing import Tuple

    from busio import I2C
except ImportError:
    pass

__version__ = "3.0.12"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_LTR329_LTR303.git"

_LTR329_I2CADDR_DEFAULT: int = const(0x29)  # Default I2C address

# These registers on both LTR-329 and LTR-303
_LTR329_REG_ALS_CONTR = const(0x80)
_LTR329_REG_ALS_MEASRATE = const(0x85)
_LTR329_REG_PARTID = const(0x86)
_LTR329_REG_MANUID = const(0x87)
_LTR329_REG_CHANNEL1 = const(0x88)
_LTR329_REG_CHANNEL0 = const(0x8A)
_LTR329_REG_STATUS = const(0x8C)
# These registers on LTR-303 only!
_LTR303_REG_INTERRUPT = const(0x8F)
_LTR303_REG_THRESHHIGH_LSB = const(0x97)
_LTR303_REG_THRESHLOW_LSB = const(0x99)
_LTR303_REG_INTPERSIST = const(0x9E)

# valid ALS gains
_als_gains = (1, 2, 4, 8, None, None, 48, 96)
# valid integration times
_integration_times = (100, 50, 200, 400, 150, 250, 300, 350)
# valid measurement rates
_measurement_rates = (50, 100, 200, 500, 1000, 2000, 2000, 2000)


class LTR329:
    """Base driver for the LTR-329 light sensor.

    :param ~busio.I2C i2c_bus: The I2C bus the sensor is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x29`
    """

    part_id = ROUnaryStruct(_LTR329_REG_PARTID, "<B")
    manufacturer_id = ROUnaryStruct(_LTR329_REG_MANUID, "<B")
    # both channels must be read at once!
    _light_data = ROUnaryStruct(_LTR329_REG_CHANNEL1, "<I")
    # Control register bits
    _reset = RWBit(_LTR329_REG_ALS_CONTR, 1)
    _als_gain = RWBits(3, _LTR329_REG_ALS_CONTR, 2)
    active_mode = RWBit(_LTR329_REG_ALS_CONTR, 0)
    # measurement rate register bits
    _integration_time = RWBits(3, _LTR329_REG_ALS_MEASRATE, 3)
    _measurement_rate = RWBits(3, _LTR329_REG_ALS_MEASRATE, 0)
    # status register bits
    als_data_invalid = RWBit(_LTR329_REG_STATUS, 7)
    _als_data_gain_range = RWBits(3, _LTR329_REG_STATUS, 4)
    new_als_data_available = RWBit(_LTR329_REG_STATUS, 2)

    def __init__(self, i2c: I2C, address: int = _LTR329_I2CADDR_DEFAULT) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c, address)
        if self.part_id != 0xA0 or self.manufacturer_id != 0x05:
            raise RuntimeError("Unable to find LTR-329, check your wiring")
        self.reset()
        self.active_mode = True

    def reset(self) -> None:
        """Reset the sensor to the default state set by the library"""
        self._reset = True
        time.sleep(0.010)

    @property
    def als_gain(self) -> int:
        """ALS gain, can be: 1, 2, 4, 8, 48 or 96 times"""
        return _als_gains[self._als_gain]

    @als_gain.setter
    def als_gain(self, gain: int) -> None:
        if not gain in _als_gains:
            raise RuntimeError("Invalid gain: must be 1, 2, 4, 8, 48 or 96 x")
        self._als_gain = _als_gains.index(gain)

    @property
    def als_data_gain(self) -> int:
        """ALS gain for data that is being read now,
        can be: 1, 2, 4, 8, 48 or 96 times"""
        return _als_gains[self._als_data_gain_range]

    @property
    def integration_time(self) -> int:
        """ALS integration times, can be: 50, 100, 150, 200, 250,
        300, 350, or 400 milliseconds"""
        return _integration_times[self._integration_time]

    @integration_time.setter
    def integration_time(self, int_time: int) -> None:
        if not int_time in _integration_times:
            raise RuntimeError(
                "Invalid integration time: must be 50, 100, 150, "
                "200, 250, 300, 350, or 400 milliseconds"
            )
        self._integration_time = _integration_times.index(int_time)

    @property
    def measurement_rate(self) -> int:
        """ALS measurement rate, must be = or > than ALS integration rate!
        Can be: 50, 100, 200, 500, 1000, or 2000 milliseconds"""
        return _measurement_rates[self._measurement_rate]

    @measurement_rate.setter
    def measurement_rate(self, rate: int) -> None:
        if not rate in _measurement_rates:
            raise RuntimeError(
                "Invalid measurement rate: must be 50, 100, 200, 500, 1000, or 2000 milliseconds"
            )
        self._measurement_rate = _measurement_rates.index(rate)

    def throw_out_reading(self) -> None:
        """Throw out a reading (typically done to clear it out)"""
        _ = self._light_data

    @property
    def light_channels(self) -> Tuple[int, int]:
        """A data pair of both visible+IR light, and the IR-only light"""
        temp = self._light_data
        if self.als_data_invalid:
            raise ValueError("Data invalid / over-run!")
        return (temp >> 16, temp & 0xFFFF)

    @property
    def visible_plus_ir_light(self) -> int:
        """The visible + IR light data"""
        if self.als_data_invalid:
            _ = self._light_data  # read data to clear it out
            raise ValueError("Data invalid / over-run!")
        return self._light_data >> 16

    @property
    def ir_light(self) -> int:
        """The IR light data"""
        if self.als_data_invalid:
            _ = self._light_data  # read data to clear it out
            raise ValueError("Data invalid / over-run!")
        return self._light_data & 0xFFFF


class LTR303(LTR329):
    """Base driver for the LTR-303 light sensor, basically an LTR-329 with INT out

    :param ~busio.I2C i2c_bus: The I2C bus the sensor is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x29`
    """

    _enable_int = RWBit(_LTR303_REG_INTERRUPT, 1)
    _int_polarity = RWBit(_LTR303_REG_INTERRUPT, 2)
    # The high and low int thresholds
    threshold_high = UnaryStruct(_LTR303_REG_THRESHHIGH_LSB, "<H")
    threshold_low = UnaryStruct(_LTR303_REG_THRESHLOW_LSB, "<H")

    _int_persistence = RWBits(4, _LTR303_REG_INTPERSIST, 0)

    @property
    def int_persistence(self) -> int:
        """How long the data needs to be high/low to generate an interrupt.
        Setting of 1 means 'every measurement', 2 means "two in a row", etc
        up to 16
        """
        return self._int_persistence + 1

    @int_persistence.setter
    def int_persistence(self, counts: int) -> None:
        if not 1 <= counts <= 16:
            raise ValueError("Persistence counts must be 1-16")
        self._int_persistence = counts - 1

    @property
    def enable_int(self) -> bool:
        """Enable the interrupt functionality."""
        return self._enable_int

    @enable_int.setter
    def enable_int(self, enable: bool) -> None:
        # we must be in non-active mode to change this register!
        curr_mode = self.active_mode
        self.active_mode = False
        # now change the bit...
        self._enable_int = enable
        # and reset the mode
        self.active_mode = curr_mode

    @property
    def int_polarity(self) -> bool:
        """The polarity of the interrupt (whether high or low is "active")"""
        return self._int_polarity

    @int_polarity.setter
    def int_polarity(self, pol: bool) -> None:
        # we must be in non-active mode to change this register!
        curr_mode = self.active_mode
        self.active_mode = False
        # now change the bit...
        self._int_polarity = pol
        # and reset the mode
        self.active_mode = curr_mode
