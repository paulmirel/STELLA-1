# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
:py:class:`~adafruit_ads122c04.ads122c04.ADS122C04`
================================================================================

CircuitPython driver for the Adafruit ADS122C04 24-Bit ADC - 4 Channel 2-kSPS - STEMMA QT / Qwiic


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit ADS122C04 24-Bit ADC - 4 Channel 2-kSPS - STEMMA QT / Qwiic <https://www.adafruit.com/product/6432>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

import struct
import time

from adafruit_bus_device.i2c_device import I2CDevice
from micropython import const

try:
    from typing import Optional

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.2"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_ADS122C04.git"

_DEFAULT_ADDR = const(0x40)

_REG_CONFIG0 = const(0x00)
_REG_CONFIG1 = const(0x01)
_REG_CONFIG2 = const(0x02)
_REG_CONFIG3 = const(0x03)

_CMD_RESET = const(0x06)
_CMD_POWERDOWN = const(0x02)
_CMD_STARTSYNC = const(0x08)
_CMD_RDATA = const(0x10)
_CMD_RREG = const(0x20)
_CMD_WREG = const(0x40)

VREF_INTERNAL = const(0x00)
"""Internal 2.048V reference."""
VREF_EXTERNAL = const(0x01)
"""External reference (REFP/REFN)."""
VREF_SUPPLY = const(0x02)
"""Analog supply (AVDD-AVSS)."""

MUX_AIN0_AIN1 = const(0x00)
"""Differential: AINP=AIN0, AINN=AIN1."""
MUX_AIN0_AIN2 = const(0x01)
"""Differential: AINP=AIN0, AINN=AIN2."""
MUX_AIN0_AIN3 = const(0x02)
"""Differential: AINP=AIN0, AINN=AIN3."""
MUX_AIN1_AIN0 = const(0x03)
"""Differential: AINP=AIN1, AINN=AIN0."""
MUX_AIN1_AIN2 = const(0x04)
"""Differential: AINP=AIN1, AINN=AIN2."""
MUX_AIN1_AIN3 = const(0x05)
"""Differential: AINP=AIN1, AINN=AIN3."""
MUX_AIN2_AIN3 = const(0x06)
"""Differential: AINP=AIN2, AINN=AIN3."""
MUX_AIN3_AIN2 = const(0x07)
"""Differential: AINP=AIN3, AINN=AIN2."""
MUX_AIN0 = const(0x08)
"""Single-ended: AIN0 vs AVSS."""
MUX_AIN1 = const(0x09)
"""Single-ended: AIN1 vs AVSS."""
MUX_AIN2 = const(0x0A)
"""Single-ended: AIN2 vs AVSS."""
MUX_AIN3 = const(0x0B)
"""Single-ended: AIN3 vs AVSS."""
MUX_REFPN_4 = const(0x0C)
"""(REFP-REFN)/4 monitor."""
MUX_SUPPLY_4 = const(0x0D)
"""(AVDD-AVSS)/4 monitor."""
MUX_SHORTED = const(0x0E)
"""Inputs shorted to (AVDD+AVSS)/2."""

GAIN_1 = const(0x00)
"""Gain = 1."""
GAIN_2 = const(0x01)
"""Gain = 2."""
GAIN_4 = const(0x02)
"""Gain = 4."""
GAIN_8 = const(0x03)
"""Gain = 8."""
GAIN_16 = const(0x04)
"""Gain = 16."""
GAIN_32 = const(0x05)
"""Gain = 32."""
GAIN_64 = const(0x06)
"""Gain = 64."""
GAIN_128 = const(0x07)
"""Gain = 128."""

RATE_20SPS = const(0x00)
"""20 SPS (normal) / 40 SPS (turbo)."""
RATE_45SPS = const(0x01)
"""45 SPS (normal) / 90 SPS (turbo)."""
RATE_90SPS = const(0x02)
"""90 SPS (normal) / 180 SPS (turbo)."""
RATE_175SPS = const(0x03)
"""175 SPS (normal) / 350 SPS (turbo)."""
RATE_330SPS = const(0x04)
"""330 SPS (normal) / 660 SPS (turbo)."""
RATE_600SPS = const(0x05)
"""600 SPS (normal) / 1200 SPS (turbo)."""
RATE_1000SPS = const(0x06)
"""1000 SPS (normal) / 2000 SPS (turbo)."""

CRC_DISABLED = const(0x00)
"""CRC disabled."""
CRC_INVERTED = const(0x01)
"""Inverted data output."""
CRC_CRC16 = const(0x02)
"""CRC16 enabled."""

IDAC_OFF = const(0x00)
"""IDAC off."""
IDAC_10UA = const(0x01)
"""10 µA."""
IDAC_50UA = const(0x02)
"""50 µA."""
IDAC_100UA = const(0x03)
"""100 µA."""
IDAC_250UA = const(0x04)
"""250 µA."""
IDAC_500UA = const(0x05)
"""500 µA."""
IDAC_1000UA = const(0x06)
"""1000 µA."""
IDAC_1500UA = const(0x07)
"""1500 µA."""

IDAC_ROUTE_DISABLED = const(0x00)
"""IDAC disabled."""
IDAC_ROUTE_AIN0 = const(0x01)
"""IDAC connected to AIN0."""
IDAC_ROUTE_AIN1 = const(0x02)
"""IDAC connected to AIN1."""
IDAC_ROUTE_AIN2 = const(0x03)
"""IDAC connected to AIN2."""
IDAC_ROUTE_AIN3 = const(0x04)
"""IDAC connected to AIN3."""
IDAC_ROUTE_REFP = const(0x05)
"""IDAC connected to REFP."""
IDAC_ROUTE_REFN = const(0x06)
"""IDAC connected to REFN."""

_GAIN_VALUES = (1, 2, 4, 8, 16, 32, 64, 128)


class ADS122C04:  # noqa: PLR0904
    """Driver for the ADS122C04 24-bit ADC.

    :param I2C i2c: The I2C bus the ADS122C04 is connected to.
    :param int address: The I2C device address. Default is ``0x40``.
    """

    def __init__(self, i2c: I2C, address: int = _DEFAULT_ADDR) -> None:
        self.i2c_device = I2CDevice(i2c, address)
        self._ref_voltage: float = 2.048
        self._crc_mode_cache: int = CRC_DISABLED
        self._last_data_valid: bool = True
        self._buf1 = bytearray(1)
        self._buf2 = bytearray(2)
        self._buf3 = bytearray(3)
        self._buf6 = bytearray(6)
        self.reset()

    def _read_register(self, register: int) -> int:
        self._buf1[0] = _CMD_RREG | ((register & 0x03) << 2)
        with self.i2c_device as i2c:
            i2c.write(self._buf1)
            if self._crc_mode_cache == CRC_CRC16:
                i2c.readinto(self._buf3)
                crc = self._calculate_crc16(self._buf3, 1)
                received = (self._buf3[1] << 8) | self._buf3[2]
                if crc != received:
                    raise OSError("CRC validation failed on register read")
                return self._buf3[0]
            if self._crc_mode_cache == CRC_INVERTED:
                i2c.readinto(self._buf2)
                if self._buf2[0] != (~self._buf2[1] & 0xFF):
                    raise OSError("Inverted data validation failed on register read")
                return self._buf2[0]
            i2c.readinto(self._buf1)
            return self._buf1[0]

    def _write_register(self, register: int, value: int) -> None:
        self._buf2[0] = _CMD_WREG | ((register & 0x03) << 2)
        self._buf2[1] = value & 0xFF
        with self.i2c_device as i2c:
            i2c.write(self._buf2)

    def _read_bits(self, register: int, num_bits: int, shift: int) -> int:
        mask = ((1 << num_bits) - 1) << shift
        return (self._read_register(register) & mask) >> shift

    def _write_bits(self, register: int, num_bits: int, shift: int, value: int) -> None:
        mask = ((1 << num_bits) - 1) << shift
        reg = self._read_register(register)
        reg = (reg & ~mask) | ((value << shift) & mask)
        self._write_register(register, reg)

    def _write_command(self, cmd: int) -> None:
        self._buf1[0] = cmd
        with self.i2c_device as i2c:
            i2c.write(self._buf1)

    def reset(self) -> None:
        """Reset the ADS122C04 to default settings."""
        self._write_command(_CMD_RESET)
        time.sleep(0.001)
        self._crc_mode_cache = CRC_DISABLED

    def power_down(self) -> None:
        """Enter power-down mode."""
        self._write_command(_CMD_POWERDOWN)

    def start_sync(self) -> None:
        """Start or sync a conversion."""
        self._write_command(_CMD_STARTSYNC)

    def read_data(self) -> int:
        """Read the raw 24-bit ADC conversion result.

        :return: Signed 24-bit conversion result.
        :rtype: int
        :raises IOError: If CRC or data integrity validation fails.
        """
        self._last_data_valid = False

        if self._crc_mode_cache == CRC_CRC16:
            buf = bytearray(5)
            buf_size = 5
        elif self._crc_mode_cache == CRC_INVERTED:
            buf = self._buf6
            buf_size = 6
        else:
            buf = self._buf3
            buf_size = 3

        self._buf1[0] = _CMD_RDATA
        with self.i2c_device as i2c:
            i2c.write(self._buf1)
            i2c.readinto(buf, end=buf_size)

        if self._crc_mode_cache == CRC_CRC16:
            received_crc = (buf[3] << 8) | buf[4]
            calculated_crc = self._calculate_crc16(buf, 3)
            if received_crc != calculated_crc:
                raise OSError("CRC16 validation failed on data read")

        if self._crc_mode_cache == CRC_INVERTED:
            if (
                buf[0] != (~buf[3] & 0xFF)
                or buf[1] != (~buf[4] & 0xFF)
                or buf[2] != (~buf[5] & 0xFF)
            ):
                raise OSError("Inverted data validation failed on data read")

        self._last_data_valid = True

        raw = (buf[0] << 16) | (buf[1] << 8) | buf[2]
        if raw & 0x800000:
            raw |= 0xFF000000
            raw = struct.unpack(">i", struct.pack(">I", raw))[0]
        return raw

    def read_voltage(self) -> float:
        """Read the ADC and return the value as a voltage.

        :return: Voltage in volts.
        :rtype: float
        """
        raw = self.read_data()
        return self.convert_to_voltage(raw)

    def convert_to_voltage(self, raw_data: int) -> float:
        """Convert a raw ADC reading to voltage.

        :param int raw_data: Signed 24-bit raw ADC value.
        :return: Voltage in volts.
        :rtype: float
        """
        eff_gain = self.effective_gain
        return raw_data * self._ref_voltage / (eff_gain * 8388608.0)

    def temperature(self) -> float:
        """Read the internal temperature sensor.

        The temperature sensor must be enabled before calling this method.

        :return: Temperature in degrees Celsius.
        :rtype: float
        """
        raw = self.read_data()
        return self.convert_to_temperature(raw)

    @staticmethod
    def convert_to_temperature(raw_data: int) -> float:
        """Convert a raw ADC reading to temperature (when in temperature sensor mode).

        :param int raw_data: Signed 24-bit raw ADC value.
        :return: Temperature in degrees Celsius.
        :rtype: float
        """
        temp_code = raw_data >> 10
        return temp_code * 0.03125

    @property
    def mux(self) -> int:
        """Input multiplexer configuration. Use one of the ``MUX_*`` constants."""
        return self._read_bits(_REG_CONFIG0, 4, 4)

    @mux.setter
    def mux(self, value: int) -> None:
        self._write_bits(_REG_CONFIG0, 4, 4, value)

    @property
    def gain(self) -> int:
        """Gain configuration. Use one of the ``GAIN_*`` constants."""
        return self._read_bits(_REG_CONFIG0, 3, 1)

    @gain.setter
    def gain(self, value: int) -> None:
        self._write_bits(_REG_CONFIG0, 3, 1, value)

    @property
    def pga(self) -> bool:
        """PGA enable. ``True`` to enable PGA, ``False`` to bypass.

        Note: the hardware register bit is PGA_BYPASS, so the sense is inverted.
        """
        return not self._read_bits(_REG_CONFIG0, 1, 0)

    @pga.setter
    def pga(self, value: bool) -> None:
        self._write_bits(_REG_CONFIG0, 1, 0, 0 if value else 1)

    @property
    def data_rate(self) -> int:
        """Data rate selection. Use one of the ``RATE_*`` constants."""
        return self._read_bits(_REG_CONFIG1, 3, 5)

    @data_rate.setter
    def data_rate(self, value: int) -> None:
        self._write_bits(_REG_CONFIG1, 3, 5, value)

    @property
    def turbo_mode(self) -> bool:
        """Turbo mode. ``True`` for turbo, ``False`` for normal."""
        return bool(self._read_bits(_REG_CONFIG1, 1, 4))

    @turbo_mode.setter
    def turbo_mode(self, value: bool) -> None:
        self._write_bits(_REG_CONFIG1, 1, 4, int(value))

    @property
    def continuous_mode(self) -> bool:
        """Conversion mode. ``True`` for continuous, ``False`` for single-shot."""
        return bool(self._read_bits(_REG_CONFIG1, 1, 3))

    @continuous_mode.setter
    def continuous_mode(self, value: bool) -> None:
        self._write_bits(_REG_CONFIG1, 1, 3, int(value))

    @property
    def vref_input(self) -> int:
        """Voltage reference selection. Use one of the ``VREF_*`` constants."""
        return self._read_bits(_REG_CONFIG1, 2, 1)

    @vref_input.setter
    def vref_input(self, value: int) -> None:
        self._write_bits(_REG_CONFIG1, 2, 1, value)

    @property
    def temperature_sensor(self) -> bool:
        """Temperature sensor mode. ``True`` to enable, ``False`` to disable."""
        return bool(self._read_bits(_REG_CONFIG1, 1, 0))

    @temperature_sensor.setter
    def temperature_sensor(self, value: bool) -> None:
        self._write_bits(_REG_CONFIG1, 1, 0, int(value))

    @property
    def data_ready(self) -> bool:
        """``True`` if new conversion data is ready. Read-only."""
        return bool(self._read_bits(_REG_CONFIG2, 1, 7))

    @property
    def data_counter_enabled(self) -> bool:
        """Data counter. ``True`` to enable, ``False`` to disable."""
        return bool(self._read_bits(_REG_CONFIG2, 1, 6))

    @data_counter_enabled.setter
    def data_counter_enabled(self, value: bool) -> None:
        self._write_bits(_REG_CONFIG2, 1, 6, int(value))

    @property
    def crc_mode(self) -> int:
        """CRC mode selection. Use one of the ``CRC_*`` constants.

        .. note::
            Setting this property also updates the internal cache used by
            :meth:`read_data` and the register read/write helpers.
        """
        return self._read_bits(_REG_CONFIG2, 2, 4)

    @crc_mode.setter
    def crc_mode(self, value: int) -> None:
        self._write_bits(_REG_CONFIG2, 2, 4, value)
        self._crc_mode_cache = value

    @property
    def burn_out_current(self) -> bool:
        """Burn-out current sources. ``True`` to enable 10 µA burn-out current."""
        return bool(self._read_bits(_REG_CONFIG2, 1, 3))

    @burn_out_current.setter
    def burn_out_current(self, value: bool) -> None:
        self._write_bits(_REG_CONFIG2, 1, 3, int(value))

    @property
    def idac_current(self) -> int:
        """IDAC current selection. Use one of the ``IDAC_*`` constants."""
        return self._read_bits(_REG_CONFIG2, 3, 0)

    @idac_current.setter
    def idac_current(self, value: int) -> None:
        self._write_bits(_REG_CONFIG2, 3, 0, value)

    @property
    def idac1_route(self) -> int:
        """IDAC1 routing selection. Use one of the ``IDAC_ROUTE_*`` constants."""
        return self._read_bits(_REG_CONFIG3, 3, 5)

    @idac1_route.setter
    def idac1_route(self, value: int) -> None:
        self._write_bits(_REG_CONFIG3, 3, 5, value)

    @property
    def idac2_route(self) -> int:
        """IDAC2 routing selection. Use one of the ``IDAC_ROUTE_*`` constants."""
        return self._read_bits(_REG_CONFIG3, 3, 2)

    @idac2_route.setter
    def idac2_route(self, value: int) -> None:
        self._write_bits(_REG_CONFIG3, 3, 2, value)

    @property
    def reference_voltage(self) -> float:
        """Reference voltage used for voltage conversion calculations, in volts.

        Defaults to 2.048 V (the internal reference). Set this to match your
        external reference if using ``VREF_EXTERNAL`` or ``VREF_SUPPLY``.
        """
        return self._ref_voltage

    @reference_voltage.setter
    def reference_voltage(self, value: float) -> None:
        self._ref_voltage = value

    @property
    def effective_gain(self) -> float:
        """The effective gain considering PGA bypass and single-ended restrictions.

        In single-ended mode the PGA is automatically bypassed and gain is
        limited to 1, 2, or 4. Read-only.
        """
        mux_val = self.mux
        gain_val = _GAIN_VALUES[self.gain]

        is_single_ended = MUX_AIN0 <= mux_val <= MUX_AIN3
        if is_single_ended:
            return float(min(gain_val, 4))
        return float(gain_val) if self.pga else 1.0

    @property
    def last_data_valid(self) -> bool:
        """``True`` if the most recent :meth:`read_data` passed integrity validation."""
        return self._last_data_valid

    @staticmethod
    def _calculate_crc16(data: bytes, length: int) -> int:
        crc = 0xFFFF
        poly = 0x1021
        for i in range(length):
            crc ^= data[i] << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ poly) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc
