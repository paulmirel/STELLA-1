# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_tcs3430`
================================================================================

CircuitPython driver library for AMS TCS3430 / TCS34303 XYZ tri-stimulus color sensor.


* Author(s): Tim Cocks

Implementation Notes
--------------------

**Hardware:**

* `Adafruit TCS3430 / TCS34303 Ambient Tri-Stimulus Color Sensor <https://www.adafruit.com/product/6479>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

# * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
# * Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

__version__ = "1.0.3"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_TCS3430.git"

# imports
import time

from adafruit_bus_device import i2c_device
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import ROBits, RWBits
from adafruit_register.i2c_struct import UnaryStruct
from micropython import const

try:
    from typing import Tuple

    import busio
except ImportError:
    pass

# -----------------------------------------------------------------------
# I2C address
# -----------------------------------------------------------------------
_TCS3430_DEFAULT_ADDR = const(0x39)

# -----------------------------------------------------------------------
# Register addresses
# -----------------------------------------------------------------------
_TCS3430_REG_ENABLE = const(0x80)  # Enable states and interrupts
_TCS3430_REG_ATIME = const(0x81)  # ADC integration time
_TCS3430_REG_WTIME = const(0x83)  # ALS wait time
_TCS3430_REG_AILTL = const(0x84)  # ALS interrupt low threshold (16-bit LE)
_TCS3430_REG_AIHTL = const(0x86)  # ALS interrupt high threshold (16-bit LE)
_TCS3430_REG_PERS = const(0x8C)  # ALS interrupt persistence filters
_TCS3430_REG_CFG0 = const(0x8D)  # Configuration register 0
_TCS3430_REG_CFG1 = const(0x90)  # Configuration register 1
_TCS3430_REG_REVID = const(0x91)  # Revision ID
_TCS3430_REG_ID = const(0x92)  # Device ID
_TCS3430_REG_STATUS = const(0x93)  # Device status
_TCS3430_REG_CH0DATAL = const(0x94)  # Z channel data (16-bit LE)
_TCS3430_REG_CH1DATAL = const(0x96)  # Y channel data (16-bit LE)
_TCS3430_REG_CH2DATAL = const(0x98)  # IR1 channel data (16-bit LE)
_TCS3430_REG_CH3DATAL = const(0x9A)  # X or IR2 channel data (16-bit LE)
_TCS3430_REG_CFG2 = const(0x9F)  # Configuration register 2
_TCS3430_REG_CFG3 = const(0xAB)  # Configuration register 3
_TCS3430_REG_AZ_CONFIG = const(0xD6)  # Auto zero configuration
_TCS3430_REG_INTENAB = const(0xDD)  # Interrupt enables

# Expected chip ID
_TCS3430_CHIP_ID = const(0xDC)


# -----------------------------------------------------------------------
# CV helper – same pattern as adafruit_apds9999
# -----------------------------------------------------------------------
class CV:
    """Constant-value helper for enum-like classes."""

    @classmethod
    def is_valid(cls, value: int) -> bool:
        """Validate that *value* is a member of this CV class."""
        IGNORE = [cls.__module__, cls.__name__]
        return value in cls.__dict__.values() and value not in IGNORE

    @classmethod
    def get_name(cls, value: int) -> str:
        """Return the attribute name for *value*."""
        for k, v in cls.__dict__.items():
            if v == value:
                return k
        raise ValueError(f"Unknown value {value}")


# -----------------------------------------------------------------------
# Enum-like CV classes
# -----------------------------------------------------------------------
class ALSGain(CV):
    """ALS gain settings for CFG1 register bits 1:0.

    +-------------------------------+----------+
    | Setting                       | Gain     |
    +===============================+==========+
    | :py:const:`ALSGain.GAIN_1X`   | 1x gain  |
    +-------------------------------+----------+
    | :py:const:`ALSGain.GAIN_4X`   | 4x gain  |
    +-------------------------------+----------+
    | :py:const:`ALSGain.GAIN_16X`  | 16x gain |
    +-------------------------------+----------+
    | :py:const:`ALSGain.GAIN_64X`  | 64x gain |
    +-------------------------------+----------+
    | :py:const:`ALSGain.GAIN_128X` | 128x gain|
    +-------------------------------+----------+
    """

    GAIN_1X = 0x00
    GAIN_4X = 0x01
    GAIN_16X = 0x02
    GAIN_64X = 0x03
    GAIN_128X = 0x04  # Requires HGAIN bit in CFG2


class InterruptPersistence(CV):
    """ALS interrupt persistence filter values for PERS register bits 3:0.

    +----------------------------------------------+------------------------------------+
    | Setting                                      | Description                        |
    +==============================================+====================================+
    | :py:const:`InterruptPersistence.EVERY`       | Every ALS cycle                    |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_1`    | 1 consecutive value out of range   |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_2`    | 2 consecutive values out of range  |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_3`    | 3 consecutive values out of range  |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_5`    | 5 consecutive values out of range  |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_10`   | 10 consecutive values out of range |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_15`   | 15 consecutive values out of range |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_20`   | 20 consecutive values out of range |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_25`   | 25 consecutive values out of range |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_30`   | 30 consecutive values out of range |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_35`   | 35 consecutive values out of range |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_40`   | 40 consecutive values out of range |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_45`   | 45 consecutive values out of range |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_50`   | 50 consecutive values out of range |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_55`   | 55 consecutive values out of range |
    +----------------------------------------------+------------------------------------+
    | :py:const:`InterruptPersistence.CYCLES_60`   | 60 consecutive values out of range |
    +----------------------------------------------+------------------------------------+
    """

    EVERY = 0x00
    CYCLES_1 = 0x01
    CYCLES_2 = 0x02
    CYCLES_3 = 0x03
    CYCLES_5 = 0x04
    CYCLES_10 = 0x05
    CYCLES_15 = 0x06
    CYCLES_20 = 0x07
    CYCLES_25 = 0x08
    CYCLES_30 = 0x09
    CYCLES_35 = 0x0A
    CYCLES_40 = 0x0B
    CYCLES_45 = 0x0C
    CYCLES_50 = 0x0D
    CYCLES_55 = 0x0E
    CYCLES_60 = 0x0F


# -----------------------------------------------------------------------
# Driver class
# -----------------------------------------------------------------------
class TCS3430:
    """CircuitPython driver for the AMS TCS3430 XYZ Color and ALS Sensor.

    :param ~busio.I2C i2c_bus: The I2C bus the device is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x39`.
    """

    # -- ENABLE register (0x80) bits --
    power_on = RWBit(_TCS3430_REG_ENABLE, 0)  # PON
    """Power on/off the sensor. True for on, False for off."""

    als_enabled = RWBit(_TCS3430_REG_ENABLE, 1)  # AEN
    """Enable/disable ALS functionality"""

    wait_enabled = RWBit(_TCS3430_REG_ENABLE, 3)  # WEN
    """Enable/disable wait functionality"""

    # -- ATIME register (0x81) – full byte --
    integration_cycles = UnaryStruct(_TCS3430_REG_ATIME, "B")
    """The number of integration cycles (1-256)"""

    # -- WTIME register (0x83) – full byte --
    wait_cycles = UnaryStruct(_TCS3430_REG_WTIME, "B")
    """The number of wait cycles (1-256)"""

    # -- ALS interrupt thresholds (16-bit little-endian) --
    als_threshold_low = UnaryStruct(_TCS3430_REG_AILTL, "<H")
    """The low threshold value for ALS"""

    als_threshold_high = UnaryStruct(_TCS3430_REG_AIHTL, "<H")
    """The high threshold value for ALS"""

    # -- PERS register (0x8C), bits 3:0 --
    interrupt_persistence = RWBits(4, _TCS3430_REG_PERS, 0)
    """Enable/disable The interrupt persistence functionality"""

    # -- CFG0 register (0x8D) --
    wait_long = RWBit(_TCS3430_REG_CFG0, 2)  # WLONG
    """Enable/disable longer wait functionality. True to enable 12x time multiplier"""

    # -- CFG1 register (0x90) --
    _als_gain = RWBits(2, _TCS3430_REG_CFG1, 0)  # AGAIN bits 1:0
    als_mux_ir2 = RWBit(_TCS3430_REG_CFG1, 3)  # AMUX
    """ALS MUX setting for IR2 or X channel. True for IR2, False for X."""

    # -- REVID register (0x91) – read-only --
    rev_id = ROBits(8, _TCS3430_REG_REVID, 0)
    """Revision ID"""

    # -- ID register (0x92) – read-only --
    chip_id = ROBits(8, _TCS3430_REG_ID, 0)
    """Chip ID"""

    # -- STATUS register (0x93) --
    _status = UnaryStruct(_TCS3430_REG_STATUS, "B")
    _als_interrupt_status = ROBits(1, _TCS3430_REG_STATUS, 4)  # AINT
    _als_saturated_status = ROBits(1, _TCS3430_REG_STATUS, 7)  # ASAT

    # -- Individual Channel data (16-bit little-endian) --
    _channel_x_or_ir2 = UnaryStruct(_TCS3430_REG_CH3DATAL, "<H")  # CH3 = X or IR2

    # -- All 4 channels as a single 8-byte burst read (Z, Y, IR1, X/IR2) --
    _channel_data_raw = ROBits(64, _TCS3430_REG_CH0DATAL, 0, register_width=8)

    # -- CFG2 register (0x9F) --
    _hgain = RWBit(_TCS3430_REG_CFG2, 4)  # HGAIN

    # -- CFG3 register (0xAB) --
    interrupt_clear_on_read = RWBit(_TCS3430_REG_CFG3, 7)  # INT_READ_CLEAR
    """Enable/disable interrupt clear on reading"""

    sleep_after_interrupt = RWBit(_TCS3430_REG_CFG3, 4)  # SAI
    """Enable/disable sleep after interrupt"""

    # -- AZ_CONFIG register (0xD6) --
    auto_zero_mode = RWBit(_TCS3430_REG_AZ_CONFIG, 7)  # AZ_MODE
    """Enable/disable auto-zero mode"""

    auto_zero_nth = RWBits(7, _TCS3430_REG_AZ_CONFIG, 0)  # AZ_NTH_ITERATION
    """Auto-zero interval. Run auto-zero every N measurements"""

    # -- INTENAB register (0xDD) --
    saturation_interrupt_enabled = RWBit(_TCS3430_REG_INTENAB, 7)  # ASIEN
    """Enable/disable saturation interrupt"""

    als_interrupt_enabled = RWBit(_TCS3430_REG_INTENAB, 4)  # AIEN
    """Enable/disable als interrupt"""

    def __init__(self, i2c_bus: "busio.I2C", address: int = _TCS3430_DEFAULT_ADDR) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)

        # Verify chip ID
        chip_id = self.chip_id
        if chip_id != _TCS3430_CHIP_ID:
            raise RuntimeError(
                "Failed to find TCS3430 – check your wiring! "
                + f"Expected ID 0x{_TCS3430_CHIP_ID:02X}, "
                + f"got 0x{chip_id:02X}."
            )

        # Power on and enable ALS (matches Arduino begin())
        self.power_on = True
        self.als_enabled = True

    # -----------------------------------------------------------------
    # Integration time (convenience conversions around integration_cycles)
    # -----------------------------------------------------------------
    @property
    def integration_time(self) -> float:
        """Integration time in milliseconds.

        Computed from :attr:`integration_cycles` as ``(cycles + 1) * 2.78``.
        Setting this property writes the closest cycle count back to the
        ATIME register.
        """
        return (self.integration_cycles + 1) * 2.78

    @integration_time.setter
    def integration_time(self, ms: float) -> None:
        self.integration_cycles = int(ms / 2.78 - 1)

    # -----------------------------------------------------------------
    # Wait time (convenience conversions around wait_cycles)
    # -----------------------------------------------------------------
    @property
    def wait_time(self) -> float:
        """Wait time in milliseconds.

        Computed from :attr:`wait_cycles` as ``(cycles + 1) * 2.78``.
        When :attr:`wait_long` is enabled the actual wait is multiplied by 12.
        Setting this property writes the closest cycle count back to the
        WTIME register (it does **not** account for :attr:`wait_long`).
        """
        return (self.wait_cycles + 1) * 2.78

    @wait_time.setter
    def wait_time(self, ms: float) -> None:
        self.wait_cycles = int(ms / 2.78 - 1)

    # -----------------------------------------------------------------
    # ALS gain (spans CFG1 AGAIN bits and CFG2 HGAIN bit)
    # -----------------------------------------------------------------
    @property
    def als_gain(self) -> int:
        """ALS analogue gain.

        Must be an :class:`ALSGain` value.  ``ALSGain.GAIN_128X`` is
        achieved by setting the hardware gain to 64x **and** asserting the
        HGAIN bit in CFG2.

        * ``ALSGain.GAIN_1X``
        * ``ALSGain.GAIN_4X``
        * ``ALSGain.GAIN_16X``
        * ``ALSGain.GAIN_64X``
        * ``ALSGain.GAIN_128X``
        """
        if self._als_gain == ALSGain.GAIN_64X and self._hgain:
            return ALSGain.GAIN_128X
        return self._als_gain

    @als_gain.setter
    def als_gain(self, value: int) -> None:
        if not ALSGain.is_valid(value):
            raise ValueError("als_gain must be an ALSGain value")
        if value == ALSGain.GAIN_128X:
            self._als_gain = ALSGain.GAIN_64X
            self._hgain = True
        else:
            self._als_gain = value
            self._hgain = False

    # -----------------------------------------------------------------
    # Status helpers
    # -----------------------------------------------------------------
    @property
    def als_saturated(self) -> bool:
        """``True`` if the ALS data is saturated (read-only).

        Use :meth:`clear_als_saturated` to clear the flag.
        """
        return bool(self._als_saturated_status)

    def clear_als_saturated(self) -> None:
        """Clear the ALS saturation flag by writing 0x80 to the STATUS register."""
        self._status = 0x80

    @property
    def als_interrupt(self) -> bool:
        """``True`` if the ALS interrupt flag is set (read-only).

        Use :meth:`clear_als_interrupt` to clear the flag.
        """
        return bool(self._als_interrupt_status)

    def clear_als_interrupt(self) -> None:
        """Clear the ALS interrupt (and all other status flags) by writing
        0xFF to the STATUS register.

        .. note::
            If the threshold condition still exists and ALS is running,
            the interrupt will re-fire on the next integration cycle.
        """
        self._status = 0xFF

    # -----------------------------------------------------------------
    # Channel reads
    # -----------------------------------------------------------------
    @property
    def channels(self) -> Tuple[int, int, int, int]:
        """Read the X, Y, Z, and IR1 channels in a single burst.

        If the ALS MUX is currently set to IR2 mode, it is temporarily
        switched back to X mode for the read and then restored.

        Returns a tuple ``(x, y, z, ir1)`` of 16-bit unsigned values.
        """
        was_ir2 = self.als_mux_ir2
        if was_ir2:
            self.als_mux_ir2 = False

        raw = self._channel_data_raw
        z = raw & 0xFFFF
        y = (raw >> 16) & 0xFFFF
        ir1 = (raw >> 32) & 0xFFFF
        x = (raw >> 48) & 0xFFFF

        if was_ir2:
            self.als_mux_ir2 = True

        return (x, y, z, ir1)

    @property
    def ir2(self) -> int:
        """Read the IR2 channel value.

        This temporarily switches the ALS MUX to IR2, waits one integration
        period for fresh data, reads CH3, and restores the previous MUX
        setting.
        """
        was_ir2 = self.als_mux_ir2
        if not was_ir2:
            self.als_mux_ir2 = True

        # Wait for one full integration cycle so data is fresh
        time.sleep(self.integration_time / 1000.0)

        value = self._channel_x_or_ir2

        if not was_ir2:
            self.als_mux_ir2 = False

        return value
