# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
:py:class:`~adafruit_ads7128.ads7128.ADS7128`
================================================================================

CircuitPython driver for the Adafruit ADS7128 8-Channel ADC and GPIO Expander

* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit ADS7128 8-Channel ADC and GPIO Expander <https://www.adafruit.com/product/6494>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

import time

from adafruit_bus_device import i2c_device
from micropython import const

try:
    from typing import Tuple

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_ADS7128.git"

# Oversampling ratios
OSR_NONE = 0
"""No oversampling (12-bit result)."""
OSR_2 = 1
"""2x oversampling (13-bit result)."""
OSR_4 = 2
"""4x oversampling (14-bit result)."""
OSR_8 = 3
"""8x oversampling (15-bit result)."""
OSR_16 = 4
"""16x oversampling (16-bit result)."""
OSR_32 = 5
"""32x oversampling (16-bit result)."""
OSR_64 = 6
"""64x oversampling (16-bit result)."""
OSR_128 = 7
"""128x oversampling (16-bit result)."""

_DEFAULT_ADDR = const(0x10)

# Opcodes
_OP_READ = const(0x10)
_OP_WRITE = const(0x08)
_OP_SET_BIT = const(0x18)
_OP_CLEAR_BIT = const(0x20)

# Registers
_STATUS = const(0x00)
_GENERAL_CFG = const(0x01)
_DATA_CFG = const(0x02)
_OSR_CFG = const(0x03)
_OPMODE_CFG = const(0x04)
_PIN_CFG = const(0x05)
_GPIO_CFG = const(0x07)
_GPO_DRIVE_CFG = const(0x09)
_GPO_VALUE = const(0x0B)
_GPI_VALUE = const(0x0D)
_ZCD_BLANKING_CFG = const(0x0F)
_SEQUENCE_CFG = const(0x10)
_CHANNEL_SEL = const(0x11)
_AUTO_SEQ_CH_SEL = const(0x12)
_ALERT_CH_SEL = const(0x14)
_ALERT_PIN_CFG = const(0x17)
_EVENT_FLAG = const(0x18)
_EVENT_HIGH_FLAG = const(0x1A)
_EVENT_LOW_FLAG = const(0x1C)
_RECENT_LSB_CH0 = const(0xA0)  # +2 per channel
_RMS_CFG = const(0xC0)
_RMS_LSB = const(0xC1)
_RMS_MSB = const(0xC2)
_GPO_ZCD_UPDATE_EN = const(0xE7)

# SYSTEM_STATUS bits
_BOR = const(0x01)
_CRC_ERR_IN = const(0x02)
_RMS_DONE = const(0x10)

# GENERAL_CFG bits
_RST = const(0x01)
_CAL = const(0x02)
_CNVST = const(0x08)
_DWC_EN = const(0x10)
_STATS_EN = const(0x20)
_CRC_EN = const(0x40)
_RMS_EN = const(0x80)

# SEQUENCE_CFG bits
_SEQ_MODE = const(0x01)
_SEQ_START = const(0x10)

# OPMODE_CFG bits
_OSC_SEL = const(0x10)
_CONV_MODE = const(0x20)

# DATA_CFG bits
_APPEND_CHID = const(0x10)

# ALERT_PIN_CFG bits
_ALERT_DRIVE = const(0x04)

# ZCD_BLANKING_CFG bits
_ZCD_MULT = const(0x80)

# RMS_CFG bits
_RMS_DC_SUB = const(0x04)


def _crc8(value: int) -> int:
    # CRC-8-CCITT, polynomial 0x07, over a single byte
    crc = value
    for _ in range(8):
        if crc & 0x80:
            crc = ((crc << 1) ^ 0x07) & 0xFF
        else:
            crc = (crc << 1) & 0xFF
    return crc


class ADS7128:  # noqa: PLR0904
    """Driver for the ADS7128 8-channel 12-bit ADC with GPIOs.

    :param ~busio.I2C i2c: The I2C bus the ADS7128 is connected to.
    :param int address: The I2C address of the device. Defaults to :const:`0x10`.
    """

    def __init__(self, i2c: "I2C", address: int = _DEFAULT_ADDR) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c, address)
        self._crc_enabled = False
        self._crc_error = False
        self._in_buf = bytearray(1)
        self._out_buf = bytearray(2)
        self._wbuf = bytearray(3)
        self._reset()

    def _read_register(self, reg: int) -> int:
        if self._crc_enabled:
            out = bytes((_OP_READ, _crc8(_OP_READ), reg, _crc8(reg)))
            in_buf = bytearray(2)
            with self.i2c_device as i2c:
                i2c.write_then_readinto(out, in_buf)
            if in_buf[1] != _crc8(in_buf[0]):
                self._crc_error = True
            return in_buf[0]
        self._out_buf[0] = _OP_READ
        self._out_buf[1] = reg
        with self.i2c_device as i2c:
            i2c.write_then_readinto(self._out_buf, self._in_buf)
        return self._in_buf[0]

    def _write_register(self, reg: int, data: int) -> None:
        if self._crc_enabled:
            out = bytes((_OP_WRITE, _crc8(_OP_WRITE), reg, _crc8(reg), data, _crc8(data)))
            with self.i2c_device as i2c:
                i2c.write(out)
            return
        self._wbuf[0] = _OP_WRITE
        self._wbuf[1] = reg
        self._wbuf[2] = data
        with self.i2c_device as i2c:
            i2c.write(self._wbuf)

    def _set_bits(self, reg: int, mask: int) -> None:
        if self._crc_enabled:
            out = bytes((_OP_SET_BIT, _crc8(_OP_SET_BIT), reg, _crc8(reg), mask, _crc8(mask)))
            with self.i2c_device as i2c:
                i2c.write(out)
            return
        self._wbuf[0] = _OP_SET_BIT
        self._wbuf[1] = reg
        self._wbuf[2] = mask
        with self.i2c_device as i2c:
            i2c.write(self._wbuf)

    def _clear_bits(self, reg: int, mask: int) -> None:
        if self._crc_enabled:
            out = bytes(
                (
                    _OP_CLEAR_BIT,
                    _crc8(_OP_CLEAR_BIT),
                    reg,
                    _crc8(reg),
                    mask,
                    _crc8(mask),
                )
            )
            with self.i2c_device as i2c:
                i2c.write(out)
            return
        self._wbuf[0] = _OP_CLEAR_BIT
        self._wbuf[1] = reg
        self._wbuf[2] = mask
        with self.i2c_device as i2c:
            i2c.write(self._wbuf)

    def _read_12bit(self, lsb_reg: int) -> int:
        # 12-bit value is MSB-aligned across the register pair:
        # MSB register = [D11:D4], LSB register = [D3:D0, 0, 0, 0, 0]
        lsb = self._read_register(lsb_reg)
        msb = self._read_register(lsb_reg + 1)
        return (msb << 4) | (lsb >> 4)

    def _reset(self) -> None:
        self._write_register(_GENERAL_CFG, _RST)
        time.sleep(0.005)
        self._write_register(_GENERAL_CFG, _CAL)
        for _ in range(1000):
            if not self._read_register(_GENERAL_CFG) & _CAL:
                break
            time.sleep(0.001)
        else:
            raise RuntimeError("ADS7128 calibration timed out")
        self._write_register(_STATUS, _BOR)

    @staticmethod
    def _check_channel(channel: int) -> None:
        if not 0 <= channel <= 7:
            raise ValueError("channel must be 0-7")

    def _read(self, channel: int) -> int:
        """Read a single 12-bit conversion (0-4095) from a channel in manual mode.

        :param int channel: Channel number, 0-7.
        :return: The 12-bit conversion result.
        :rtype: int
        """
        self._check_channel(channel)
        self._set_bits(_GENERAL_CFG, _STATS_EN)
        chan_sel = self._read_register(_CHANNEL_SEL)
        chan_sel = (chan_sel & 0xF0) | (channel & 0x0F)
        self._write_register(_CHANNEL_SEL, chan_sel)
        self._set_bits(_GENERAL_CFG, _CNVST)
        time.sleep(0.00001)
        return self._read_12bit(_RECENT_LSB_CH0 + channel * 2)

    @property
    def sequence_channels(self) -> int:
        """Bitmask of channels included in the auto-sequence (bit 0 = CH0)."""
        return self._read_register(_AUTO_SEQ_CH_SEL)

    @sequence_channels.setter
    def sequence_channels(self, channel_mask: int) -> None:
        self._write_register(_AUTO_SEQ_CH_SEL, channel_mask & 0xFF)

    def start_sequence(self) -> None:
        """Start autonomous auto-sequence conversions on the selected channels."""
        self._set_bits(_GENERAL_CFG, _STATS_EN)
        self._set_bits(_DATA_CFG, _APPEND_CHID)
        self._set_bits(_OPMODE_CFG, _CONV_MODE)
        self._write_register(_SEQUENCE_CFG, _SEQ_MODE | _SEQ_START)

    def stop_sequence(self) -> None:
        """Stop the auto-sequence."""
        self._clear_bits(_SEQUENCE_CFG, _SEQ_START)

    def read_sequence_result(self) -> "Tuple[int, int]":
        """Read the next conversion result from the running sequence.

        :return: A ``(value, channel)`` tuple where ``value`` is the 12-bit
            conversion result and ``channel`` is the channel it came from.
        :rtype: tuple
        """
        out = bytes((_OP_READ, 0x00))
        in_buf = bytearray(2)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(out, in_buf)
        value = (in_buf[0] << 4) | ((in_buf[1] >> 4) & 0x0F)
        channel = in_buf[1] & 0x0F
        return value, channel

    @property
    def oversampling(self) -> int:
        """Oversampling ratio (0-7). See the ``OSR_*`` module constants."""
        return self._read_register(_OSR_CFG) & 0x07

    @oversampling.setter
    def oversampling(self, osr: int) -> None:
        if not 0 <= osr <= 7:
            raise ValueError("oversampling must be 0-7")
        self._write_register(_OSR_CFG, osr & 0x07)

    @property
    def pin_cfg(self) -> int:
        """Per-channel analog (bit clear) / digital (bit set) selection bitmask."""
        return self._read_register(_PIN_CFG)

    @pin_cfg.setter
    def pin_cfg(self, value: int) -> None:
        self._write_register(_PIN_CFG, value & 0xFF)

    @property
    def gpio_cfg(self) -> int:
        """Per-channel digital direction bitmask (bit set = output, clear = input)."""
        return self._read_register(_GPIO_CFG)

    @gpio_cfg.setter
    def gpio_cfg(self, value: int) -> None:
        self._write_register(_GPIO_CFG, value & 0xFF)

    @property
    def gpo_drive_cfg(self) -> int:
        """Per-channel output drive bitmask (bit set = push-pull, clear = open-drain)."""
        return self._read_register(_GPO_DRIVE_CFG)

    @gpo_drive_cfg.setter
    def gpo_drive_cfg(self, value: int) -> None:
        self._write_register(_GPO_DRIVE_CFG, value & 0xFF)

    @property
    def gpo_value(self) -> int:
        """Digital output level bitmask, one bit per channel."""
        return self._read_register(_GPO_VALUE)

    @gpo_value.setter
    def gpo_value(self, value: int) -> None:
        self._write_register(_GPO_VALUE, value & 0xFF)

    @property
    def gpi_value(self) -> int:
        """Digital input level bitmask, one bit per channel. (read-only)"""
        return self._read_register(_GPI_VALUE)

    @property
    def gpo_zcd_update_en(self) -> int:
        """Per-channel zero-crossing-to-GPO update enable bitmask."""
        return self._read_register(_GPO_ZCD_UPDATE_EN)

    @gpo_zcd_update_en.setter
    def gpo_zcd_update_en(self, value: int) -> None:
        self._write_register(_GPO_ZCD_UPDATE_EN, value & 0xFF)

    @property
    def crc_enabled(self) -> bool:
        """Whether CRC validation of I2C transactions is enabled."""
        return self._crc_enabled

    @crc_enabled.setter
    def crc_enabled(self, enable: bool) -> None:
        if enable:
            self._set_bits(_GENERAL_CFG, _CRC_EN)
            self._crc_enabled = True
        else:
            self._clear_bits(_GENERAL_CFG, _CRC_EN)
            self._crc_enabled = False

    @property
    def crc_error(self) -> bool:
        """``True`` if a CRC error has been detected on the I2C interface. (read-only)"""
        if self._read_register(_STATUS) & _CRC_ERR_IN:
            return True
        return self._crc_error

    def clear_crc_error(self) -> None:
        """Clear the CRC error flag."""
        self._crc_error = False
        self._write_register(_STATUS, _CRC_ERR_IN)

    @property
    def statistics_enabled(self) -> bool:
        """Whether min/max/recent statistics tracking is enabled."""
        return bool(self._read_register(_GENERAL_CFG) & _STATS_EN)

    @statistics_enabled.setter
    def statistics_enabled(self, enable: bool) -> None:
        if enable:
            self._set_bits(_GENERAL_CFG, _STATS_EN)
        else:
            self._clear_bits(_GENERAL_CFG, _STATS_EN)

    def reset_statistics(self) -> None:
        """Clear all recorded statistics and restart recording."""
        self._clear_bits(_GENERAL_CFG, _STATS_EN)
        self._set_bits(_GENERAL_CFG, _STATS_EN)

    @property
    def dwc_enabled(self) -> bool:
        """Whether the digital window comparator is enabled."""
        return bool(self._read_register(_GENERAL_CFG) & _DWC_EN)

    @dwc_enabled.setter
    def dwc_enabled(self, enable: bool) -> None:
        if enable:
            self._set_bits(_GENERAL_CFG, _DWC_EN)
        else:
            self._clear_bits(_GENERAL_CFG, _DWC_EN)

    @property
    def event_flags(self) -> int:
        """Combined high/low threshold event flags, one bit per channel. (read-only)"""
        return self._read_register(_EVENT_FLAG)

    @property
    def event_high_flags(self) -> int:
        """High threshold event flags, one bit per channel. (read-only)"""
        return self._read_register(_EVENT_HIGH_FLAG)

    @property
    def event_low_flags(self) -> int:
        """Low threshold event flags, one bit per channel. (read-only)"""
        return self._read_register(_EVENT_LOW_FLAG)

    def clear_event_flags(self) -> None:
        """Clear all high and low threshold event flags."""
        self._write_register(_EVENT_HIGH_FLAG, 0xFF)
        self._write_register(_EVENT_LOW_FLAG, 0xFF)

    @property
    def alert_push_pull(self) -> bool:
        """ALERT pin drive: ``True`` for push-pull, ``False`` for open-drain."""
        return bool(self._read_register(_ALERT_PIN_CFG) & _ALERT_DRIVE)

    @alert_push_pull.setter
    def alert_push_pull(self, value: bool) -> None:
        cfg = self._read_register(_ALERT_PIN_CFG)
        if value:
            cfg |= _ALERT_DRIVE
        else:
            cfg &= ~_ALERT_DRIVE & 0xFF
        self._write_register(_ALERT_PIN_CFG, cfg)

    @property
    def alert_logic(self) -> int:
        """ALERT pin logic: 0=active low, 1=active high, 2=pulsed low, 3=pulsed high."""
        return self._read_register(_ALERT_PIN_CFG) & 0x03

    @alert_logic.setter
    def alert_logic(self, value: int) -> None:
        if not 0 <= value <= 3:
            raise ValueError("alert_logic must be 0-3")
        cfg = self._read_register(_ALERT_PIN_CFG)
        cfg = (cfg & ~0x03 & 0xFF) | value
        self._write_register(_ALERT_PIN_CFG, cfg)

    @property
    def alert_channels(self) -> int:
        """Bitmask of channels that can trigger the ALERT pin (bit 0 = CH0)."""
        return self._read_register(_ALERT_CH_SEL)

    @alert_channels.setter
    def alert_channels(self, channel_mask: int) -> None:
        self._write_register(_ALERT_CH_SEL, channel_mask & 0xFF)

    @property
    def low_power_oscillator(self) -> bool:
        """Use the low-power oscillator (``True``) or high-speed oscillator (``False``)."""
        return bool(self._read_register(_OPMODE_CFG) & _OSC_SEL)

    @low_power_oscillator.setter
    def low_power_oscillator(self, value: bool) -> None:
        cfg = self._read_register(_OPMODE_CFG)
        if value:
            cfg |= _OSC_SEL
        else:
            cfg &= ~_OSC_SEL & 0xFF
        self._write_register(_OPMODE_CFG, cfg)

    @property
    def clock_divider(self) -> int:
        """Autonomous-mode sampling clock divider, 0-15."""
        return self._read_register(_OPMODE_CFG) & 0x0F

    @clock_divider.setter
    def clock_divider(self, divider: int) -> None:
        if not 0 <= divider <= 15:
            raise ValueError("clock_divider must be 0-15")
        cfg = self._read_register(_OPMODE_CFG)
        cfg = (cfg & 0xF0) | (divider & 0x0F)
        self._write_register(_OPMODE_CFG, cfg)

    @property
    def zcd_channel(self) -> int:
        """Analog channel monitored by the zero-crossing detector, 0-7."""
        return (self._read_register(_CHANNEL_SEL) >> 4) & 0x0F

    @zcd_channel.setter
    def zcd_channel(self, channel: int) -> None:
        self._check_channel(channel)
        reg = self._read_register(_CHANNEL_SEL)
        reg = (reg & 0x0F) | (channel << 4)
        self._write_register(_CHANNEL_SEL, reg)

    @property
    def zcd_blanking(self) -> int:
        """Zero-crossing blanking count, 0-127 (conversions skipped after an event)."""
        return self._read_register(_ZCD_BLANKING_CFG) & 0x7F

    @zcd_blanking.setter
    def zcd_blanking(self, count: int) -> None:
        if not 0 <= count <= 127:
            raise ValueError("zcd_blanking must be 0-127")
        reg = self._read_register(_ZCD_BLANKING_CFG)
        reg = (reg & _ZCD_MULT) | (count & 0x7F)
        self._write_register(_ZCD_BLANKING_CFG, reg)

    @property
    def zcd_blanking_multiply(self) -> bool:
        """When ``True``, the zero-crossing blanking count is multiplied by 8."""
        return bool(self._read_register(_ZCD_BLANKING_CFG) & _ZCD_MULT)

    @zcd_blanking_multiply.setter
    def zcd_blanking_multiply(self, value: bool) -> None:
        reg = self._read_register(_ZCD_BLANKING_CFG)
        if value:
            reg |= _ZCD_MULT
        else:
            reg &= ~_ZCD_MULT & 0xFF
        self._write_register(_ZCD_BLANKING_CFG, reg)

    @property
    def rms_enabled(self) -> bool:
        """Whether the RMS computation module is enabled.

        Setting this to ``True`` clears any previous result and starts a new
        computation using samples from autonomous conversion mode.
        """
        return bool(self._read_register(_GENERAL_CFG) & _RMS_EN)

    @rms_enabled.setter
    def rms_enabled(self, enable: bool) -> None:
        if enable:
            self._set_bits(_GENERAL_CFG, _RMS_EN)
        else:
            self._clear_bits(_GENERAL_CFG, _RMS_EN)

    @property
    def rms_channel(self) -> int:
        """Analog channel the RMS module monitors, 0-7."""
        return (self._read_register(_RMS_CFG) >> 4) & 0x0F

    @rms_channel.setter
    def rms_channel(self, channel: int) -> None:
        self._check_channel(channel)
        reg = self._read_register(_RMS_CFG)
        reg = (reg & 0x0F) | (channel << 4)
        self._write_register(_RMS_CFG, reg)

    @property
    def rms_samples(self) -> int:
        """RMS sample-count setting: 0=1024, 1=4096, 2=16384, 3=65536 samples."""
        return self._read_register(_RMS_CFG) & 0x03

    @rms_samples.setter
    def rms_samples(self, setting: int) -> None:
        if not 0 <= setting <= 3:
            raise ValueError("rms_samples must be 0-3")
        reg = self._read_register(_RMS_CFG)
        reg = (reg & 0xFC) | (setting & 0x03)
        self._write_register(_RMS_CFG, reg)

    @property
    def rms_dc_subtract(self) -> bool:
        """Whether the DC component is subtracted before the RMS calculation."""
        return bool(self._read_register(_RMS_CFG) & _RMS_DC_SUB)

    @rms_dc_subtract.setter
    def rms_dc_subtract(self, enable: bool) -> None:
        if enable:
            self._set_bits(_RMS_CFG, _RMS_DC_SUB)
        else:
            self._clear_bits(_RMS_CFG, _RMS_DC_SUB)

    @property
    def rms(self) -> int:
        """The 16-bit RMS result over the configured number of samples. (read-only)"""
        lsb = self._read_register(_RMS_LSB)
        msb = self._read_register(_RMS_MSB)
        return (msb << 8) | lsb

    @property
    def rms_done(self) -> bool:
        """``True`` if the RMS computation is complete. Reading clears the flag. (read-only)"""
        if self._read_register(_STATUS) & _RMS_DONE:
            self._set_bits(_STATUS, _RMS_DONE)
            return True
        return False
