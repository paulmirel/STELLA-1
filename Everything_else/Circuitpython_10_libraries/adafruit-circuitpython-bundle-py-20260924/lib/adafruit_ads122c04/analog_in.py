# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
:py:class:`~adafruit_ads122c04.analog_in.AnalogIn`
======================================================
AnalogIn for ADC readings.

* Author(s): Liz Clark

"""

from adafruit_ads122c04.ads122c04 import ADS122C04, MUX_AIN0, MUX_AIN1, MUX_AIN2, MUX_AIN3

_SINGLE_ENDED_MUXES = (MUX_AIN0, MUX_AIN1, MUX_AIN2, MUX_AIN3)


class AnalogIn:
    """AnalogIn-compatible wrapper for ADS122C04 single-ended readings.

    Provides a :attr:`value` property scaled to a 16-bit unsigned range
    ``[0, 65535]`` and a :attr:`voltage` property in volts, matching the
    CircuitPython ``analogio.AnalogIn`` API.

    :param ADS122C04 adc: The ADS122C04 driver instance.
    :param int pin: Single-ended channel (0-3).
    """

    def __init__(self, adc: ADS122C04, pin: int) -> None:
        if not isinstance(adc, ADS122C04):
            raise ValueError("adc must be an ADS122C04 instance")
        if pin < 0 or pin > 3:
            raise ValueError("pin must be 0-3")
        self._adc = adc
        self._pin = pin
        self._mux = _SINGLE_ENDED_MUXES[pin]

    @property
    def value(self) -> int:
        """ADC reading as an unsigned 16-bit integer in the range ``[0, 65535]``.

        The 24-bit signed result is clamped to the positive range and then
        scaled to 16 bits to match the ``analogio.AnalogIn`` API.
        """
        self._adc.mux = self._mux
        self._adc.start_sync()
        # Wait for conversion
        while not self._adc.data_ready:
            pass
        raw = self._adc.read_data()
        # Clamp negative values to 0, then scale 24-bit positive range to 16-bit
        raw = max(raw, 0)
        # 24-bit positive max is 0x7FFFFF (8388607)
        # Scale to 16-bit range: raw * 65535 / 8388607
        return min((raw * 65535) // 8388607, 65535)

    @property
    def voltage(self) -> float:
        """ADC reading as a voltage in volts."""
        self._adc.mux = self._mux
        self._adc.start_sync()
        while not self._adc.data_ready:
            pass
        return self._adc.read_voltage()
