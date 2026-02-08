# SPDX-FileCopyrightText: Copyright (c) 2025 Tim C for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_opt4048`
================================================================================

CircuitPython driver library for the Adafruit OPT4048 breakout board, a high-speed,
high-precision tristimulus XYZ color sensor.


* Author(s): Tim C

Implementation Notes
--------------------

**Hardware:**

* `Adafruit OPT4048 Breakout <https://www.adafruit.com/products/6335>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register

"""

# imports

__version__ = "1.1.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_OPT4048.git"

from time import sleep

from adafruit_bus_device import i2c_device
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import ROBits, RWBits
from adafruit_register.i2c_struct import UnaryStruct
from micropython import const

try:
    from typing import ClassVar, Optional, Tuple

    import busio
except ImportError:
    pass

__version__ = "1.1.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_OPT4048.git"

# Correct content of DEVICE_ID register
_OPT4048_CHIP_ID = const(0x0821)  # OPT4048 default device id


class CV:
    """Constant value class helper for enums."""

    @classmethod
    def is_valid(cls, value: int) -> bool:
        """Validate that a given value is a member"""
        IGNORE_LIST = [cls.__module__, cls.__name__]
        if value in cls.__dict__.values() and value not in IGNORE_LIST:
            return True
        return False

    @classmethod
    def get_name(cls, value) -> str:
        """Get the name for a given value"""
        name_dict = {}
        for _key, _value in cls.__dict__.items():
            name_dict[_value] = _key
        return name_dict[value]


class Range(CV):
    """Available range settings for the OPT4048 sensor.

    Full-scale light level ranges as described in datasheet page 29.

    +------------------------------+-------------------------+
    | Setting                      | Range Value             |
    +==============================+=========================+
    | :py:const:`Range.RANGE_2K`   | 2.2 klux                |
    +------------------------------+-------------------------+
    | :py:const:`Range.RANGE_4K`   | 4.5 klux                |
    +------------------------------+-------------------------+
    | :py:const:`Range.RANGE_9K`   | 9 klux                  |
    +------------------------------+-------------------------+
    | :py:const:`Range.RANGE_18K`  | 18 klux                 |
    +------------------------------+-------------------------+
    | :py:const:`Range.RANGE_36K`  | 36 klux                 |
    +------------------------------+-------------------------+
    | :py:const:`Range.RANGE_72K`  | 72 klux                 |
    +------------------------------+-------------------------+
    | :py:const:`Range.RANGE_144K` | 144 klux                |
    +------------------------------+-------------------------+
    | :py:const:`Range.AUTO`       | Auto-range              |
    +------------------------------+-------------------------+
    """

    RANGE_2K = 0  # 2.2 klux
    RANGE_4K = 1  # 4.5 klux
    RANGE_9K = 2  # 9 klux
    RANGE_18K = 3  # 18 klux
    RANGE_36K = 4  # 36 klux
    RANGE_72K = 5  # 72 klux
    RANGE_144K = 6  # 144 klux
    AUTO = 12  # Auto-range


class ConversionTime(CV):
    """Available conversion time settings for the OPT4048 sensor.

    These control the device conversion time per channel as described in datasheet page 29.

    +------------------------------------------+-------------------------+
    | Setting                                  | Time                    |
    +==========================================+=========================+
    | :py:const:`ConversionTime.TIME_600US`    | 600 microseconds        |
    +------------------------------------------+-------------------------+
    | :py:const:`ConversionTime.TIME_1MS`      | 1 millisecond           |
    +------------------------------------------+-------------------------+
    | :py:const:`ConversionTime.TIME_1_8MS`    | 1.8 milliseconds        |
    +------------------------------------------+-------------------------+
    | :py:const:`ConversionTime.TIME_3_4MS`    | 3.4 milliseconds        |
    +------------------------------------------+-------------------------+
    | :py:const:`ConversionTime.TIME_6_5MS`    | 6.5 milliseconds        |
    +------------------------------------------+-------------------------+
    | :py:const:`ConversionTime.TIME_12_7MS`   | 12.7 milliseconds       |
    +------------------------------------------+-------------------------+
    | :py:const:`ConversionTime.TIME_25MS`     | 25 milliseconds         |
    +------------------------------------------+-------------------------+
    | :py:const:`ConversionTime.TIME_50MS`     | 50 milliseconds         |
    +------------------------------------------+-------------------------+
    | :py:const:`ConversionTime.TIME_100MS`    | 100 milliseconds        |
    +------------------------------------------+-------------------------+
    | :py:const:`ConversionTime.TIME_200MS`    | 200 milliseconds        |
    +------------------------------------------+-------------------------+
    | :py:const:`ConversionTime.TIME_400MS`    | 400 milliseconds        |
    +------------------------------------------+-------------------------+
    | :py:const:`ConversionTime.TIME_800MS`    | 800 milliseconds        |
    +------------------------------------------+-------------------------+
    """

    TIME_600US = 0  # 600 microseconds
    TIME_1MS = 1  # 1 millisecond
    TIME_1_8MS = 2  # 1.8 milliseconds
    TIME_3_4MS = 3  # 3.4 milliseconds
    TIME_6_5MS = 4  # 6.5 milliseconds
    TIME_12_7MS = 5  # 12.7 milliseconds
    TIME_25MS = 6  # 25 milliseconds
    TIME_50MS = 7  # 50 milliseconds
    TIME_100MS = 8  # 100 milliseconds
    TIME_200MS = 9  # 200 milliseconds
    TIME_400MS = 10  # 400 milliseconds
    TIME_800MS = 11  # 800 milliseconds


class Mode(CV):
    """Available operating mode settings for the OPT4048 sensor.

    Controls the device mode of operation as described in datasheet page 29.

    +--------------------------------------+-------------------------+
    | Setting                              | Mode                    |
    +======================================+=========================+
    | :py:const:`Mode.POWERDOWN`           | Power-down mode         |
    +--------------------------------------+-------------------------+
    | :py:const:`Mode.AUTO_ONESHOT`        | Auto-range one-shot     |
    +--------------------------------------+-------------------------+
    | :py:const:`Mode.ONESHOT`             | One-shot mode           |
    +--------------------------------------+-------------------------+
    | :py:const:`Mode.CONTINUOUS`          | Continuous mode         |
    +--------------------------------------+-------------------------+
    """

    POWERDOWN = 0  # Power-down mode
    AUTO_ONESHOT = 1  # Forced auto-range one-shot mode
    ONESHOT = 2  # One-shot mode
    CONTINUOUS = 3  # Continuous mode


class FaultCount(CV):
    """Available fault count settings for the OPT4048 sensor.

    Controls how many consecutive fault events are needed to trigger an interrupt.

    +------------------------------------+-------------------------+
    | Setting                            | Count                   |
    +====================================+=========================+
    | :py:const:`FaultCount.COUNT_1`     | 1 fault count (default) |
    +------------------------------------+-------------------------+
    | :py:const:`FaultCount.COUNT_2`     | 2 consecutive faults    |
    +------------------------------------+-------------------------+
    | :py:const:`FaultCount.COUNT_4`     | 4 consecutive faults    |
    +------------------------------------+-------------------------+
    | :py:const:`FaultCount.COUNT_8`     | 8 consecutive faults    |
    +------------------------------------+-------------------------+
    """

    COUNT_1 = 0  # 1 fault count (default)
    COUNT_2 = 1  # 2 consecutive fault counts
    COUNT_4 = 2  # 4 consecutive fault counts
    COUNT_8 = 3  # 8 consecutive fault counts


class IntConfig(CV):
    """Interrupt configuration settings for the OPT4048 sensor.

    Controls the interrupt mechanism after end of conversion.

    +----------------------------------------+----------------------------------+
    | Setting                                | Configuration                    |
    +========================================+==================================+
    | :py:const:`IntConfig.SMBUS_ALERT`      | SMBUS Alert                      |
    +----------------------------------------+----------------------------------+
    | :py:const:`IntConfig.DATA_READY_NEXT`  | INT Pin data ready for next chan |
    +----------------------------------------+----------------------------------+
    | :py:const:`IntConfig.DATA_READY_ALL`   | INT Pin data ready for all chans |
    +----------------------------------------+----------------------------------+
    """

    SMBUS_ALERT = 0  # SMBUS Alert
    DATA_READY_NEXT = 1  # INT Pin data ready for next channel
    DATA_READY_ALL = 3  # INT Pin data ready for all channels


# Default I2C address (ADDR pin connected to GND)
_OPT4048_DEFAULT_ADDR = const(0x44)

# Register addresses
_OPT4048_REG_CH0_MSB = const(0x00)  # X channel MSB register
_OPT4048_REG_CH0_LSB = const(0x01)  # X channel LSB register
_OPT4048_REG_CH1_MSB = const(0x02)  # Y channel MSB register
_OPT4048_REG_CH1_LSB = const(0x03)  # Y channel LSB register
_OPT4048_REG_CH2_MSB = const(0x04)  # Z channel MSB register
_OPT4048_REG_CH2_LSB = const(0x05)  # Z channel LSB register
_OPT4048_REG_CH3_MSB = const(0x06)  # W channel MSB register
_OPT4048_REG_CH3_LSB = const(0x07)  # W channel LSB register
_OPT4048_REG_THRESHOLD_LOW = const(0x08)  # Low threshold register
_OPT4048_REG_THRESHOLD_HIGH = const(0x09)  # High threshold register
_OPT4048_REG_CONFIG = const(0x0A)  # Configuration register
_OPT4048_REG_THRESHOLD_CFG = const(0x0B)  # Threshold configuration register
_OPT4048_REG_STATUS = const(0x0C)  # Status register
_OPT4048_REG_DEVICE_ID = const(0x11)  # Device ID register

# Status register (0x0C) bit flags
OPT4048_FLAG_L = const(0x01)  # Flag low - measurement smaller than threshold
OPT4048_FLAG_H = const(0x02)  # Flag high - measurement larger than threshold
OPT4048_FLAG_CONVERSION_READY = const(0x04)  # Conversion ready
OPT4048_FLAG_OVERLOAD = const(0x08)  # Overflow condition


class OPT4048:  # noqa: PLR0904, too many public methods
    """Library for the OPT4048 Tristimulus XYZ Color Sensor

    :param ~busio.I2C i2c_bus: The I2C bus the device is connected to
    :param int address: The I2C device address. Defaults to :const:`0x44`

    **Quickstart: Importing and using the device**

        Here is an example of using the :class:`OPT4048`.
        First you will need to import the libraries to use the sensor

        .. code-block:: python

            import board
            from adafruit_opt4048 import OPT4048

        Once this is done you can define your `board.I2C` object and define your sensor object

        .. code-block:: python

            i2c = board.I2C()  # uses board.SCL and board.SDA
            sensor = OPT4048(i2c)

        Now you have access to the color data

        .. code-block:: python

            x, y, z, w = sensor.color_data
    """

    # _device_id = ROBits(16, _OPT4048_REG_DEVICE_ID, 0, register_width=2, lsb_first=False)
    _device_id = UnaryStruct(_OPT4048_REG_DEVICE_ID, ">H")
    _interrupt_direction = RWBit(_OPT4048_REG_THRESHOLD_CFG, 4, register_width=2, lsb_first=False)
    _interrupt_config = RWBits(2, _OPT4048_REG_THRESHOLD_CFG, 2, register_width=2, lsb_first=False)
    _interrupt_latch = RWBit(_OPT4048_REG_CONFIG, 3, register_width=2, lsb_first=False)
    _interrupt_polarity = RWBit(_OPT4048_REG_CONFIG, 2, register_width=2, lsb_first=False)
    _range = RWBits(4, _OPT4048_REG_CONFIG, 10, register_width=2, lsb_first=False)
    _conversion_time = RWBits(4, _OPT4048_REG_CONFIG, 6, register_width=2, lsb_first=False)
    _mode = RWBits(2, _OPT4048_REG_CONFIG, 4, register_width=2, lsb_first=False)
    _quick_wake = RWBit(_OPT4048_REG_CONFIG, 15, register_width=2, lsb_first=False)
    _fault_count = RWBits(2, _OPT4048_REG_CONFIG, 0, register_width=2, lsb_first=False)
    _threshold_channel = RWBits(2, _OPT4048_REG_THRESHOLD_CFG, 5, register_width=2, lsb_first=False)

    # Threshold Low register bits (register 0x08)
    _threshold_low_exponent = RWBits(
        4, _OPT4048_REG_THRESHOLD_LOW, 12, register_width=2, lsb_first=False
    )
    _threshold_low_mantissa = RWBits(
        12, _OPT4048_REG_THRESHOLD_LOW, 0, register_width=2, lsb_first=False
    )

    # Threshold High register bits (register 0x09)
    _threshold_high_exponent = RWBits(
        4, _OPT4048_REG_THRESHOLD_HIGH, 12, register_width=2, lsb_first=False
    )
    _threshold_high_mantissa = RWBits(
        12, _OPT4048_REG_THRESHOLD_HIGH, 0, register_width=2, lsb_first=False
    )
    _all_channels_raw = RWBits(
        16 * 8, _OPT4048_REG_CH0_MSB, 0, register_width=2 * 8, lsb_first=False
    )
    _flags = ROBits(4, _OPT4048_REG_STATUS, 0, register_width=2, lsb_first=False)

    def __init__(self, i2c_bus, address=_OPT4048_DEFAULT_ADDR):
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
        self.init()

    def init(self):
        """Initialize the sensor and verify the device ID"""
        # Check device ID
        if self._device_id != _OPT4048_CHIP_ID:
            raise RuntimeError("Failed to find an OPT4048 sensor - check your wiring!")

        # Initialize the sensor with default settings
        self.interrupt_direction = True
        self.interrupt_config = IntConfig.DATA_READY_ALL
        self.interrupt_latch = True
        self.interrupt_polarity = True  # Use active-high interrupts by default
        self.interrupt_config = IntConfig.DATA_READY_ALL

    @property
    def interrupt_direction(self):
        """Get the current interrupt direction setting.

        Returns True if interrupts are generated when measurement > high threshold,
        False if interrupts are generated when measurement < low threshold.
        """
        return self._interrupt_direction

    @interrupt_direction.setter
    def interrupt_direction(self, value):
        """Set the direction of interrupt generation.

        :param bool value: True for interrupt when measurement > high threshold,
                          False for interrupt when measurement < low threshold
        """
        self._interrupt_direction = value

    @property
    def interrupt_config(self):
        """Get the current interrupt configuration.

        Returns the current interrupt configuration mode.
        See IntConfig class for valid values.
        """
        return self._interrupt_config

    @interrupt_config.setter
    def interrupt_config(self, value):
        """Set the interrupt configuration.

        :param int value: The interrupt configuration value.
                         Must be a valid IntConfig value.
        """
        if not IntConfig.is_valid(value):
            raise ValueError("Interrupt configuration must be a valid IntConfig value")
        self._interrupt_config = value

    @property
    def interrupt_latch(self):
        """Get the current interrupt latch setting.

        Returns True if interrupts are latched (interrupt flag remains active until
        register is read), False if interrupts are transparent (interrupt flag
        is updated with each measurement).
        """
        return self._interrupt_latch

    @interrupt_latch.setter
    def interrupt_latch(self, value):
        """Set the interrupt latch mode.

        :param bool value: True for latched interrupts (interrupt flag remains active
                          until register is read), False for transparent interrupts
                          (interrupt flag is updated with each measurement)
        """
        self._interrupt_latch = value

    @property
    def interrupt_polarity(self):
        """Get the current interrupt pin polarity setting.

        Returns True if interrupts are active-high (1 = interrupt active),
        False if interrupts are active-low (0 = interrupt active).
        """
        return self._interrupt_polarity

    @interrupt_polarity.setter
    def interrupt_polarity(self, value):
        """Set the interrupt pin polarity.

        :param bool value: True for active-high interrupts (1 = interrupt active),
                          False for active-low interrupts (0 = interrupt active)
        """
        self._interrupt_polarity = value

    @property
    def range(self):
        """Get the current range setting for light measurements.

        Returns the current range setting from the Range enum.
        This controls the full-scale light level range of the device.

        See the Range class for valid values:
        - Range.RANGE_2K: 2.2 klux
        - Range.RANGE_4K: 4.5 klux
        - Range.RANGE_9K: 9 klux
        - Range.RANGE_18K: 18 klux
        - Range.RANGE_36K: 36 klux
        - Range.RANGE_72K: 72 klux
        - Range.RANGE_144K: 144 klux
        - Range.AUTO: Auto-range
        """
        return self._range

    @range.setter
    def range(self, value):
        """Set the range for light measurements.

        :param int value: The range setting to use from Range enum.
                          Controls the full-scale light level range.
                          Must be a valid Range value.
        """
        if not Range.is_valid(value):
            raise ValueError("Range setting must be a valid Range value")
        self._range = value

    @property
    def conversion_time(self):
        """Get the current conversion time setting for the OPT4048 sensor.

        Returns the current conversion time setting from the ConversionTime enum.
        This controls the device conversion time per channel.

        See the ConversionTime class for valid values:
        - ConversionTime.TIME_600US: 600 microseconds
        - ConversionTime.TIME_1MS: 1 millisecond
        - ConversionTime.TIME_1_8MS: 1.8 milliseconds
        - ConversionTime.TIME_3_4MS: 3.4 milliseconds
        - ConversionTime.TIME_6_5MS: 6.5 milliseconds
        - ConversionTime.TIME_12_7MS: 12.7 milliseconds
        - ConversionTime.TIME_25MS: 25 milliseconds
        - ConversionTime.TIME_50MS: 50 milliseconds
        - ConversionTime.TIME_100MS: 100 milliseconds
        - ConversionTime.TIME_200MS: 200 milliseconds
        - ConversionTime.TIME_400MS: 400 milliseconds
        - ConversionTime.TIME_800MS: 800 milliseconds
        """
        return self._conversion_time

    @conversion_time.setter
    def conversion_time(self, value):
        """Set the conversion time for light measurements.

        :param int value: The conversion time setting to use from ConversionTime enum.
                          Controls the device conversion time per channel.
                          Must be a valid ConversionTime value.
        """
        if not ConversionTime.is_valid(value):
            raise ValueError("Conversion time setting must be a valid ConversionTime value")
        self._conversion_time = value

    @property
    def mode(self):
        """Get the current operating mode setting for the OPT4048 sensor.

        Returns the current operating mode setting from the Mode enum.
        This controls the device operating mode.

        See the Mode class for valid values:
        - Mode.POWERDOWN: Power-down mode
        - Mode.AUTO_ONESHOT: Auto-range one-shot mode
        - Mode.ONESHOT: One-shot mode
        - Mode.CONTINUOUS: Continuous mode
        """
        return self._mode

    @mode.setter
    def mode(self, value):
        """Set the operating mode of the sensor.

        :param int value: The operating mode setting to use from Mode enum.
                          Controls the device's operating mode.
                          Must be a valid Mode value.
        """
        if not Mode.is_valid(value):
            raise ValueError("Mode setting must be a valid Mode value")
        self._mode = value

    @property
    def quick_wake(self):
        """Get the current state of the Quick Wake feature.

        Quick Wake controls whether the sensor powers down completely in one-shot mode.
        When enabled, the sensor doesn't power down all circuits in one-shot mode,
        allowing faster wake-up from standby with a penalty in power consumption
        compared to full standby mode.

        Returns True if Quick Wake is enabled, False if disabled.
        """
        return self._quick_wake

    @quick_wake.setter
    def quick_wake(self, value):
        """Enable or disable Quick Wake-up feature.

        :param bool value: True to enable Quick Wake, False to disable.
                          When enabled, the sensor doesn't power down completely
                          in one-shot mode, allowing faster wake-up with higher
                          power consumption.
        """
        self._quick_wake = value

    @property
    def fault_count(self):
        """Get the current fault count setting.

        Returns the current fault count setting from the FaultCount enum.
        This controls how many consecutive measurements must be above/below
        thresholds before an interrupt is triggered.

        See the FaultCount class for valid values:
        - FaultCount.COUNT_1: 1 fault count (default)
        - FaultCount.COUNT_2: 2 consecutive faults
        - FaultCount.COUNT_4: 4 consecutive faults
        - FaultCount.COUNT_8: 8 consecutive faults
        """
        return self._fault_count

    @fault_count.setter
    def fault_count(self, value):
        """Set the fault count for interrupt generation.

        :param int value: The fault count setting to use from FaultCount enum.
                          Controls how many consecutive measurements must be
                          above/below thresholds before an interrupt is triggered.
                          Must be a valid FaultCount value.
        """
        if not FaultCount.is_valid(value):
            raise ValueError("Fault count setting must be a valid FaultCount value")
        self._fault_count = value

    @property
    def threshold_channel(self):
        """Get the channel currently used for threshold comparison.

        Returns the channel number (0-3) currently used for threshold comparison:
        - 0 = Channel 0 (X)
        - 1 = Channel 1 (Y)
        - 2 = Channel 2 (Z)
        - 3 = Channel 3 (W)
        """
        return self._threshold_channel

    @threshold_channel.setter
    def threshold_channel(self, value):
        """Set the channel to be used for threshold comparison.

        :param int value: Channel number (0-3) to use for threshold comparison:
                          0 = Channel 0 (X)
                          1 = Channel 1 (Y)
                          2 = Channel 2 (Z)
                          3 = Channel 3 (W)
        """
        if not isinstance(value, int) or value < 0 or value > 3:
            raise ValueError("Threshold channel must be an integer between 0 and 3")
        self._threshold_channel = value

    @property
    def threshold_low(self):
        """Get the current low threshold value.

        Returns the current low threshold value as a 32-bit integer.
        This value determines when a low threshold interrupt is generated
        when interrupt_direction is False.
        """
        # Read the exponent and mantissa from the threshold low register
        exponent = self._threshold_low_exponent
        mantissa = self._threshold_low_mantissa
        # Calculate ADC code value by applying the exponent as a bit shift
        # ADD 8 to the exponent as per datasheet equations 12-13
        return mantissa << (8 + exponent)

    @threshold_low.setter
    def threshold_low(self, value):
        """Set the low threshold value for interrupt generation.

        :param int value: The low threshold value as a 32-bit integer
        """
        # Find the appropriate exponent and mantissa values that represent the threshold
        exponent = 0
        mantissa = value

        # The mantissa needs to fit in 12 bits, so we start by shifting right
        # to determine how many shifts we need (which gives us the exponent)
        # Note that the threshold registers already have 8 added to exponent
        # internally so we first subtract 8 from our target exponent
        if mantissa > 0xFFF:  # If value won't fit in 12 bits
            while mantissa > 0xFFF and exponent < 15:
                mantissa >>= 1
                exponent += 1
            if mantissa > 0xFFF:  # If still won't fit with max exponent, clamp
                mantissa = 0xFFF
                exponent = 15 - 8  # Max exponent (15) minus the 8 that's added internally

        # Write the exponent and mantissa to the register
        self._threshold_low_exponent = exponent
        self._threshold_low_mantissa = mantissa

    @property
    def threshold_high(self):
        """Get the current high threshold value.

        Returns the current high threshold value as a 32-bit integer.
        This value determines when a high threshold interrupt is generated
        when interrupt_direction is True.
        """
        # Read the exponent and mantissa from the threshold high register
        exponent = self._threshold_high_exponent
        mantissa = self._threshold_high_mantissa

        # Calculate ADC code value by applying the exponent as a bit shift
        # ADD 8 to the exponent as per datasheet equations 10-11
        return mantissa << (8 + exponent)

    @threshold_high.setter
    def threshold_high(self, value):
        """Set the high threshold value for interrupt generation.

        :param int value: The high threshold value as a 32-bit integer
        """
        # Find the appropriate exponent and mantissa values that represent the threshold
        exponent = 0
        mantissa = value

        # The mantissa needs to fit in 12 bits, so we start by shifting right
        # to determine how many shifts we need (which gives us the exponent)
        # Note that the threshold registers already have 8 added to exponent
        # internally so we first subtract 8 from our target exponent
        if mantissa > 0xFFF:  # If value won't fit in 12 bits
            while mantissa > 0xFFF and exponent < 15:
                mantissa >>= 1
                exponent += 1
            if mantissa > 0xFFF:  # If still won't fit with max exponent, clamp
                mantissa = 0xFFF
                exponent = 15 - 8  # Max exponent (15) minus the 8 that's added internally

        # Write the exponent and mantissa to the register
        self._threshold_high_exponent = exponent
        self._threshold_high_mantissa = mantissa

    @property
    def all_channels(self):
        """Read all four channels, verify CRC, and return raw ADC code values.

        Reads registers for channels 0-3 in one burst, checks the CRC bits for each,
        and computes the raw ADC code values.

        :return: Tuple of 4 raw channel values (X, Y, Z, W) if successful
        :rtype: Tuple[int, int, int, int]
        :raises RuntimeError: If CRC check fails for any channel
        """
        # Read all channels in one operation using the ROBits accessor
        all_channels_data = self._all_channels_raw

        # Process each channel's data
        channels = []

        for ch in range(4):
            # Extract channel data from the appropriate position in the buffer
            # Each channel has 4 bytes (32 bits) of data
            channel_offset = ch * 32

            # Extract exponent (4 bits), MSB (12 bits), LSB (8 bits), and counter/CRC (8 bits)
            exp = (all_channels_data >> (channel_offset + 28)) & 0xF
            msb = (all_channels_data >> (channel_offset + 16)) & 0xFFF
            lsb = (all_channels_data >> (channel_offset + 8)) & 0xFF
            counter = (all_channels_data >> (channel_offset + 4)) & 0xF
            crc = all_channels_data >> channel_offset & 0xF

            # Combine MSB and LSB to form the 20-bit mantissa
            mant = (msb << 8) | lsb
            # Calculate CRC
            # Initialize CRC variables
            x0 = 0  # CRC bit 0
            x1 = 0  # CRC bit 1
            x2 = 0  # CRC bit 2
            x3 = 0  # CRC bit 3

            # Calculate bit 0 (x0): XOR of all bits
            # XOR all exponent bits
            for i in range(4):
                x0 ^= (exp >> i) & 1

            # XOR all mantissa bits
            for i in range(20):
                x0 ^= (mant >> i) & 1

            # XOR all counter bits
            for i in range(4):
                x0 ^= (counter >> i) & 1

            # Calculate bit 1 (x1)
            # Include counter bits 1 and 3
            x1 ^= (counter >> 1) & 1  # COUNTER_CHx[1]
            x1 ^= (counter >> 3) & 1  # COUNTER_CHx[3]

            # Include odd-indexed mantissa bits
            for i in range(1, 20, 2):
                x1 ^= (mant >> i) & 1

            # Include exponent bits 1 and 3
            x1 ^= (exp >> 1) & 1  # E[1]
            x1 ^= (exp >> 3) & 1  # E[3]

            # Calculate bit 2 (x2)
            # Include counter bit 3
            x2 ^= (counter >> 3) & 1  # COUNTER_CHx[3]

            # Include mantissa bits at positions 3,7,11,15,19
            for i in range(3, 20, 4):
                x2 ^= (mant >> i) & 1

            # Include exponent bit 3
            x2 ^= (exp >> 3) & 1  # E[3]

            # Calculate bit 3 (x3)
            # XOR mantissa bits at positions 3, 11, 19
            x3 ^= (mant >> 3) & 1  # R[3]
            x3 ^= (mant >> 11) & 1  # R[11]
            x3 ^= (mant >> 19) & 1  # R[19]

            # Combine bits to form the CRC
            calculated_crc = (x3 << 3) | (x2 << 2) | (x1 << 1) | x0

            # Verify CRC
            if crc != calculated_crc:
                raise RuntimeError(f"CRC check failed for channel {ch}")

            # Convert to raw ADC value format (mantissa << exponent)
            output = mant << exp

            # Add to channels list
            # channels.append(output)
            channels.insert(0, output)

        # Return all four channels (X, Y, Z, W)
        return tuple(channels)

    @property
    def xyz(self):
        """Calculate CIE XYZ tristimulus values from raw sensor channels.

        Uses the 3 channel of OPT4048 outputs and applies the transformation
        matrix from the datasheet.

        :return: Tuple of (X, Y, Z) tristimulus values
        :rtype: Tuple[float, float, float]
        """
        # Read all four channels
        ch0, ch1, ch2, ch3 = self.all_channels

        # Matrix multiplication coefficients (from datasheet)
        m0x = 2.34892992e-04
        m0y = -1.89652390e-05
        m0z = 1.20811684e-05

        m1x = 4.07467441e-05
        m1y = 1.98958202e-04
        m1z = -1.58848115e-05

        m2x = 9.28619404e-05
        m2y = -1.69739553e-05
        m2z = 6.74021520e-04

        m3x = 0
        m3y = 0
        m3z = 0

        # Matrix multiplication to calculate X, Y, Z, L values
        # [ch0 ch1 ch2 ch3] * [m0x m0y m0z m0l] = [X Y Z Lux]
        #                     [m1x m1y m1z m1l]
        #                     [m2x m2y m2z m2l]
        #                     [m3x m3y m3z m3l]

        # Matrix multiplication for XYZ
        x = ch0 * m0x + ch1 * m1x + ch2 * m2x + ch3 * m3x
        y = ch0 * m0y + ch1 * m1y + ch2 * m2y + ch3 * m3y
        z = ch0 * m0z + ch1 * m1z + ch2 * m2z + ch3 * m3z

        return x, y, z

    @property
    def cie(self):
        """Calculate CIE chromaticity (x, y) and LUX.

        CIE values are calculated from the x, y, z value from the xyz() function.
        LUX value estimated using the OPT4048 raw values together transformation
        matrix from the datasheet.

        :return: Tuple (cie_x, cie_y, lux)
        :rtype: Tuple[float, float, float]
        """

        # for lux calculation
        ch0, ch1, ch2, ch3 = self.all_channels  # noqa: F841, local var not used

        # Calculate lux
        lux = ch1 * 2.15e-03

        x, y, z = self.xyz

        # Calculate CIE x, y chromaticity coordinates
        sum_xyz = x + y + z
        # ---- Clamp negatives (no negative light) ----
        x = max(0.0, x)
        y = max(0.0, y)
        z = max(0.0, z)

        if sum_xyz <= 0:
            # Avoid division by zero
            return 0.0, 0.0, 0.0

        cie_x = x / sum_xyz
        cie_y = y / sum_xyz

        return cie_x, cie_y, lux

    @property
    def normalized_xyz(self):
        """Normalize XYZ values so their sum becomes 1.0.

        This removes brightness influence and keeps the values in a valid range.

        :return: Tuple (Xn, Yn, Zn)
        :rtype: Tuple[float, float, float]
        """
        X, Y, Z = self.xyz

        # Clamp negatives or very small to avoid invalid normalization
        X = 0 if X < 0.5 else X
        Y = 0 if Y < 0.3 else Y
        Z = 0 if Z < 0.3 else Z

        SUM = X + Y + Z

        if SUM == 0:
            # Avoid division by zero → return (0,0,0) or some fallback
            return (0.0, 0.0, 0.0)

        Xn = X / SUM
        Yn = Y / SUM
        Zn = Z / SUM

        # Clamp each to max 1.0
        Xn = min(Xn, 1.0)
        Yn = min(Yn, 1.0)
        Zn = min(Zn, 1.0)

        return (Xn, Yn, Zn)

    @property
    def rgb(self):
        """convert xyz value to rgb and return illuminance (lux) value.

        Based on the XYZ normalized value from normalizedtosum().
        reference: https://www.oceanopticsbook.info/view/photometry-and-visibility/from-xyz-to-rgb

        :return: Tuple (r, g, b, lux)
        :rtype: Tuple[int, int, int, float]
        """

        x, y, z = self.normalized_xyz

        # Get lux value
        _, _, lux = self.cie

        # Convert normalized XYZ to RGB

        # Convert XYZ to linear RGB (sRGB)
        r_lin = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z
        g_lin = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
        b_lin = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z

        # Clamp negatives (no negative light)
        r_lin = max(0.0, r_lin)
        g_lin = max(0.0, g_lin)
        b_lin = max(0.0, b_lin)

        # Gamma correction (sRGB standard)
        def gamma_correct(c):
            if c <= 0.0031308:
                return 12.92 * c
            else:
                return 1.055 * (c ** (1 / 2.4)) - 0.055

        r = gamma_correct(r_lin)
        g = gamma_correct(g_lin)
        b = gamma_correct(b_lin)

        # Scale to 0–255 and clamp
        r = int(min(max(r * 255, 0), 255))
        g = int(min(max(g * 255, 0), 255))
        b = int(min(max(b * 255, 0), 255))

        return r, g, b, lux

    def calculate_color_temperature(self, cie_x, cie_y):
        """Calculate the correlated color temperature (CCT) in Kelvin.

        Uses McCamy's approximation formula to calculate CCT from CIE 1931 x,y
        coordinates. This is accurate for color temperatures between 2000K and
        30000K.

        Formula:
        n = (x - 0.3320) / (0.1858 - y)
        CCT = 437 * n^3 + 3601 * n^2 + 6861 * n + 5517

        :param float cie_x: CIE x chromaticity coordinate
        :param float cie_y: CIE y chromaticity coordinate
        :return: The calculated color temperature in Kelvin
        :rtype: float
        """
        # Check for invalid coordinates
        if cie_x == 0 and cie_y == 0:
            return 0.0

        # Calculate using McCamy's formula
        # n = (x - 0.3320) / (0.1858 - y)
        n = (cie_x - 0.3320) / (0.1858 - cie_y)

        # CCT = 437 * n^3 + 3601 * n^2 + 6861 * n + 5517
        cct = (437.0 * n * n * n) + (3601.0 * n * n) + (6861.0 * n) + 5517.0

        return cct

    @property
    def flags(self):
        """Get the current status flags.

        Reads the status register (0x0C) to determine the current state of various
        flags. Reading this register also clears latched interrupt flags.

        :return: 8-bit value where:
                 - bit 0 (0x01): FLAG_L - Flag low (measurement below threshold)
                 - bit 1 (0x02): FLAG_H - Flag high (measurement above threshold)
                 - bit 2 (0x04): CONVERSION_READY_FLAG - Conversion complete
                 - bit 3 (0x08): OVERLOAD_FLAG - Overflow condition
        :rtype: int
        """
        return self._flags
