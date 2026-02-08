# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
`adafruit_yoto.network`
================================================================================

Helper library for the Yoto Players


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* Yoto Mini Player running CircuitPython

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

* Adafruit's PortalBase library: https://github.com/adafruit/Adafruit_CircuitPython_PortalBase

"""

import neopixel
from adafruit_portalbase.network import NetworkBase
from adafruit_portalbase.wifi_esp32s2 import WiFi

__version__ = "1.0.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_YotoPlayer.git"


class Network(NetworkBase):
    """Network Helper Class for the Yoto Mini

    :param status_neopixel: The pin for the status NeoPixel. Defaults to ``None``.
    :param bool extract_values: If true, single-length fetched values are automatically extracted
                                from lists and tuples. Defaults to ``True``.
    :param debug: Turn on debug print outs. Defaults to False.

    """

    def __init__(
        self,
        *,
        status_neopixel=None,
        extract_values=True,
        debug=False,
    ):
        if status_neopixel:
            if isinstance(status_neopixel, neopixel.NeoPixel):
                status_led = status_neopixel
            else:
                status_led = neopixel.NeoPixel(status_neopixel, 1, brightness=0.2)
        else:
            status_led = None

        super().__init__(
            WiFi(status_led=status_led),
            extract_values=extract_values,
            debug=debug,
        )

    @property
    def enabled(self):
        """Get or Set whether the WiFi is enabled"""
        return self._wifi.enabled

    @enabled.setter
    def enabled(self, value):
        self._wifi.enabled = bool(value)
