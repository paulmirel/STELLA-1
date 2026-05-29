# SPDX-FileCopyrightText: Copyright (c) 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Written by Liz Clark (Adafruit Industries) with OpenAI ChatGPT v4 September 25, 2023 build
# https://help.openai.com/en/articles/6825453-chatgpt-release-notes

# https://chat.openai.com/share/f4f94c37-66a1-42d9-879b-9624c13f3e26
"""
`adafruit_vcnl4020`
================================================================================

Driver for the VCNL4020 proximity and light sensor


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* Adafruit VCNL4020 Proximity and Light Sensor <https://www.adafruit.com/product/5810>

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_register.i2c_bit import ROBit, RWBit
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_struct import ROUnaryStruct, Struct
from micropython import const

try:
    import typing

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.6"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_VCNL4020.git"

_I2C_ADDRESS = const(0x13)
_REG_COMMAND = const(0x80)
_REG_PRODUCT_ID = const(0x81)
_REG_PROX_RATE = const(0x82)
_REG_IR_LED_CURRENT = const(0x83)
_REG_AMBIENT_PARAM = const(0x84)
_REG_AMBIENT_RESULT_HIGH = const(0x85)
_REG_AMBIENT_RESULT_LOW = const(0x86)
_REG_PROX_RESULT_HIGH = const(0x87)
_REG_PROX_RESULT_LOW = const(0x88)
_REG_INT_CTRL = const(0x89)
_REG_LOW_THRES_HIGH = const(0x8A)
_REG_LOW_THRES_LOW = const(0x8B)
_REG_HIGH_THRES_HIGH = const(0x8C)
_REG_HIGH_THRES_LOW = const(0x8D)
_REG_INT_STATUS = const(0x8E)
_REG_PROX_ADJUST = const(0x8F)
_INT_TH_HI = const(0x01)
_INT_TH_LOW = const(0x02)
_INT_ALS_READY = const(0x04)
_INT_PROX_READY = const(0x08)


class Adafruit_VCNL4020:
    """Adafruit VCNL4020 Proximity/Ambient Light sensor driver"""

    auto_offset_comp = RWBit(_REG_AMBIENT_PARAM, 3)
    """Auto offset compensation for ambient light measurement."""
    _command_reg = RWBits(8, _REG_COMMAND, 0)
    continuous_conversion = RWBit(_REG_AMBIENT_PARAM, 7)
    """Continuous conversion mode for ambient light measurement."""
    _int_ctrl_reg = RWBits(8, _REG_INT_CTRL, 0)
    _int_status_reg = RWBits(3, _REG_INT_STATUS, 0)
    _led_current = RWBits(6, _REG_IR_LED_CURRENT, 0)
    _product_revision = ROUnaryStruct(_REG_PRODUCT_ID, "<B")
    lux = ROUnaryStruct(_REG_AMBIENT_RESULT_HIGH, ">H")
    """Reads the ambient light/lux sensor (ALS) measurement result"""
    _lux_averaging = RWBits(3, _REG_AMBIENT_PARAM, 0)
    lux_enabled = RWBit(_REG_COMMAND, 2)
    """Enable/disable lux sensor"""
    lux_on_demand = RWBit(_REG_COMMAND, 4)
    """On-demand setting for lux measurements"""
    _lux_rate = RWBits(3, _REG_AMBIENT_PARAM, 4)
    lux_ready = ROBit(_REG_COMMAND, 6)
    """Status of ambient light data"""
    proximity = ROUnaryStruct(_REG_PROX_RESULT_HIGH, ">H")
    """Reads the proximity measurement result"""
    proximity_enabled = RWBit(_REG_COMMAND, 1)
    """Enable/disable proximity sensor"""
    _proximity_frequency = RWBits(2, _REG_PROX_ADJUST, 3)
    proximity_on_demand = RWBit(_REG_COMMAND, 3)
    """On-demand setting for proximity measurements"""
    _proximity_rate = RWBits(3, _REG_PROX_RATE, 0)
    proximity_ready = ROBit(_REG_COMMAND, 5)
    """Status of proximity data."""
    low_threshold = Struct(_REG_LOW_THRES_HIGH, ">H")
    """Sets the low threshold for proximity measurement"""
    high_threshold = Struct(_REG_HIGH_THRES_HIGH, ">H")
    """Sets the high threshold for proximity measurement."""
    _interrupt_count = RWBits(3, _REG_INT_CTRL, 5)
    proximity_interrupt = RWBit(_REG_INT_CTRL, 3)
    """Enable/disable proximity interrupt"""
    lux_interrupt = RWBit(_REG_INT_CTRL, 2)
    """Enable/disable lux interrupt"""
    high_threshold_interrupt = RWBit(_REG_INT_CTRL, 1)
    """Enable/disable proximity high threshold interrupt"""
    low_threshold_interrupt = RWBit(_REG_INT_CTRL, 0)
    """Enable/disable proximity low threshold interrupt"""
    selftimed_enabled = RWBit(_REG_COMMAND, 0)
    """Enable/disable selftimed reading"""

    _proximity_rates = [1.95, 3.9, 7.8, 16.6, 31.2, 62.5, 125, 250]
    _lux_rates = [1, 2, 3, 4, 5, 6, 8, 10]
    _avg_samples = [1, 2, 4, 8, 16, 32, 64, 128]
    _int_counts = [1, 2, 4, 8, 16, 32, 64, 128]
    _proximity_frequencies = [390.625, 781.25, 1.5625, 3.125]

    def __init__(self, i2c: I2C, addr: int = _I2C_ADDRESS) -> None:
        """
        Initializes the VCNL4020 sensor and checks for a valid Product ID Revision.
        :param i2c: The I2C interface to use
        :param addr: The I2C address of the VCNL4020, defaults to _I2C_ADDRESS
        """
        self.i2c_device = I2CDevice(i2c, addr)

        # Check the Product ID Revision
        if self._product_revision != 0x21:
            raise RuntimeError(f"Invalid Product ID Revision {self._product_revision}")
        try:
            # Configuration settings
            self.proximity_rate = 250
            self.led_current = 200
            self.lux_rate = 10
            self.lux_averaging = 1
        except Exception as error:
            raise RuntimeError(f"Failed to initialize: {error}") from error

    @property
    def _enable(self) -> bool:
        return self.lux_enabled and self.proximity_enabled and self.selftimed_enabled

    @_enable.setter
    def _enable(self, value: bool) -> None:
        self.lux_enabled = value
        self.proximity_enabled = value
        self.selftimed_enabled = value

    @property
    def clear_interrupts(self) -> None:
        """
        Clears the interrupt flags.

        :param value: True to clear all interrupt flags.
        """
        clear_bits = 0
        clear_bits |= _INT_PROX_READY
        clear_bits |= _INT_ALS_READY
        clear_bits |= _INT_TH_LOW
        clear_bits |= _INT_TH_HI
        self._int_status_reg |= clear_bits

    @property
    def interrupt_count(self) -> int:
        """
        Interrupt count setting

        :rtype: int
        """
        return self._int_counts[self._interrupt_count]

    @interrupt_count.setter
    def interrupt_count(self, value: int) -> None:
        self._enable = False
        if value not in self._int_counts:
            raise ValueError(
                f"Invalid interrupt count: {value}. Available counts: {self._int_counts}"
            )
        count = self._int_counts.index(value)
        self._interrupt_count = count
        self._enable = True

    @property
    def led_current(self) -> int:
        """
        The LED current for proximity mode in mA.

        :return: The LED current in mA.
        """
        return self._led_current * 10

    @led_current.setter
    def led_current(self, value: int) -> None:
        self._enable = False
        self._led_current = value // 10
        self._enable = True

    @property
    def lux_averaging(self) -> int:
        """
        Ambient averaging sample rate

        :rtype: int
        """
        return self._avg_samples[self._lux_averaging]

    @lux_averaging.setter
    def lux_averaging(self, value: int) -> None:
        self._enable = False
        if value not in self._avg_samples:
            raise ValueError(
                f"Invalid sample rate: {value}. Available sample rates: {self._avg_samples}"
            )
        sample_rate = self._avg_samples.index(value)
        self._lux_averaging = sample_rate
        self._enable = True

    @property
    def lux_rate(self) -> int:
        """
        Ambient light measurement rate

        :rtype: int
        """
        return self._lux_rates[self._lux_rate]

    @lux_rate.setter
    def lux_rate(self, value: int) -> None:
        self._enable = False
        if value not in self._lux_rates:
            raise ValueError(f"Invalid ambient rate: {value}. Available rates: {self._lux_rates}")
        rate = self._lux_rates.index(value)
        self._lux_rate = rate
        self._enable = True

    @property
    def proximity_frequency(self) -> int:
        """
        Proximity frequency setting

        :rtype: int
        """
        return self._proximity_frequencies[self._proximity_frequency]

    @proximity_frequency.setter
    def proximity_frequency(self, value: int) -> None:
        self._enable = False
        if value not in self._proximity_frequencies:
            raise ValueError(
                f"Invalid frequency: {value}. Available frequencies: {self._proximity_frequencies}"
            )
        freq = self._proximity_frequencies.index(value)
        self._proximity_frequency = freq
        self._enable = True

    @property
    def proximity_rate(self) -> int:
        """
        Proximity measurement rate

        :rtype: int
        """
        return self._proximity_rates[self._proximity_rate]

    @proximity_rate.setter
    def proximity_rate(self, value: int) -> None:
        self._enable = False
        if value not in self._proximity_rates:
            raise ValueError(
                f"Invalid proximity rate: {value}. Available rates: {self._proximity_rates}"
            )
        rate = self._proximity_rates.index(value)
        self._proximity_rate = rate
        self._enable = True
