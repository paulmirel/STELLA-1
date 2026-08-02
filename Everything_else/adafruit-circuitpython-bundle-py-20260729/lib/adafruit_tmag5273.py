# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industrie
#
# SPDX-License-Identifier: MIT
"""
`adafruit_tmag5273`
================================================================================

CircuitPython driver for the Adafruit TMAG5273 (A1 and A2) 3D Hall Effect Magnetometer Breakout


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit TMAG5273 (A1) 3D Hall Effect Magnetometer Breakout - ±40mT, ±80mT <https://www.adafruit.com/product/6489>`_
* `Adafruit TMAG5273 (A2) 3D Hall Effect Magnetometer Breakout - ±133mT / 266mT <https://www.adafruit.com/product/6490>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import struct
import time

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from micropython import const

try:
    from typing import Tuple

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.2"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_TMAG5273.git"

_DEFAULT_I2CADDR = const(0x35)

_DEVICE_CONFIG_1 = const(0x00)
_DEVICE_CONFIG_2 = const(0x01)
_SENSOR_CONFIG_1 = const(0x02)
_SENSOR_CONFIG_2 = const(0x03)
_X_THR_CONFIG = const(0x04)
_Y_THR_CONFIG = const(0x05)
_Z_THR_CONFIG = const(0x06)
_T_CONFIG = const(0x07)
_INT_CONFIG_1 = const(0x08)
_MAG_GAIN_CONFIG = const(0x09)
_MAG_OFFSET_1 = const(0x0A)
_MAG_OFFSET_2 = const(0x0B)
_I2C_ADDRESS = const(0x0C)
_DEVICE_ID = const(0x0D)
_MANUFACTURER_ID_LSB = const(0x0E)
_MANUFACTURER_ID_MSB = const(0x0F)
_T_MSB_RESULT = const(0x10)
_X_MSB_RESULT = const(0x12)
_Y_MSB_RESULT = const(0x14)
_Z_MSB_RESULT = const(0x16)
_CONV_STATUS = const(0x18)
_ANGLE_MSB_RESULT = const(0x19)
_MAGNITUDE_RESULT = const(0x1B)
_DEVICE_STATUS = const(0x1C)
_TEMP_ADC_T0 = const(17508)
_TEMP_SENS_T0 = 25.0
_TEMP_ADC_RES = 60.1
_MANUFACTURER_ID = const(0x5449)

# Conversion averaging options
CONV_AVG_1X = const(0x00)
"""1x conversion averaging."""
CONV_AVG_2X = const(0x01)
"""2x conversion averaging."""
CONV_AVG_4X = const(0x02)
"""4x conversion averaging."""
CONV_AVG_8X = const(0x03)
"""8x conversion averaging."""
CONV_AVG_16X = const(0x04)
"""16x conversion averaging."""
CONV_AVG_32X = const(0x05)
"""32x conversion averaging."""

# Magnetic channel enable options
MAG_CH_OFF = const(0x00)
"""All magnetic channels off."""
MAG_CH_X = const(0x01)
"""X channel only."""
MAG_CH_Y = const(0x02)
"""Y channel only."""
MAG_CH_XY = const(0x03)
"""X and Y channels."""
MAG_CH_Z = const(0x04)
"""Z channel only."""
MAG_CH_ZX = const(0x05)
"""Z and X channels."""
MAG_CH_YZ = const(0x06)
"""Y and Z channels."""
MAG_CH_XYZ = const(0x07)
"""X, Y, and Z channels."""
MAG_CH_XYX = const(0x08)
"""X, Y, X pseudo-simultaneous."""
MAG_CH_YXY = const(0x09)
"""Y, X, Y pseudo-simultaneous."""
MAG_CH_YZY = const(0x0A)
"""Y, Z, Y pseudo-simultaneous."""
MAG_CH_XZX = const(0x0B)
"""X, Z, X pseudo-simultaneous."""

# Sleep time options
SLEEP_1MS = const(0x00)
"""1ms sleep time."""
SLEEP_5MS = const(0x01)
"""5ms sleep time."""
SLEEP_10MS = const(0x02)
"""10ms sleep time."""
SLEEP_15MS = const(0x03)
"""15ms sleep time."""
SLEEP_20MS = const(0x04)
"""20ms sleep time."""
SLEEP_30MS = const(0x05)
"""30ms sleep time."""
SLEEP_50MS = const(0x06)
"""50ms sleep time."""
SLEEP_100MS = const(0x07)
"""100ms sleep time."""
SLEEP_500MS = const(0x08)
"""500ms sleep time."""
SLEEP_1000MS = const(0x09)
"""1000ms sleep time."""
SLEEP_2000MS = const(0x0A)
"""2000ms sleep time."""
SLEEP_5000MS = const(0x0B)
"""5000ms sleep time."""
SLEEP_20000MS = const(0x0C)
"""20000ms sleep time."""

# Operating mode options
MODE_STANDBY = const(0x00)
"""Standby (trigger) mode."""
MODE_SLEEP = const(0x01)
"""Sleep mode (ultra-low power)."""
MODE_CONTINUOUS = const(0x02)
"""Continuous measurement mode."""
MODE_WAKEUP_SLEEP = const(0x03)
"""Wake-up and sleep mode."""

# Magnet temperature coefficient options
TEMPCO_NONE = const(0x00)
"""No temperature compensation (0%)."""
TEMPCO_NDFEB = const(0x01)
"""0.12%/°C compensation for NdFeB magnets."""
TEMPCO_CERAMIC = const(0x03)
"""0.2%/°C compensation for ceramic/ferrite magnets."""

# Angle calculation options
ANGLE_OFF = const(0x00)
"""No angle calculation."""
ANGLE_XY = const(0x01)
"""Angle from X (1st) and Y (2nd) axes."""
ANGLE_YZ = const(0x02)
"""Angle from Y (1st) and Z (2nd) axes."""
ANGLE_XZ = const(0x03)
"""Angle from X (1st) and Z (2nd) axes."""

# Interrupt mode options
INT_NONE = const(0x00)
"""No interrupt."""
INT_THROUGH_INT = const(0x01)
"""Interrupt through INT pin."""
INT_EXCEPT_I2C = const(0x02)
"""Interrupt through INT except during I2C."""
INT_THROUGH_SCL = const(0x03)
"""Interrupt through SCL pin."""
INT_SCL_EXCEPT_I2C = const(0x04)
"""Interrupt through SCL except during I2C."""


class TMAG5273:
    """Driver for the TI TMAG5273 3-axis Hall-effect magnetic sensor.

    :param ~busio.I2C i2c_bus: The I2C bus the sensor is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x35`.
    """

    # --- Device Config 1 (0x00) ---
    crc_enabled = RWBit(_DEVICE_CONFIG_1, 7)
    """Whether CRC is enabled for I2C communication."""
    mag_tempco = RWBits(2, _DEVICE_CONFIG_1, 5)
    """The magnet temperature compensation setting. Use one of the ``TEMPCO_*`` constants."""
    conversion_average = RWBits(3, _DEVICE_CONFIG_1, 2)
    """The conversion averaging setting. Use one of the ``CONV_AVG_*`` constants."""

    # --- Device Config 2 (0x01) ---
    low_noise = RWBit(_DEVICE_CONFIG_2, 4)
    """Whether low-noise mode is enabled. When ``False``, low-power mode is used."""
    operating_mode = RWBits(2, _DEVICE_CONFIG_2, 0)
    """The operating mode. Use one of the ``MODE_*`` constants."""

    # --- Sensor Config 1 (0x02) ---
    magnetic_channels = RWBits(4, _SENSOR_CONFIG_1, 4)
    """The magnetic channel configuration. Use one of the ``MAG_CH_*`` constants."""
    sleep_time = RWBits(4, _SENSOR_CONFIG_1, 0)
    """The sleep time for wake-up and sleep mode. Use one of the ``SLEEP_*`` constants."""

    # --- Sensor Config 2 (0x03) ---
    angle_calculation = RWBits(2, _SENSOR_CONFIG_2, 2)
    """The angle calculation axis pair. Use one of the ``ANGLE_*`` constants."""
    _xy_range = RWBit(_SENSOR_CONFIG_2, 1)
    _z_range = RWBit(_SENSOR_CONFIG_2, 0)

    # --- Threshold Config ---
    x_threshold = UnaryStruct(_X_THR_CONFIG, "<b")
    """The X-axis threshold as a signed 8-bit value."""
    y_threshold = UnaryStruct(_Y_THR_CONFIG, "<b")
    """The Y-axis threshold as a signed 8-bit value."""
    z_threshold = UnaryStruct(_Z_THR_CONFIG, "<b")
    """The Z-axis threshold as a signed 8-bit value."""

    # --- Temperature Config (0x07) ---
    temperature_threshold = RWBits(7, _T_CONFIG, 1)
    """The temperature threshold (7-bit, 8°C per LSB)."""
    temperature_enabled = RWBit(_T_CONFIG, 0)
    """Whether the temperature measurement channel is enabled."""

    # --- Interrupt Config 1 (0x08) ---
    result_interrupt = RWBit(_INT_CONFIG_1, 7)
    """Whether the conversion-complete result interrupt is enabled."""
    threshold_interrupt = RWBit(_INT_CONFIG_1, 6)
    """Whether the threshold interrupt is enabled."""
    interrupt_pulsed = RWBit(_INT_CONFIG_1, 5)
    """Whether the interrupt pin uses pulsed mode (10us pulse).
    When ``False``, latched mode is used."""
    interrupt_mode = RWBits(3, _INT_CONFIG_1, 2)
    """The interrupt mode. Use one of the ``INT_*`` constants."""

    # --- Gain and Offset ---
    gain_value = UnaryStruct(_MAG_GAIN_CONFIG, "<B")
    """The gain correction value (0-255, where 0 means 1.0 gain)."""
    offset1 = UnaryStruct(_MAG_OFFSET_1, "<b")
    """The first axis offset correction as a signed 8-bit value."""
    offset2 = UnaryStruct(_MAG_OFFSET_2, "<b")
    """The second axis offset correction as a signed 8-bit value."""

    # --- Read-only Registers ---
    device_id = ROUnaryStruct(_DEVICE_ID, "<B")
    """The 8-bit device ID register value."""
    conversion_status = ROUnaryStruct(_CONV_STATUS, "<B")
    """The conversion status register byte."""
    device_status = ROUnaryStruct(_DEVICE_STATUS, "<B")
    """The device status register byte."""
    _magnitude_raw = ROUnaryStruct(_MAGNITUDE_RESULT, "<B")

    def __init__(self, i2c_bus: I2C, address: int = _DEFAULT_I2CADDR) -> None:
        self.i2c_device = I2CDevice(i2c_bus, address)

        time.sleep(0.001)
        if self.manufacturer_id != _MANUFACTURER_ID:
            raise RuntimeError(f"Failed to find TMAG5273, found: 0x{self.manufacturer_id:04X}")

        ver = self.device_id & 0x03
        self._is_x2 = ver == 0x02

        if self._is_x2:
            self._range_xy = 133.0
            self._range_z = 133.0
        else:
            self._range_xy = 40.0
            self._range_z = 40.0

        self.magnetic_channels = MAG_CH_XYZ
        self.xy_range_wide = True
        self.z_range_wide = True
        self.conversion_average = CONV_AVG_32X
        self.operating_mode = MODE_CONTINUOUS
        self.temperature_enabled = True
        self.low_noise = True
        self.mag_tempco = TEMPCO_NDFEB
        self.angle_calculation = ANGLE_XY
        self.interrupt_mode = INT_THROUGH_INT
        self.result_interrupt = True

    @property
    def manufacturer_id(self) -> int:
        """The 16-bit manufacturer ID. Should be ``0x5449`` (\"TI\")."""
        buf = bytearray(2)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([_MANUFACTURER_ID_LSB]), buf)
        return buf[0] | (buf[1] << 8)

    @property
    def xy_range_wide(self) -> bool:
        """Whether XY axes use wide range (80mT for x1 / 266mT for x2).
        When ``False``, narrow range is used (40mT for x1 / 133mT for x2).
        """
        return self._xy_range

    @xy_range_wide.setter
    def xy_range_wide(self, value: bool) -> None:
        self._xy_range = value
        if self._is_x2:
            self._range_xy = 266.0 if value else 133.0
        else:
            self._range_xy = 80.0 if value else 40.0

    @property
    def z_range_wide(self) -> bool:
        """Whether Z axis uses wide range (80mT for x1 / 266mT for x2).
        When ``False``, narrow range is used (40mT for x1 / 133mT for x2).
        """
        return self._z_range

    @z_range_wide.setter
    def z_range_wide(self, value: bool) -> None:
        self._z_range = value
        if self._is_x2:
            self._range_z = 266.0 if value else 133.0
        else:
            self._range_z = 80.0 if value else 40.0

    def _read_raw_16(self, register: int) -> int:
        buf = bytearray(2)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([register]), buf)
        return struct.unpack(">h", buf)[0]

    @staticmethod
    def _raw_to_microtesla(raw: int, range_mt: float) -> float:
        return (raw / 32768.0) * range_mt * 1000.0

    @property
    def magnetic(self) -> Tuple[float, float, float]:
        """The magnetic field readings for X, Y, and Z axes in microTesla,
        as a 3-tuple ``(x, y, z)``.
        """
        raw_x = self._read_raw_16(_X_MSB_RESULT)
        raw_y = self._read_raw_16(_Y_MSB_RESULT)
        raw_z = self._read_raw_16(_Z_MSB_RESULT)
        return (
            self._raw_to_microtesla(raw_x, self._range_xy),
            self._raw_to_microtesla(raw_y, self._range_xy),
            self._raw_to_microtesla(raw_z, self._range_z),
        )

    @property
    def temperature(self) -> float:
        """The temperature reading in degrees Celsius."""
        raw = self._read_raw_16(_T_MSB_RESULT)
        return _TEMP_SENS_T0 + ((raw - _TEMP_ADC_T0) / _TEMP_ADC_RES)

    @property
    def angle(self) -> float:
        """The calculated angle in degrees (0-360) based on the configured
        axis pair (see :attr:`angle_calculation`).
        """
        buf = bytearray(2)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([_ANGLE_MSB_RESULT]), buf)
        raw = struct.unpack(">H", buf)[0] & 0x1FFF
        return float(raw >> 4) + ((raw & 0x0F) / 16.0)

    @property
    def magnitude(self) -> int:
        """The raw 8-bit magnitude value."""
        return self._magnitude_raw

    @property
    def magnitude_mt(self) -> float:
        """The calculated magnitude in milliTesla for the configured angle
        axis pair.
        """
        raw = self._magnitude_raw
        angle_mode = self.angle_calculation
        if angle_mode in {ANGLE_XZ, ANGLE_YZ}:
            range_val = max(self._range_xy, self._range_z)
        else:
            range_val = self._range_xy
        return float(raw) * range_val / 128.0

    def trigger_conversion(self) -> None:
        """Trigger a single conversion when in standby mode.

        Briefly switches to continuous mode to initiate a conversion,
        then returns to standby.
        """
        self.operating_mode = MODE_CONTINUOUS
        time.sleep(0.005)
        self.operating_mode = MODE_STANDBY
