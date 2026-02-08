# SPDX-FileCopyrightText: Copyright (c) 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_ina23x`
================================================================================

CircuitPython driver for the INA237 and INA238 DC Current Voltage Power Monitors


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit INA237 Breakout <https://www.adafruit.com/product/6340>`_
* `Adafruit INA238 Breakout <https://www.adafruit.com/product/6349>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
* Adafruit CircuitPython INA228 library: https://github.com/adafruit/Adafruit_CircuitPython_INA228
"""

import time

from adafruit_ina228 import INA2XX, AlertType
from adafruit_register.i2c_bit import ROBit
from adafruit_register.i2c_bits import ROBits, RWBits
from adafruit_register.i2c_struct import ROUnaryStruct
from micropython import const

try:
    import typing  # pylint: disable=unused-import

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_INA23x.git"

_SOVL = const(0x0C)  # Shunt Overvoltage Threshold
_SUVL = const(0x0D)  # Shunt Undervoltage Threshold
_BOVL = const(0x0E)  # Bus Overvoltage Threshold
_BUVL = const(0x0F)  # Bus Undervoltage Threshold
_TEMPLIMIT = const(0x10)  # Temperature Over-Limit Threshold
_PWRLIMIT = const(0x11)  # Power Over-Limit Threshold

# Constants
_INA237_DEVICE_ID = const(0x237)
_INA238_DEVICE_ID = const(0x238)


class INA23X(INA2XX):  # noqa: PLR0904
    """Driver for the INA237/INA238 current and power sensor.

    :param ~busio.I2C i2c_bus: The I2C bus the INA23X is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x40`
    :param bool skip_reset: Skip resetting the device on init. Defaults to False.
    """

    # INA23X-specific register bits
    _alert_type = RWBits(7, 0x0B, 5, register_width=2, lsb_first=False)
    _conversion_ready = ROBit(0x0B, 1, register_width=2, lsb_first=False)
    _alert_flags = ROBits(12, 0x0B, 0, register_width=2, lsb_first=False)

    _raw_vshunt = ROUnaryStruct(0x04, ">h")
    _raw_current = ROUnaryStruct(0x07, ">h")
    _raw_power = ROUnaryStruct(0x08, ">H")

    def __init__(self, i2c_bus: I2C, address: int = 0x40, skip_reset: bool = False) -> None:
        super().__init__(i2c_bus, address, skip_reset)

        # Verify device ID (both INA237 and INA238 use compatible IDs)
        if self.device_id not in {_INA237_DEVICE_ID, _INA238_DEVICE_ID}:
            raise ValueError("Failed to find INA237/INA238 - incorrect device ID")

        # Set INA23X defaults
        self.set_calibration(0.015, 10.0)

    def set_calibration(self, shunt_res: float = 0.015, max_current: float = 10.0) -> None:
        """Set the calibration based on shunt resistance and maximum expected current.

        :param float shunt_res: Shunt resistance in ohms
        :param float max_current: Maximum expected current in amperes
        """
        self._shunt_res = shunt_res
        # INA237/238 uses 2^15 as divisor
        self._current_lsb = max_current / (1 << 15)
        self._update_shunt_cal()

    def _update_shunt_cal(self) -> None:
        """Update the shunt calibration register."""
        # Scale factor based on ADC range
        scale = 4 if self._adc_range else 1

        # INA237/238 formula: SHUNT_CAL = 819.2 × 10^6 × CURRENT_LSB × RSHUNT × scale
        shunt_cal = int(819.2e6 * self._current_lsb * self._shunt_res * scale)
        self._shunt_cal = min(shunt_cal, 0xFFFF)

    @property
    def die_temperature(self) -> float:
        """Die temperature in degrees Celsius."""
        # INA237/238 uses 12 bits (15:4) with 125 m°C/LSB
        return (self._raw_dietemp >> 4) * 0.125

    @property
    def bus_voltage(self) -> float:
        """Bus voltage in volts."""
        # INA237/238 uses 3.125 mV/LSB
        return self._raw_vbus * 0.003125

    @property
    def shunt_voltage(self) -> float:
        """Shunt voltage in volts."""
        # Scale depends on ADC range
        scale = 1.25e-6 if self._adc_range else 5.0e-6  # µV/LSB
        return self._raw_vshunt * scale

    @property
    def current(self) -> float:
        """Current in amperes."""
        return self._raw_current * self._current_lsb

    @property
    def power(self) -> float:
        """Power in watts."""
        # INA237/238 power LSB = 20 × current_lsb
        return self._raw_power * 20.0 * self._current_lsb

    @property
    def conversion_ready(self) -> bool:
        """Check if conversion is complete."""
        return bool(self._conversion_ready)

    @property
    def alert_type(self) -> int:
        """Alert type configuration."""
        return self._alert_type

    @alert_type.setter
    def alert_type(self, value: int) -> None:
        # Alert type can be a combination of flags, so we check if all bits are valid
        valid_mask = (
            AlertType.CONVERSION_READY
            | AlertType.OVERTEMPERATURE
            | AlertType.OVERPOWER
            | AlertType.UNDERVOLTAGE
            | AlertType.OVERVOLTAGE
            | AlertType.UNDERSHUNT
            | AlertType.OVERSHUNT
        )
        if value & ~valid_mask:
            raise ValueError(
                f"Invalid alert type 0x{value:02X}. Must be a combination of AlertType.* constants"
            )
        self._alert_type = value

    @property
    def alert_flags(self) -> int:
        """Current alert flags."""
        return self._alert_flags
