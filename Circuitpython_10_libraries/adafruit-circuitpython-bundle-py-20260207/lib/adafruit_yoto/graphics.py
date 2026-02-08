# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_yoto.graphics`
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

import board
from adafruit_portalbase.graphics import GraphicsBase

__version__ = "1.0.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_YotoPlayer.git"


class Graphics(GraphicsBase):
    """Graphics Helper Class for the Yoto Mini Library

    :param default_bg: The path to your default background image file or a hex color.
                       Defaults to 0x000000.
    :param int rotation: Default rotation (0, 90, 180, 270). Defaults to 0.
    :param bool auto_refresh: Automatically refresh the display after updates. Defaults to True.
    :param debug: Turn on debug print outs. Defaults to False.
    """

    def __init__(self, *, default_bg=0x000000, rotation=0, auto_refresh=True, debug=False):
        self._debug = debug
        self.display = board.DISPLAY
        self.display.rotation = rotation
        self.auto_refresh = auto_refresh
        self.display.auto_refresh = auto_refresh

        super().__init__(board.DISPLAY, default_bg=default_bg, debug=debug)
        gc.collect()

    def refresh(self):
        """Manually refresh the display"""
        self.display.refresh()
