# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_vcnl4030`
================================================================================

CircuitPython driver library for VCNL4030X01 Proximity / Ambient Light sensor


* Author(s): Tim Cocks

Implementation Notes
--------------------

**Hardware:**

* Adafruit VCNL4030X01 Proximity and Ambient Light Sensor Breakout

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

# * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
# * Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

__version__ = "1.1.3"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_VCNL4030.git"

from adafruit_bus_device import i2c_device
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import ROBits, RWBits
from adafruit_register.i2c_struct import UnaryStruct
from micropython import const

try:
    import busio
except ImportError:
    pass

# -----------------------------------------------------------------------
# I2C address and chip ID
# -----------------------------------------------------------------------
_VCNL4030_DEFAULT_ADDR = const(0x60)
_VCNL4030_ID_L_EXPECTED = const(0x80)

# -----------------------------------------------------------------------
# Register addresses (all registers are 16-bit little-endian)
# -----------------------------------------------------------------------
_VCNL4030_REG_ALS_CONF = const(0x00)  # ALS_CONF1 (L) + ALS_CONF2 (H)
_VCNL4030_REG_ALS_THDH = const(0x01)  # ALS high threshold
_VCNL4030_REG_ALS_THDL = const(0x02)  # ALS low threshold
_VCNL4030_REG_PS_CONF1_2 = const(0x03)  # PS_CONF1 (L) + PS_CONF2 (H)
_VCNL4030_REG_PS_CONF3_MS = const(0x04)  # PS_CONF3 (L) + PS_MS (H)
_VCNL4030_REG_PS_CANC = const(0x05)  # PS cancellation level
_VCNL4030_REG_PS_THDL = const(0x06)  # PS low threshold
_VCNL4030_REG_PS_THDH = const(0x07)  # PS high threshold
_VCNL4030_REG_PS_DATA = const(0x08)  # PS data output
_VCNL4030_REG_ALS_DATA = const(0x0B)  # ALS data output
_VCNL4030_REG_WHITE_DATA = const(0x0C)  # White channel data output
_VCNL4030_REG_INT_FLAG = const(0x0D)  # Reserved (L) + INT_Flag (H)
_VCNL4030_REG_ID = const(0x0E)  # ID_L (L) + ID_M (H)

# Interrupt flag bit masks (within the high byte of INT_FLAG register)
VCNL4030_ALS_IF_L = const(0x20)  # ALS crossed low threshold
VCNL4030_ALS_IF_H = const(0x10)  # ALS crossed high threshold
VCNL4030_PROX_SPFLAG = const(0x04)  # PS sunlight protection active
VCNL4030_PROX_IF_CLOSE = const(0x02)  # PS object approaching
VCNL4030_PROX_IF_AWAY = const(0x01)  # PS object moving away


# -----------------------------------------------------------------------
# CV helper
# -----------------------------------------------------------------------
class CV:
    """Constant-value helper for enum-like classes."""

    @classmethod
    def is_valid(cls, value: int) -> bool:
        """Return True if *value* is a member of this CV class."""
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
class ALSIntegrationTime(CV):
    """ALS integration time settings for ALS_IT bits [7:5] of ALS_CONF.

    Longer integration times give higher resolution (lower lux/step).

    +-------------------------------------------+--------+----------------+
    | Setting                                   | Time   | Resolution     |
    +===========================================+========+================+
    | :py:const:`ALSIntegrationTime.MS_50`      | 50 ms  | 0.064 lux/step |
    +-------------------------------------------+--------+----------------+
    | :py:const:`ALSIntegrationTime.MS_100`     | 100 ms | 0.032 lux/step |
    +-------------------------------------------+--------+----------------+
    | :py:const:`ALSIntegrationTime.MS_200`     | 200 ms | 0.016 lux/step |
    +-------------------------------------------+--------+----------------+
    | :py:const:`ALSIntegrationTime.MS_400`     | 400 ms | 0.008 lux/step |
    +-------------------------------------------+--------+----------------+
    | :py:const:`ALSIntegrationTime.MS_800`     | 800 ms | 0.004 lux/step |
    +-------------------------------------------+--------+----------------+
    """

    MS_50 = 0b000
    MS_100 = 0b001
    MS_200 = 0b010
    MS_400 = 0b011
    MS_800 = 0b100


class ALSPersistence(CV):
    """ALS interrupt persistence settings for ALS_PERS bits [3:2] of ALS_CONF.

    Number of consecutive out-of-threshold readings before an interrupt fires.

    +--------------------------------------+------------+
    | Setting                              | Readings   |
    +======================================+============+
    | :py:const:`ALSPersistence.CYCLES_1`  | 1 reading  |
    +--------------------------------------+------------+
    | :py:const:`ALSPersistence.CYCLES_2`  | 2 readings |
    +--------------------------------------+------------+
    | :py:const:`ALSPersistence.CYCLES_4`  | 4 readings |
    +--------------------------------------+------------+
    | :py:const:`ALSPersistence.CYCLES_8`  | 8 readings |
    +--------------------------------------+------------+
    """

    CYCLES_1 = 0b00
    CYCLES_2 = 0b01
    CYCLES_4 = 0b10
    CYCLES_8 = 0b11


class ProxDuty(CV):
    """PS IRED duty ratio settings for PS_DUTY bits [7:6] of PS_CONF1.

    Higher duty divisor = lower average LED power.

    +-----------------------------------+----------------------+
    | Setting                           | Duty cycle           |
    +===================================+======================+
    | :py:const:`ProxDuty.RATIO_40`     | 1/40  (highest power)|
    +-----------------------------------+----------------------+
    | :py:const:`ProxDuty.RATIO_80`     | 1/80                 |
    +-----------------------------------+----------------------+
    | :py:const:`ProxDuty.RATIO_160`    | 1/160                |
    +-----------------------------------+----------------------+
    | :py:const:`ProxDuty.RATIO_320`    | 1/320 (lowest power) |
    +-----------------------------------+----------------------+
    """

    RATIO_40 = 0b00
    RATIO_80 = 0b01
    RATIO_160 = 0b10
    RATIO_320 = 0b11


class ProxPersistence(CV):
    """PS interrupt persistence settings for PS_PERS bits [5:4] of PS_CONF1.

    +---------------------------------------+------------+
    | Setting                               | Readings   |
    +=======================================+============+
    | :py:const:`ProxPersistence.CYCLES_1`  | 1 reading  |
    +---------------------------------------+------------+
    | :py:const:`ProxPersistence.CYCLES_2`  | 2 readings |
    +---------------------------------------+------------+
    | :py:const:`ProxPersistence.CYCLES_3`  | 3 readings |
    +---------------------------------------+------------+
    | :py:const:`ProxPersistence.CYCLES_4`  | 4 readings |
    +---------------------------------------+------------+
    """

    CYCLES_1 = 0b00
    CYCLES_2 = 0b01
    CYCLES_3 = 0b10
    CYCLES_4 = 0b11


class ProxIntegrationTime(CV):
    """PS integration time settings for PS_IT bits [3:1] of PS_CONF1.

    Higher T values give higher sensitivity.

    +----------------------------------------------+--------------------------+
    | Setting                                      | Period                   |
    +==============================================+==========================+
    | :py:const:`ProxIntegrationTime.T_1`          | 1T                       |
    +----------------------------------------------+--------------------------+
    | :py:const:`ProxIntegrationTime.T_1_5`        | 1.5T                     |
    +----------------------------------------------+--------------------------+
    | :py:const:`ProxIntegrationTime.T_2`          | 2T                       |
    +----------------------------------------------+--------------------------+
    | :py:const:`ProxIntegrationTime.T_2_5`        | 2.5T                     |
    +----------------------------------------------+--------------------------+
    | :py:const:`ProxIntegrationTime.T_3`          | 3T                       |
    +----------------------------------------------+--------------------------+
    | :py:const:`ProxIntegrationTime.T_3_5`        | 3.5T                     |
    +----------------------------------------------+--------------------------+
    | :py:const:`ProxIntegrationTime.T_4`          | 4T                       |
    +----------------------------------------------+--------------------------+
    | :py:const:`ProxIntegrationTime.T_8`          | 8T (highest sensitivity) |
    +----------------------------------------------+--------------------------+
    """

    T_1 = 0b000
    T_1_5 = 0b001
    T_2 = 0b010
    T_2_5 = 0b011
    T_3 = 0b100
    T_3_5 = 0b101
    T_4 = 0b110
    T_8 = 0b111


class ProxGain(CV):
    """PS gain settings for PS_GAIN bits [13:12] of PS_CONF2.

    +------------------------------------------+-------------------------------+
    | Setting                                  | Description                   |
    +==========================================+===============================+
    | :py:const:`ProxGain.TWO_STEP`            | Two-step mode (~4x single 1x) |
    +------------------------------------------+-------------------------------+
    | :py:const:`ProxGain.SINGLE_8X`           | Single mode, 8x range         |
    +------------------------------------------+-------------------------------+
    | :py:const:`ProxGain.SINGLE_1X`           | Single mode, 1x range         |
    +------------------------------------------+-------------------------------+
    """

    TWO_STEP = 0b00
    SINGLE_8X = 0b10
    SINGLE_1X = 0b11


class ProxInterruptMode(CV):
    """PS interrupt mode settings for PS_INT bits [9:8] of PS_CONF2.

    +----------------------------------------------+-----------------------------+
    | Setting                                      | Description                 |
    +==============================================+=============================+
    | :py:const:`ProxInterruptMode.DISABLED`       | Interrupt disabled          |
    +----------------------------------------------+-----------------------------+
    | :py:const:`ProxInterruptMode.CLOSE`          | Interrupt on close          |
    +----------------------------------------------+-----------------------------+
    | :py:const:`ProxInterruptMode.AWAY`           | Interrupt on away           |
    +----------------------------------------------+-----------------------------+
    | :py:const:`ProxInterruptMode.BOTH`           | Interrupt on close and away |
    +----------------------------------------------+-----------------------------+
    """

    DISABLED = 0b00
    CLOSE = 0b01
    AWAY = 0b10
    BOTH = 0b11


class ProxLEDCurrent(CV):
    """LED driving current settings for LED_I bits [10:8] of PS_MS.

    +------------------------------------------+----------+
    | Setting                                  | Current  |
    +==========================================+==========+
    | :py:const:`ProxLEDCurrent.MA_50`         | 50 mA    |
    +------------------------------------------+----------+
    | :py:const:`ProxLEDCurrent.MA_75`         | 75 mA    |
    +------------------------------------------+----------+
    | :py:const:`ProxLEDCurrent.MA_100`        | 100 mA   |
    +------------------------------------------+----------+
    | :py:const:`ProxLEDCurrent.MA_120`        | 120 mA   |
    +------------------------------------------+----------+
    | :py:const:`ProxLEDCurrent.MA_140`        | 140 mA   |
    +------------------------------------------+----------+
    | :py:const:`ProxLEDCurrent.MA_160`        | 160 mA   |
    +------------------------------------------+----------+
    | :py:const:`ProxLEDCurrent.MA_180`        | 180 mA   |
    +------------------------------------------+----------+
    | :py:const:`ProxLEDCurrent.MA_200`        | 200 mA   |
    +------------------------------------------+----------+
    """

    MA_50 = 0b000
    MA_75 = 0b001
    MA_100 = 0b010
    MA_120 = 0b011
    MA_140 = 0b100
    MA_160 = 0b101
    MA_180 = 0b110
    MA_200 = 0b111


class SunlightCancelCurrent(CV):
    """Sunlight cancellation current multiplier for PS_SC_CUR bits [14:13] of PS_MS.

    +----------------------------------------------+-------------+
    | Setting                                      | Multiplier  |
    +==============================================+=============+
    | :py:const:`SunlightCancelCurrent.X1`         | 1x typical  |
    +----------------------------------------------+-------------+
    | :py:const:`SunlightCancelCurrent.X2`         | 2x typical  |
    +----------------------------------------------+-------------+
    | :py:const:`SunlightCancelCurrent.X4`         | 4x typical  |
    +----------------------------------------------+-------------+
    | :py:const:`SunlightCancelCurrent.X8`         | 8x typical  |
    +----------------------------------------------+-------------+
    """

    X1 = 0b00
    X2 = 0b01
    X4 = 0b10
    X8 = 0b11


# -----------------------------------------------------------------------
# Driver class
# -----------------------------------------------------------------------
class VCNL4030:
    """CircuitPython driver for the Vishay VCNL4030X01 proximity and ambient
    light sensor.

    :param ~busio.I2C i2c_bus: The I2C bus the device is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x60`.
    """

    # ----------------------------------------------------------------
    # REG_ALS_CONF (0x00) – 16-bit LE
    # Low byte = ALS_CONF1, High byte = ALS_CONF2
    # ----------------------------------------------------------------
    _als_sd = RWBit(_VCNL4030_REG_ALS_CONF, 0, register_width=2)
    # ALS_SD: 0 = enabled, 1 = shutdown (inverted; use als_enabled property)

    als_interrupt_enabled = RWBit(_VCNL4030_REG_ALS_CONF, 1, register_width=2)
    """Enable or disable the ALS interrupt. True to enable."""

    _als_persistence = RWBits(2, _VCNL4030_REG_ALS_CONF, 2, register_width=2)

    als_high_dynamic_range = RWBit(_VCNL4030_REG_ALS_CONF, 4, register_width=2)
    """Enable ALS high dynamic range mode (2x range, halves sensitivity). True to enable."""

    _als_integration_time = RWBits(3, _VCNL4030_REG_ALS_CONF, 5, register_width=2)

    _white_sd = RWBit(_VCNL4030_REG_ALS_CONF, 8, register_width=2)
    # WHITE_SD: 0 = enabled, 1 = shutdown (inverted; use white_channel_enabled property)

    als_low_sensitivity = RWBit(_VCNL4030_REG_ALS_CONF, 9, register_width=2)
    """Enable ALS low sensitivity mode (1x vs 2x). True for lower sensitivity."""

    # ----------------------------------------------------------------
    # REG_ALS_THDH (0x01) – ALS high threshold, 16-bit LE
    # ----------------------------------------------------------------
    als_threshold_high = UnaryStruct(_VCNL4030_REG_ALS_THDH, "<H")
    """ALS interrupt high threshold (16-bit)."""

    # ----------------------------------------------------------------
    # REG_ALS_THDL (0x02) – ALS low threshold, 16-bit LE
    # ----------------------------------------------------------------
    als_threshold_low = UnaryStruct(_VCNL4030_REG_ALS_THDL, "<H")
    """ALS interrupt low threshold (16-bit)."""

    # ----------------------------------------------------------------
    # REG_PS_CONF1_2 (0x03) – 16-bit LE
    # Low byte = PS_CONF1, High byte = PS_CONF2
    # ----------------------------------------------------------------
    _ps_sd = RWBit(_VCNL4030_REG_PS_CONF1_2, 0, register_width=2)
    # PS_SD: 0 = enabled, 1 = shutdown (inverted; use proximity_enabled property)

    _proximity_integration_time = RWBits(3, _VCNL4030_REG_PS_CONF1_2, 1, register_width=2)

    _proximity_persistence = RWBits(2, _VCNL4030_REG_PS_CONF1_2, 4, register_width=2)

    _proximity_duty = RWBits(2, _VCNL4030_REG_PS_CONF1_2, 6, register_width=2)

    _proximity_interrupt_mode = RWBits(2, _VCNL4030_REG_PS_CONF1_2, 8, register_width=2)

    proximity_low_sensitivity = RWBit(_VCNL4030_REG_PS_CONF1_2, 10, register_width=2)
    """Enable PS low sensitivity mode. True for lower sensitivity."""

    proximity_resolution_16bit = RWBit(_VCNL4030_REG_PS_CONF1_2, 11, register_width=2)
    """Enable 16-bit PS output resolution (False = 12-bit). True for 16-bit."""

    _proximity_gain = RWBits(2, _VCNL4030_REG_PS_CONF1_2, 12, register_width=2)

    # ----------------------------------------------------------------
    # REG_PS_CONF3_MS (0x04) – 16-bit LE
    # Low byte = PS_CONF3, High byte = PS_MS
    # ----------------------------------------------------------------
    sunlight_cancellation_enabled = RWBit(_VCNL4030_REG_PS_CONF3_MS, 0, register_width=2)
    """Enable sunlight cancellation feature. True to enable."""

    proximity_logic_mode = RWBit(_VCNL4030_REG_PS_CONF3_MS, 1, register_width=2)
    """Enable PS logic output mode. True for logic output, False for normal+interrupt."""

    _ps_trig = RWBit(_VCNL4030_REG_PS_CONF3_MS, 2, register_width=2)
    # PS_TRIG: write 1 to trigger a single reading in active force mode (self-clearing)

    proximity_active_force_mode = RWBit(_VCNL4030_REG_PS_CONF3_MS, 3, register_width=2)
    """Enable PS active force mode (manual trigger). True to enable."""

    proximity_smart_persistence = RWBit(_VCNL4030_REG_PS_CONF3_MS, 4, register_width=2)
    """Enable PS smart persistence. True to enable."""

    led_low_current = RWBit(_VCNL4030_REG_PS_CONF3_MS, 7, register_width=2)
    """Reduce LED current to 1/10 of normal. True to enable."""

    _led_current = RWBits(3, _VCNL4030_REG_PS_CONF3_MS, 8, register_width=2)

    sunlight_protect_output_high = RWBit(_VCNL4030_REG_PS_CONF3_MS, 11, register_width=2)
    """Sunlight protect output level. True for 0xFF output, False for 0x00."""

    sunlight_protection_enhanced = RWBit(_VCNL4030_REG_PS_CONF3_MS, 12, register_width=2)
    """Enable enhanced sunlight protection (1.5x capability). True to enable."""

    _sunlight_cancel_current = RWBits(2, _VCNL4030_REG_PS_CONF3_MS, 13, register_width=2)

    # ----------------------------------------------------------------
    # REG_PS_CANC (0x05) – PS cancellation level, 16-bit LE
    # ----------------------------------------------------------------
    proximity_cancellation = UnaryStruct(_VCNL4030_REG_PS_CANC, "<H")
    """PS crosstalk cancellation level (subtracted from raw PS reading)."""

    # ----------------------------------------------------------------
    # REG_PS_THDL (0x06) – PS low threshold, 16-bit LE
    # ----------------------------------------------------------------
    proximity_threshold_low = UnaryStruct(_VCNL4030_REG_PS_THDL, "<H")
    """PS interrupt low threshold (16-bit)."""

    # ----------------------------------------------------------------
    # REG_PS_THDH (0x07) – PS high threshold, 16-bit LE
    # ----------------------------------------------------------------
    proximity_threshold_high = UnaryStruct(_VCNL4030_REG_PS_THDH, "<H")
    """PS interrupt high threshold (16-bit)."""

    # ----------------------------------------------------------------
    # REG_PS_DATA (0x08) – PS output, 16-bit LE (read-only)
    # ----------------------------------------------------------------
    _proximity_raw = ROBits(16, _VCNL4030_REG_PS_DATA, 0, register_width=2)

    # ----------------------------------------------------------------
    # REG_ALS_DATA (0x0B) – ALS output, 16-bit LE (read-only)
    # ----------------------------------------------------------------
    _als_raw = ROBits(16, _VCNL4030_REG_ALS_DATA, 0, register_width=2)

    # ----------------------------------------------------------------
    # REG_WHITE_DATA (0x0C) – White channel output, 16-bit LE (read-only)
    # ----------------------------------------------------------------
    _white_raw = ROBits(16, _VCNL4030_REG_WHITE_DATA, 0, register_width=2)

    # ----------------------------------------------------------------
    # REG_INT_FLAG (0x0D) – 16-bit LE; flags are in the high byte (bits 15:8)
    # Reading this register clears the flags.
    # ----------------------------------------------------------------
    _int_flags_raw = ROBits(8, _VCNL4030_REG_INT_FLAG, 8, register_width=2)

    # ----------------------------------------------------------------
    # REG_ID (0x0E) – 16-bit LE; ID_L is low byte, ID_M is high byte
    # ----------------------------------------------------------------
    _chip_id_l = ROBits(8, _VCNL4030_REG_ID, 0, register_width=2)

    # ----------------------------------------------------------------
    # ALS lux resolution lookup: ALSIntegrationTime value → lux/count
    # ----------------------------------------------------------------
    _ALS_RESOLUTION = {
        ALSIntegrationTime.MS_50: 0.064,
        ALSIntegrationTime.MS_100: 0.032,
        ALSIntegrationTime.MS_200: 0.016,
        ALSIntegrationTime.MS_400: 0.008,
        ALSIntegrationTime.MS_800: 0.004,
    }

    def __init__(self, i2c_bus: "busio.I2C", address: int = _VCNL4030_DEFAULT_ADDR) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)

        # Verify chip ID (low byte of REG_ID must be 0x80)
        chip_id = self._chip_id_l
        if chip_id != _VCNL4030_ID_L_EXPECTED:
            raise RuntimeError(
                "Failed to find VCNL4030 – check your wiring! "
                + f"Expected ID_L 0x{_VCNL4030_ID_L_EXPECTED:02X}, "
                + f"got 0x{chip_id:02X}."
            )

        # ALS: 100 ms integration time, normal dynamic range and sensitivity
        self.als_integration_time = ALSIntegrationTime.MS_100
        self.als_high_dynamic_range = False
        self.als_low_sensitivity = False
        self.als_enabled = True
        self.white_channel_enabled = True

        # PS: 16-bit mode, 200 mA LED current, enable PS
        self.proximity_resolution_16bit = True
        self.led_current = ProxLEDCurrent.MA_200
        self.proximity_enabled = True

    # ----------------------------------------------------------------
    # Enable/disable properties (inverted SD bits)
    # ----------------------------------------------------------------
    @property
    def als_enabled(self) -> bool:
        """Enable or disable the ambient light sensor. True = enabled."""
        return not self._als_sd

    @als_enabled.setter
    def als_enabled(self, enable: bool) -> None:
        self._als_sd = not enable

    @property
    def white_channel_enabled(self) -> bool:
        """Enable or disable the white channel. True = enabled."""
        return not self._white_sd

    @white_channel_enabled.setter
    def white_channel_enabled(self, enable: bool) -> None:
        self._white_sd = not enable

    @property
    def proximity_enabled(self) -> bool:
        """Enable or disable the proximity sensor. True = enabled."""
        return not self._ps_sd

    @proximity_enabled.setter
    def proximity_enabled(self, enable: bool) -> None:
        self._ps_sd = not enable

    # ----------------------------------------------------------------
    # CV-validated properties
    # ----------------------------------------------------------------
    @property
    def als_integration_time(self) -> int:
        """ALS integration time.

        Must be an :class:`ALSIntegrationTime` value, e.g.
        ``ALSIntegrationTime.MS_100``.
        """
        return self._als_integration_time

    @als_integration_time.setter
    def als_integration_time(self, value: int) -> None:
        if not ALSIntegrationTime.is_valid(value):
            raise ValueError("als_integration_time must be an ALSIntegrationTime constant")
        self._als_integration_time = value

    @property
    def als_persistence(self) -> int:
        """ALS interrupt persistence.

        Must be an :class:`ALSPersistence` value, e.g.
        ``ALSPersistence.CYCLES_1``.
        """
        return self._als_persistence

    @als_persistence.setter
    def als_persistence(self, value: int) -> None:
        if not ALSPersistence.is_valid(value):
            raise ValueError("als_persistence must be an ALSPersistence constant")
        self._als_persistence = value

    @property
    def proximity_integration_time(self) -> int:
        """PS integration time.

        Must be a :class:`ProxIntegrationTime` value, e.g.
        ``ProxIntegrationTime.T_1``.
        """
        return self._proximity_integration_time

    @proximity_integration_time.setter
    def proximity_integration_time(self, value: int) -> None:
        if not ProxIntegrationTime.is_valid(value):
            raise ValueError("proximity_integration_time must be a ProxIntegrationTime constant")
        self._proximity_integration_time = value

    @property
    def proximity_persistence(self) -> int:
        """PS interrupt persistence.

        Must be a :class:`ProxPersistence` value, e.g.
        ``ProxPersistence.CYCLES_1``.
        """
        return self._proximity_persistence

    @proximity_persistence.setter
    def proximity_persistence(self, value: int) -> None:
        if not ProxPersistence.is_valid(value):
            raise ValueError("proximity_persistence must be a ProxPersistence constant")
        self._proximity_persistence = value

    @property
    def proximity_duty(self) -> int:
        """PS IRED duty ratio.

        Must be a :class:`ProxDuty` value, e.g. ``ProxDuty.RATIO_40``.
        """
        return self._proximity_duty

    @proximity_duty.setter
    def proximity_duty(self, value: int) -> None:
        if not ProxDuty.is_valid(value):
            raise ValueError("proximity_duty must be a ProxDuty constant")
        self._proximity_duty = value

    @property
    def proximity_interrupt_mode(self) -> int:
        """PS interrupt mode.

        Must be a :class:`ProxInterruptMode` value, e.g.
        ``ProxInterruptMode.DISABLED``.
        """
        return self._proximity_interrupt_mode

    @proximity_interrupt_mode.setter
    def proximity_interrupt_mode(self, value: int) -> None:
        if not ProxInterruptMode.is_valid(value):
            raise ValueError("proximity_interrupt_mode must be a ProxInterruptMode constant")
        self._proximity_interrupt_mode = value

    @property
    def proximity_gain(self) -> int:
        """PS gain setting.

        Must be a :class:`ProxGain` value, e.g. ``ProxGain.TWO_STEP``.
        """
        return self._proximity_gain

    @proximity_gain.setter
    def proximity_gain(self, value: int) -> None:
        if not ProxGain.is_valid(value):
            raise ValueError("proximity_gain must be a ProxGain constant")
        self._proximity_gain = value

    @property
    def led_current(self) -> int:
        """LED driving current.

        Must be a :class:`ProxLEDCurrent` value, e.g.
        ``ProxLEDCurrent.MA_200``.
        """
        return self._led_current

    @led_current.setter
    def led_current(self, value: int) -> None:
        if not ProxLEDCurrent.is_valid(value):
            raise ValueError("led_current must be a ProxLEDCurrent constant")
        self._led_current = value

    @property
    def sunlight_cancel_current(self) -> int:
        """Sunlight cancellation current multiplier.

        Must be a :class:`SunlightCancelCurrent` value, e.g.
        ``SunlightCancelCurrent.X1``.
        """
        return self._sunlight_cancel_current

    @sunlight_cancel_current.setter
    def sunlight_cancel_current(self, value: int) -> None:
        if not SunlightCancelCurrent.is_valid(value):
            raise ValueError("sunlight_cancel_current must be a SunlightCancelCurrent constant")
        self._sunlight_cancel_current = value

    # ----------------------------------------------------------------
    # Data reads
    # ----------------------------------------------------------------
    @property
    def als(self) -> int:
        """Raw 16-bit ambient light sensor reading."""
        return self._als_raw

    @property
    def lux(self) -> float:
        """Ambient light in lux, computed from the raw ALS reading.

        Resolution is determined by the current :attr:`als_integration_time`,
        :attr:`als_high_dynamic_range`, and :attr:`als_low_sensitivity` settings.
        """
        raw = self._als_raw
        resolution = self._ALS_RESOLUTION.get(self.als_integration_time, 0.004)
        if self.als_high_dynamic_range:
            resolution *= 2.0
        if self.als_low_sensitivity:
            resolution *= 2.0
        return raw * resolution

    @property
    def white(self) -> int:
        """Raw 16-bit white channel reading."""
        return self._white_raw

    @property
    def proximity(self) -> int:
        """Raw PS reading (12-bit or 16-bit depending on :attr:`proximity_resolution_16bit`)."""
        return self._proximity_raw

    # ----------------------------------------------------------------
    # Active force mode trigger
    # ----------------------------------------------------------------
    def trigger_proximity(self) -> None:
        """Trigger a single PS measurement in active force mode.

        Has no effect unless :attr:`proximity_active_force_mode` is True.
        The PS_TRIG bit is self-clearing.
        """
        self._ps_trig = True

    # ----------------------------------------------------------------
    # Interrupt flags
    # ----------------------------------------------------------------
    @property
    def interrupt_flags(self) -> int:
        """Read and return the interrupt flags byte.

        Reading this register **clears** all flags on the device.
        Use the returned byte with the ``VCNL4030_ALS_IF_H``,
        ``VCNL4030_ALS_IF_L``, ``VCNL4030_PROX_IF_CLOSE``,
        ``VCNL4030_PROX_IF_AWAY``, and ``VCNL4030_PROX_SPFLAG``
        bitmask constants, or check the individual flag properties.
        """
        flags = self._int_flags_raw
        # 0xFF likely means an I2C failure; retry once
        if flags == 0xFF:
            flags = self._int_flags_raw
        self._cached_int_flags = flags
        return flags

    @property
    def als_high_flag(self) -> bool:
        """True if the ALS high-threshold flag was set in the last
        :attr:`interrupt_flags` read."""
        return bool(self._cached_int_flags & VCNL4030_ALS_IF_H)

    @property
    def als_low_flag(self) -> bool:
        """True if the ALS low-threshold flag was set in the last
        :attr:`interrupt_flags` read."""
        return bool(self._cached_int_flags & VCNL4030_ALS_IF_L)

    @property
    def proximity_close_flag(self) -> bool:
        """True if the PS close (approaching) flag was set in the last
        :attr:`interrupt_flags` read."""
        return bool(self._cached_int_flags & VCNL4030_PROX_IF_CLOSE)

    @property
    def proximity_away_flag(self) -> bool:
        """True if the PS away (receding) flag was set in the last
        :attr:`interrupt_flags` read."""
        return bool(self._cached_int_flags & VCNL4030_PROX_IF_AWAY)

    @property
    def proximity_sunlight_flag(self) -> bool:
        """True if the PS sunlight protection flag was set in the last
        :attr:`interrupt_flags` read."""
        return bool(self._cached_int_flags & VCNL4030_PROX_SPFLAG)

    def reset(self):
        """Reset the sensor back to its initial configuration state."""
        self.als_integration_time = ALSIntegrationTime.MS_100
        self.als_persistence = ALSPersistence.CYCLES_1
        self.proximity_integration_time = ProxIntegrationTime.T_1
        self.proximity_persistence = ProxPersistence.CYCLES_1
        self.proximity_duty = ProxDuty.RATIO_40
        self.proximity_interrupt_mode = ProxInterruptMode.DISABLED
        self.proximity_gain = ProxGain.TWO_STEP
        self.led_current = ProxLEDCurrent.MA_50
        self.sunlight_cancel_current = SunlightCancelCurrent.X1

        self.als_enabled = True
        self.white_channel_enabled = True
        self.proximity_enabled = True
        self.als_interrupt_enabled = False
        self.als_high_dynamic_range = False
        self.als_low_sensitivity = False
        self.proximity_low_sensitivity = False
        self.proximity_resolution_16bit = True
        self.sunlight_cancellation_enabled = False
        self.proximity_logic_mode = False
        self.proximity_active_force_mode = False
        self.proximity_smart_persistence = False
        self.led_low_current = False
        self.sunlight_protect_output_high = False
        self.sunlight_protection_enhanced = False

        self.als_threshold_high = 0
        self.als_threshold_low = 0
        self.proximity_threshold_high = 0
        self.proximity_threshold_low = 0
        self.proximity_cancellation = 0
