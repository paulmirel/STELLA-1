# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_yoto.yoto`
================================================================================

Helper Library for the Yoto Players


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

import gc

from adafruit_portalbase import PortalBase

from adafruit_yoto.graphics import Graphics
from adafruit_yoto.network import Network
from adafruit_yoto.peripherals import Peripherals

__version__ = "1.0.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_YotoPlayer.git"


class Yoto(PortalBase):
    """Class representing the Yoto Mini music player

    :param url: The URL of your data source. Defaults to ``None``.
    :param headers: The headers for authentication, typically used by Azure API's.
    :param json_path: The list of json traversal to get data out of. Can be list of lists for
                      multiple data points. Defaults to ``None`` to not use json.
    :param regexp_path: The list of regexp strings to get data out (use a single regexp group).
                        Can be list of regexps for multiple data points. Defaults to ``None``
                        to not use regexp.
    :param default_bg: The path to your default background image file or a hex color.
                       Defaults to 0x000000.
    :param status_neopixel: The pin for the status NeoPixel. Defaults to ``None``.
    :param json_transform: A function or a list of functions to call with the parsed JSON.
                           Changes and additions are permitted for the ``dict`` object.
    :param int rotation: Default rotation (0, 90, 180, 270). Defaults to 0.
    :param bool auto_refresh: Automatically refresh the display after updates. Defaults to True.
    :param debug: Turn on debug print outs. Defaults to False.
    """

    def __init__(  # noqa: PLR0913
        self,
        *,
        url=None,
        headers=None,
        json_path=None,
        regexp_path=None,
        default_bg=0x000000,
        status_neopixel=None,
        json_transform=None,
        rotation=0,
        auto_refresh=True,
        debug=False,
    ):
        self.peripherals = Peripherals()

        network = Network(
            status_neopixel=status_neopixel,
            extract_values=False,
            debug=debug,
        )

        graphics = Graphics(
            default_bg=default_bg,
            rotation=rotation,
            debug=debug,
        )

        super().__init__(
            network,
            graphics,
            url=url,
            headers=headers,
            json_path=json_path,
            regexp_path=regexp_path,
            json_transform=json_transform,
            debug=debug,
        )

        gc.collect()
