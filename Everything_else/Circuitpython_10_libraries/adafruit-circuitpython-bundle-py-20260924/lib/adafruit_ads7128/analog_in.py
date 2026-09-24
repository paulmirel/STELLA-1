# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
:py:class:`~adafruit_ads7128.analog_in.AnalogIn`
======================================================
AnalogIn for ADC readings.

* Author(s): Liz Clark

"""

from micropython import const

from adafruit_ads7128.ads7128 import ADS7128

__version__ = "1.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_ADS7128.git"

_EVENT_RGN = const(0x1E)
_HYSTERESIS_CH0 = const(0x20)  # per-channel block base, +4 per channel
_MAX_LSB_CH0 = const(0x60)  # +2 per channel
_MIN_LSB_CH0 = const(0x80)
_RECENT_LSB_CH0 = const(0xA0)  # +2 per channel


class AnalogIn:
    """AnalogIn-compatible wrapper for ADS7128 single-ended readings.

    Provides a :attr:`value` property scaled to a 16-bit unsigned range
    ``[0, 65535]`` and a :attr:`voltage` property in volts, matching the
    CircuitPython ``analogio.AnalogIn`` API.

    :param ADS7128 adc: The ADS7128 driver instance.
    :param int pin: Channel number (0-7).
    """

    def __init__(self, adc: ADS7128, pin: int) -> None:
        if not isinstance(adc, ADS7128):
            raise ValueError("adc must be an ADS7128 instance")
        if pin < 0 or pin > 7:
            raise ValueError("pin must be 0-7")
        self._adc = adc
        self._pin = pin
        adc.pin_cfg = adc.pin_cfg & ~(1 << pin) & 0xFF

    @property
    def value(self) -> int:
        """ADC reading as an unsigned 16-bit integer in the range ``[0, 65535]``.

        The 12-bit conversion result is scaled to 16 bits to match the
        ``analogio.AnalogIn`` API.
        """
        raw = self._adc._read(self._pin)
        return min((raw * 65535) // 4095, 65535)

    def voltage(self, reference_voltage: float = 5.0) -> float:
        """Read the channel and convert the result to volts.

        :param float reference_voltage: ADC reference voltage in volts.
            Defaults to :const:`5.0` to match the device's default reference.
        :return: The measured voltage in volts.
        :rtype: float
        """
        return (self._adc._read(self._pin) / 4096.0) * reference_voltage

    @property
    def max(self) -> int:
        """Maximum value recorded on this channel, in 12-bit counts. (read-only)

        Requires :attr:`ADS7128.statistics_enabled` to be ``True``.
        """
        return self._adc._read_12bit(_MAX_LSB_CH0 + self._pin * 2)

    @property
    def min(self) -> int:
        """Minimum value recorded on this channel, in 12-bit counts. (read-only)

        Requires :attr:`ADS7128.statistics_enabled` to be ``True``.
        """
        return self._adc._read_12bit(_MIN_LSB_CH0 + self._pin * 2)

    @property
    def recent(self) -> int:
        """Most recent conversion recorded on this channel, in 12-bit counts. (read-only)

        Requires :attr:`ADS7128.statistics_enabled` to be ``True``.
        """
        return self._adc._read_12bit(_RECENT_LSB_CH0 + self._pin * 2)

    @property
    def high_threshold(self) -> int:
        """Window-comparator high threshold for this channel, in 12-bit counts (0-4095)."""
        base = _HYSTERESIS_CH0 + self._pin * 4
        msb = self._adc._read_register(base + 1)
        hyst = self._adc._read_register(base)
        return (msb << 4) | ((hyst >> 4) & 0x0F)

    @high_threshold.setter
    def high_threshold(self, value: int) -> None:
        if not 0 <= value <= 0x0FFF:
            raise ValueError("high_threshold must be 0-4095")
        base = _HYSTERESIS_CH0 + self._pin * 4
        self._adc._write_register(base + 1, (value >> 4) & 0xFF)
        hyst = self._adc._read_register(base)
        hyst = (hyst & 0x0F) | ((value & 0x0F) << 4)
        self._adc._write_register(base, hyst)

    @property
    def low_threshold(self) -> int:
        """Window-comparator low threshold for this channel, in 12-bit counts (0-4095)."""
        base = _HYSTERESIS_CH0 + self._pin * 4
        msb = self._adc._read_register(base + 3)
        evt = self._adc._read_register(base + 2)
        return (msb << 4) | ((evt >> 4) & 0x0F)

    @low_threshold.setter
    def low_threshold(self, value: int) -> None:
        if not 0 <= value <= 0x0FFF:
            raise ValueError("low_threshold must be 0-4095")
        base = _HYSTERESIS_CH0 + self._pin * 4
        self._adc._write_register(base + 3, (value >> 4) & 0xFF)
        evt = self._adc._read_register(base + 2)
        evt = (evt & 0x0F) | ((value & 0x0F) << 4)
        self._adc._write_register(base + 2, evt)

    @property
    def hysteresis(self) -> int:
        """Window-comparator hysteresis for this channel, 0-15."""
        return self._adc._read_register(_HYSTERESIS_CH0 + self._pin * 4) & 0x0F

    @hysteresis.setter
    def hysteresis(self, value: int) -> None:
        if not 0 <= value <= 15:
            raise ValueError("hysteresis must be 0-15")
        base = _HYSTERESIS_CH0 + self._pin * 4
        reg = self._adc._read_register(base)
        reg = (reg & 0xF0) | (value & 0x0F)
        self._adc._write_register(base, reg)

    @property
    def event_region(self) -> bool:
        """Comparator event region: ``True`` for in-band, ``False`` for out-of-window."""
        return bool(self._adc._read_register(_EVENT_RGN) & (1 << self._pin))

    @event_region.setter
    def event_region(self, in_band: bool) -> None:
        if in_band:
            self._adc._set_bits(_EVENT_RGN, 1 << self._pin)
        else:
            self._adc._clear_bits(_EVENT_RGN, 1 << self._pin)

    @property
    def event_count(self) -> int:
        """Consecutive samples before an alert triggers, 0-15 (alert after count + 1)."""
        base = _HYSTERESIS_CH0 + self._pin * 4
        return self._adc._read_register(base + 2) & 0x0F

    @event_count.setter
    def event_count(self, count: int) -> None:
        if not 0 <= count <= 15:
            raise ValueError("event_count must be 0-15")
        base = _HYSTERESIS_CH0 + self._pin * 4
        evt = self._adc._read_register(base + 2)
        evt = (evt & 0xF0) | (count & 0x0F)
        self._adc._write_register(base + 2, evt)
