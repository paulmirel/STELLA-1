# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_display_emoji_text`
================================================================================

Displayio class for displaying text that contains emoji


* Author(s): Tim Cocks

Implementation Notes
--------------------

**Hardware:**

Any display that supports displayio.

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""

# imports
import os

import adafruit_imageload
import bitmaptools
import displayio
import terminalio
from adafruit_displayio_layout.widgets.widget import Widget

__version__ = "1.0.2"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Display_Emoji_Text.git"


class EmojiLabel(Widget):
    WIDTH = 10
    MULTI_CODE_RANGES = [
        [35, 35],
        [42, 42],
        [48, 57],
        [9977, 9977],
        [10084, 10084],
        [127462, 127487],
        [127939, 127940],
        [127946, 127948],
        [127987, 127988],
        [128008, 128008],
        [128021, 128021],
        [128038, 128038],
        [128059, 128059],
        [128065, 128065],
        [128104, 128105],
        [128113, 128113],
        [128115, 128115],
        [128129, 128130],
        [128134, 128135],
        [128558, 128558],
        [128565, 128566],
        [128581, 128583],
        [128587, 128587],
        [128675, 128675],
        [128692, 128694],
        [129336, 129337],
        [129341, 129342],
        [129485, 129486],
        [129489, 129489],
        [129492, 129492],
        [129495, 129495],
        [129497, 129497],
    ]
    FIVE_WIDES = [127947, 9977, 128105, 127948, 128104, 128065, 127987]

    def __init__(
        self,
        text,
        scale=1,
        ascii_font=terminalio.FONT,
        # ruff: noqa: PLR0912, PLR0915, PLR1702
        # Too many branches, Too many statements, Too many nested blocks
    ):
        try:
            os.stat("emoji")
        except OSError:
            raise RuntimeError(
                "You need to download a set of emoji PNG files and place them CIRCUITPY/emoji/."
                " The recommended set is available for download here: https://emoji.serenityos.org/"
            )
        super().__init__(scale=scale)
        self.font = ascii_font
        self.ascii_palette = displayio.Palette(2)
        self.ascii_palette[0] = 0x000000
        self.ascii_palette[1] = 0xFFFFFF

        self._width = 0
        self._height = 12
        self._bounding_box = [0, 0, 0, 0]
        self._row_width = 0

        self._last_x = 0
        self._last_y = 0

        skip_count = 0
        for i, char in enumerate(text):
            if skip_count > 0:
                skip_count -= 1
                continue
            # print(char)
            if char == "\n":
                # print("newline")
                self._last_y += 12
                self._last_x = 0
                self._height += 12
                self._row_width = 0
                self._bounding_box[3] = self._height
                continue

            found_glyph = self.font.get_glyph(ord(char))
            if found_glyph is not None:
                bmp = displayio.Bitmap(found_glyph.width, found_glyph.height, 2)
                glyph_offset_x = found_glyph.tile_index * found_glyph.width
                bitmaptools.blit(
                    bmp,
                    found_glyph.bitmap,
                    0,
                    0,
                    x1=glyph_offset_x,
                    y1=0,
                    x2=glyph_offset_x + found_glyph.width,
                    y2=found_glyph.height,
                    skip_source_index=0,
                )
                tg = displayio.TileGrid(bitmap=bmp, pixel_shader=self.ascii_palette)
                tg.x = self._last_x
                tg.y = self._last_y
                self._row_width += bmp.width
                if self._width < self._row_width:
                    self._width = self._row_width
                    self._bounding_box[2] = self._width
                self._last_x += found_glyph.width
                self.append(tg)
            else:
                bmp = None
                for cur_range in EmojiLabel.MULTI_CODE_RANGES:
                    # is it a valid multi code prefix
                    if cur_range[0] <= ord(char) <= cur_range[1]:
                        if ord(char) in EmojiLabel.FIVE_WIDES:
                            # try 5 wide file
                            try:
                                filename = f"emoji/U+{ord(char):X}_U+{ord(text[i + 1]):X}_U+{ord(text[i + 2]):X}_U+{ord(text[i + 3]):X}_U+{ord(text[i + 4]):X}.png"  # noqa: E501, Line too long
                                bmp, palette = adafruit_imageload.load(filename)
                                skip_count = 4
                                break
                            except (OSError, IndexError):
                                pass

                        # try 4 wide file
                        try:
                            filename = f"emoji/U+{ord(char):X}_U+{ord(text[i + 1]):X}_U+{ord(text[i + 2]):X}_U+{ord(text[i + 3]):X}.png"  # noqa: E501, Line too long
                            bmp, palette = adafruit_imageload.load(filename)
                            skip_count = 3
                            break
                        except (OSError, IndexError):
                            # try double wide file
                            try:
                                filename = f"emoji/U+{ord(char):X}_U+{ord(text[i + 1]):X}.png"
                                bmp, palette = adafruit_imageload.load(filename)
                                skip_count = 1
                                break
                            except (OSError, IndexError):
                                pass

                if bmp is None:
                    # it's not a multi code prefix
                    filename = f"emoji/U+{ord(char):X}.png"
                    try:
                        bmp, palette = adafruit_imageload.load(filename)
                    except OSError:
                        print(f"Unable to render: {hex(ord(char))}")

                try:
                    tg = displayio.TileGrid(bitmap=bmp, pixel_shader=palette)
                    tg.x = self._last_x
                    tg.y = self._last_y

                    self._row_width += bmp.width
                    if self._width < self._row_width:
                        self._width = self._row_width
                        self._bounding_box[2] = self._width
                    self._last_x += bmp.width + 1
                    self.append(tg)
                except TypeError:
                    # Unsupported bitmap type
                    print(f"Unable to render {hex(ord(char))}. Unsupported bitmap")
