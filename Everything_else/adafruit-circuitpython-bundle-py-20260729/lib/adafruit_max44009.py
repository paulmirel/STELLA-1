# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_max44009`
================================================================================




* Author(s): Tim Cocks

Implementation Notes
--------------------

**Hardware:**

* `Adafruit MAX44009 Wide-range Lux Light Sensor <https://www.adafruit.com/product/6498>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

__version__ = "1.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_MAX44009.git"

from adafruit_bus_device import i2c_device
from adafruit_register.i2c_bit import ROBit, RWBit
from adafruit_register.i2c_bits import ROBits, RWBits
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from micropython import const

try:
    import busio
except ImportError:
    pass

# -----------------------------------------------------------------------
# I2C addresses
# -----------------------------------------------------------------------
_MAX44009_DEFAULT_ADDRESS = const(0x4A)  # A0 = GND
_MAX44009_ALT_ADDRESS = const(0x4B)  # A0 = VCC

# -----------------------------------------------------------------------
# Register addresses
# -----------------------------------------------------------------------
_MAX44009_REG_INT_STATUS = const(0x00)  # Interrupt status (read clears)
_MAX44009_REG_INT_ENABLE = const(0x01)  # Interrupt enable
_MAX44009_REG_CONFIG = const(0x02)  # Configuration
_MAX44009_REG_LUX_HIGH = const(0x03)  # Lux reading high byte
_MAX44009_REG_LUX_LOW = const(0x04)  # Lux reading low byte
_MAX44009_REG_THRESH_UPPER = const(0x05)  # Upper threshold
_MAX44009_REG_THRESH_LOWER = const(0x06)  # Lower threshold
_MAX44009_REG_THRESH_TIMER = const(0x07)  # Threshold timer

# -----------------------------------------------------------------------
# Lux calculation constant
# -----------------------------------------------------------------------
_MAX44009_LUX_MULTIPLIER = 0.045


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
class IntegrationTime(CV):
    """Integration time settings for TIM bits [2:0] of CONFIG register.

    In automatic mode (MANUAL=0), only the first four values (800ms-100ms)
    are available. The shorter integration times (50ms-6.25ms) require
    manual mode to be enabled.

    +------------------------------------------+---------+---------------------------+
    | Setting                                  | Time    | Notes                     |
    +==========================================+=========+===========================+
    | :py:const:`IntegrationTime.MS_800`       | 800 ms  | Best low-light sensitivity|
    +------------------------------------------+---------+---------------------------+
    | :py:const:`IntegrationTime.MS_400`       | 400 ms  |                           |
    +------------------------------------------+---------+---------------------------+
    | :py:const:`IntegrationTime.MS_200`       | 200 ms  |                           |
    +------------------------------------------+---------+---------------------------+
    | :py:const:`IntegrationTime.MS_100`       | 100 ms  | Default, best high-bright |
    +------------------------------------------+---------+---------------------------+
    | :py:const:`IntegrationTime.MS_50`        | 50 ms   | Manual mode only          |
    +------------------------------------------+---------+---------------------------+
    | :py:const:`IntegrationTime.MS_25`        | 25 ms   | Manual mode only          |
    +------------------------------------------+---------+---------------------------+
    | :py:const:`IntegrationTime.MS_12_5`      | 12.5 ms | Manual mode only          |
    +------------------------------------------+---------+---------------------------+
    | :py:const:`IntegrationTime.MS_6_25`      | 6.25 ms | Manual mode only          |
    +------------------------------------------+---------+---------------------------+
    """

    MS_800 = 0b000
    MS_400 = 0b001
    MS_200 = 0b010
    MS_100 = 0b011
    MS_50 = 0b100
    MS_25 = 0b101
    MS_12_5 = 0b110
    MS_6_25 = 0b111


class Mode(CV):
    """Operating mode settings for CONT (bit 7) and MANUAL (bit 6) of CONFIG.

    +----------------------------------------------+------+--------+--------------------+
    | Setting                                      | CONT | MANUAL | Description        |
    +==============================================+======+========+====================+
    | :py:const:`Mode.DEFAULT`                     | 0    | 0      | Auto, 800ms cycle  |
    +----------------------------------------------+------+--------+--------------------+
    | :py:const:`Mode.CONTINUOUS`                  | 1    | 0      | Auto, fast updates |
    +----------------------------------------------+------+--------+--------------------+
    | :py:const:`Mode.MANUAL`                      | 0    | 1      | Manual, 800ms cycle|
    +----------------------------------------------+------+--------+--------------------+
    | :py:const:`Mode.MANUAL_CONTINUOUS`           | 1    | 1      | Manual, fast       |
    +----------------------------------------------+------+--------+--------------------+
    """

    DEFAULT = 0b00
    CONTINUOUS = 0b10
    MANUAL = 0b01
    MANUAL_CONTINUOUS = 0b11


# -----------------------------------------------------------------------
# Driver class
# -----------------------------------------------------------------------
class MAX44009:
    """CircuitPython driver for the MAX44009 ambient light sensor.

    :param ~busio.I2C i2c_bus: The I2C bus the device is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x4A`.
    """

    # ----------------------------------------------------------------
    # REG_INT_STATUS (0x00) – read-only, reading clears the interrupt
    # ----------------------------------------------------------------
    interrupt_status = ROBit(_MAX44009_REG_INT_STATUS, 0)
    """True if an interrupt event occurred. Reading clears the interrupt."""

    # ----------------------------------------------------------------
    # REG_INT_ENABLE (0x01)
    # ----------------------------------------------------------------
    interrupt_enabled = RWBit(_MAX44009_REG_INT_ENABLE, 0)
    """Enable or disable the interrupt. True to enable."""

    # ----------------------------------------------------------------
    # REG_CONFIG (0x02)
    #   bit 7: CONT   – continuous mode
    #   bit 6: MANUAL – manual configuration
    #   bit 3: CDR    – current division ratio
    #   bits [2:0]: TIM – integration time
    # ----------------------------------------------------------------
    _mode = RWBits(2, _MAX44009_REG_CONFIG, 6)

    current_division_ratio = RWBit(_MAX44009_REG_CONFIG, 3)
    """Current division ratio. When True, only 1/8 of photodiode current
    is used, extending measurement range for very bright conditions."""

    _integration_time = RWBits(3, _MAX44009_REG_CONFIG, 0)

    # ----------------------------------------------------------------
    # REG_LUX_HIGH (0x03) + REG_LUX_LOW (0x04)
    # 2-byte big-endian read starting at LUX_HIGH for atomic snapshot
    # ----------------------------------------------------------------
    _lux_raw = ROUnaryStruct(_MAX44009_REG_LUX_HIGH, ">H")

    # ----------------------------------------------------------------
    # REG_THRESH_UPPER (0x05) – upper window threshold
    # REG_THRESH_LOWER (0x06) – lower window threshold
    # ----------------------------------------------------------------
    _threshold_upper = UnaryStruct(_MAX44009_REG_THRESH_UPPER, ">B")
    _threshold_lower = UnaryStruct(_MAX44009_REG_THRESH_LOWER, ">B")

    # ----------------------------------------------------------------
    # REG_THRESH_TIMER (0x07) – threshold persist timer
    # ----------------------------------------------------------------
    threshold_timer = UnaryStruct(_MAX44009_REG_THRESH_TIMER, ">B")
    """Threshold persist timer value (0-255). The interrupt triggers only
    if lux stays outside the threshold window for (value * 100ms)."""

    def __init__(self, i2c_bus: "busio.I2C", address: int = _MAX44009_DEFAULT_ADDRESS) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)

        self._overrange = False

        # Verify communication by reading the config register
        try:
            _ = self._mode
        except OSError as err:
            raise RuntimeError("Failed to communicate with MAX44009 – check your wiring!") from err

        # Default to continuous auto-ranging mode
        self.mode = Mode.CONTINUOUS

    @property
    def lux(self) -> float:
        """Read the lux value with full 12-bit resolution.

        Returns NaN if the sensor is in an overrange condition (exponent = 0x0F).
        Check :attr:`overrange` after reading to detect saturation.
        """
        raw = self._lux_raw
        exponent = (raw >> 12) & 0x0F

        if exponent == 0x0F:
            self._overrange = True
            return float("nan")

        self._overrange = False

        # Full 8-bit mantissa: upper 4 bits from LUX_HIGH, lower 4 from LUX_LOW
        mantissa = ((raw >> 4) & 0xF0) | (raw & 0x0F)

        # Lux = 2^exponent * mantissa * 0.045
        return (1 << exponent) * mantissa * _MAX44009_LUX_MULTIPLIER

    @property
    def overrange(self) -> bool:
        """True if the last :attr:`lux` reading was an overrange condition."""
        return self._overrange

    @property
    def mode(self) -> int:
        """The operating mode. Must be a :class:`Mode` value."""
        return self._mode

    @mode.setter
    def mode(self, value: int) -> None:
        if not Mode.is_valid(value):
            raise ValueError(f"Invalid mode: {value}")
        self._mode = value

    @property
    def integration_time(self) -> int:
        """The integration time. Must be an :class:`IntegrationTime` value.

        Integration times shorter than 100ms require manual mode to be enabled.
        """
        return self._integration_time

    @integration_time.setter
    def integration_time(self, value: int) -> None:
        if not IntegrationTime.is_valid(value):
            raise ValueError(f"Invalid integration time: {value}")
        self._integration_time = value

    @property
    def upper_threshold(self) -> float:
        """Upper lux threshold for interrupt generation."""
        return self._threshold_to_lux(self._threshold_upper)

    @upper_threshold.setter
    def upper_threshold(self, lux: float) -> None:
        self._threshold_upper = self._lux_to_threshold(lux)

    @property
    def lower_threshold(self) -> float:
        """Lower lux threshold for interrupt generation."""
        return self._threshold_to_lux(self._threshold_lower)

    @lower_threshold.setter
    def lower_threshold(self, lux: float) -> None:
        self._threshold_lower = self._lux_to_threshold(lux)

    @staticmethod
    def _lux_to_threshold(lux: float) -> int:
        """Convert a lux value to the 8-bit threshold register format."""
        if lux <= 0:
            return 0x00

        exponent = 0
        while exponent < 14:
            max_for_exp = (1 << exponent) * 255.0 * _MAX44009_LUX_MULTIPLIER
            if lux <= max_for_exp:
                break
            exponent += 1

        mantissa = int(lux / ((1 << exponent) * _MAX44009_LUX_MULTIPLIER))
        mantissa_upper = (mantissa >> 4) & 0x0F

        return (exponent << 4) | mantissa_upper

    @staticmethod
    def _threshold_to_lux(threshold: int) -> float:
        """Convert an 8-bit threshold register value to lux."""
        exponent = (threshold >> 4) & 0x0F
        mantissa_upper = threshold & 0x0F
        # Lower 4 bits are implicitly 0x0F
        full_mantissa = (mantissa_upper << 4) | 0x0F
        return (1 << exponent) * full_mantissa * _MAX44009_LUX_MULTIPLIER
