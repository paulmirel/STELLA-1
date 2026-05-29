# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_checkbox`
================================================================================

A displayio based CheckBox widget. It includes a text label and a box
 that can be checked or unchecked.


* Author(s): Tim Cocks

Implementation Notes
--------------------

**Hardware:**

* Any displayio compatible display

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""

# imports
from adafruit_anchored_group import AnchoredGroup
from adafruit_display_text.bitmap_label import Label
from bitmaptools import draw_line, fill_region
from displayio import Bitmap, OnDiskBitmap, Palette, TileGrid

try:
    from typing import Optional, Union

    from displayio import ColorConverter
    from fontio import FontProtocol
except ImportError:
    pass

__version__ = "1.0.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_CheckBox.git"


class CheckBox(AnchoredGroup):
    """
    A displayio based CheckBox widget. It includes a text label and a box
    that can be checked or unchecked.

    :param FontProtocol font: The font to use for the CheckBox's label
    :param spritesheet: An OnDiskBitmap or Bitmap to use as the sprite
      sheet for the CheckBox. It should be twice as wide as it is tall,
      the right half should contain the checked state sprite. If None
      is provided, a basic checkbox bitmap will be used by default.
    :param pixel_shader: The pixel shader to use if a Bitmap was passed
      for spritesheet. Unused if spritesheet is not a Bitmap
    :param string text: The text to show next to the CheckBox
    :param int text_color: The color of the text next to the CheckBox
      as an RGB hex integer.
    :param int text_background_color: The background color of the text
      next to the CheckBox as an RGB hex integer.
    :param bool checked: Whether the CheckBox is checked when created.
    """

    def __init__(
        self,
        font,
        spritesheet: Optional[Union[OnDiskBitmap, Bitmap]] = None,
        pixel_shader: Optional[Union[Palette, ColorConverter]] = None,
        text="",
        text_color=0xFFFFFF,
        text_background_color=None,
        checked=False,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.label = Label(
            font, text=text, color=text_color, background_color=text_background_color
        )

        if spritesheet is not None and isinstance(spritesheet, OnDiskBitmap):
            self.spritesheet = spritesheet
            self.check_tilegrid = TileGrid(
                bitmap=self.spritesheet,
                pixel_shader=self.spritesheet.pixel_shader,
                tile_width=self.spritesheet.width // 2,
            )
        elif spritesheet is not None and isinstance(spritesheet, Bitmap):
            if pixel_shader is None:
                raise ValueError("Must pass a pixel_shader to use Bitmap as a spritesheet")
            self.check_tilegrid = TileGrid(
                bitmap=self.spritesheet,
                pixel_shader=pixel_shader,
                tile_width=self.spritesheet.width // 2,
            )
        elif spritesheet is None:
            self._init_basic_spritesheet()

        self.append(self.check_tilegrid)
        self.label.anchor_point = (0, 0.5)
        self.label.anchored_position = (
            self.check_tilegrid.x + self.check_tilegrid.tile_width + 2,
            (self.check_tilegrid.y + self.check_tilegrid.tile_height) // 2,
        )
        self.append(self.label)

        self._checked = False
        self.checked = checked

    def _init_basic_spritesheet(self):
        """
        Initialize a basic sprite sheet for a CheckBox, used if no sprite sheet was provided
        """
        self.spritesheet = Bitmap(32, 16, 3)
        pixel_shader = Palette(3)
        pixel_shader[0] = 0xFF00FF
        pixel_shader[1] = 0xFFFFFF
        pixel_shader[2] = 0x000000
        pixel_shader.make_transparent(0)

        x1, y1 = 1, 1
        x2, y2 = 14 + 1, 14 + 1
        fill_region(self.spritesheet, x1, y1, x2, y2, 1)
        fill_region(self.spritesheet, x1 + 16, y1, x2 + 16, y2, 1)

        outline_segments = [(1, 0, 14, 0), (1, 15, 14, 15), (0, 1, 0, 14), (15, 1, 15, 14)]
        for segment in outline_segments:
            x1, y1, x2, y2 = segment
            draw_line(self.spritesheet, x1, y1, x2, y2, 2)
            draw_line(self.spritesheet, x1 + 16, y1, x2 + 16, y2, 2)

        x_segments = [(19, 3, 28, 12), (19, 12, 28, 3)]
        for segment in x_segments:
            x1, y1, x2, y2 = segment
            draw_line(self.spritesheet, x1, y1, x2, y2, 2)

        self.check_tilegrid = TileGrid(
            bitmap=self.spritesheet,
            pixel_shader=pixel_shader,
            tile_width=self.spritesheet.width // 2,
        )

    @property
    def checked(self):
        """
        Whether the CheckBox is currently checked.
        :return: True if checked, False otherwise.
        """
        return self._checked

    @checked.setter
    def checked(self, value):
        self._checked = bool(value)
        if self._checked:
            self.check_tilegrid[0] = 1
        else:
            self.check_tilegrid[0] = 0
