# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
:py:class:`~adafruit_hx711.analog_in.AnalogIn`
======================================================
AnalogIn for ADC readings.

* Author(s): Liz Clark

"""

from adafruit_hx711.hx711 import HX711

try:
    from typing import Union
except ImportError:
    pass


class AnalogIn:
    """AnalogIn Mock Implementation for ADC Reads.

    :param HX711 adc: The ADC object.
    :param int chan_gain: Gain and channel configuration.
    """

    def __init__(self, adc: HX711, chan_gain: int = HX711.CHAN_A_GAIN_128) -> None:
        if not isinstance(adc, HX711):
            raise ValueError("ADC object must be an instance of the HX711 class.")
        self._adc = adc
        self._chan_gain = chan_gain

    @property
    def value(self) -> int:
        """Returns the value of an ADC pin as an integer."""
        result = self._adc.read(self._chan_gain)
        return result
