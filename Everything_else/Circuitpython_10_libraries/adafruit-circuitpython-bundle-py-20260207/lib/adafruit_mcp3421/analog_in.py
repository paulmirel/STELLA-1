# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
:py:class:`~adafruit_mcp3421.analog_in.AnalogIn`
======================================================
AnalogIn for ADC readings.

* Author(s): Liz Clark

"""

from adafruit_mcp3421.mcp3421 import MCP3421


class AnalogIn:
    """AnalogIn Mock Implementation for ADC Reads.

    :param MCP3421 adc: The ADC object.
    """

    def __init__(self, adc: MCP3421) -> None:
        if not isinstance(adc, MCP3421):
            raise ValueError("ADC object is from the MCP3421 class.")
        self._adc = adc

    @property
    def value(self) -> int:
        """Returns the value of an ADC pin as an integer"""
        result = self._adc.read()
        return result
