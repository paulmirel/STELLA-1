# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_color_terminal`
================================================================================

Extension of supports ANSI color escapes for subsets of text and optionally the
ASCII bell escape code.


* Author(s): Tim Cocks

Implementation Notes
--------------------

**Hardware:**


**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""

# imports

__version__ = "0.2.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Color_Terminal.git"

from audiocore import WaveFile
from displayio import Palette, TileGrid
from terminalio import Terminal
from tilepalettemapper import TilePaletteMapper

ANSI_TO_PALETTE_INDEX_MAP = {
    "30": 0,
    "31": 2,
    "32": 3,
    "33": 4,
    "34": 5,
    "35": 6,
    "36": 7,
    "37": 1,
    "90": 8,
    "40": 0,
    "41": 2,
    "42": 3,
    "43": 4,
    "44": 5,
    "45": 6,
    "46": 7,
    "47": 1,
    "100": 8,
}


class ColorTerminal:
    """
    Extension of terminalio.Terminal that supports ANSI color escapes for subsets of text

    :param font: The font to use for the terminal.
    :param width: The width of the terminal in characters.
    :param height: The height of the terminal in characters.
    :param custom_palette: A custom palette of colors to use instead of the default ones.
      Must contain at least 9 colors.
    :param audio_interface: The audio interface to use for playing ASCII bell escape codes.
    :param bell_audio_file: The wave audio file to use for the ASCII bell escape codes.
      Defaults to beep.wav
    """

    def __init__(
        self,
        font,
        width,
        height,
        custom_palette=None,
        audio_interface=None,
        bell_audio_file="/beep.wav",
    ):
        if custom_palette is None:
            self.terminal_palette = Palette(9)
            self.terminal_palette[0] = 0x000000
            self.terminal_palette[1] = 0xFFFFFF

            self.terminal_palette[2] = 0xFF0000
            self.terminal_palette[3] = 0x00FF00
            self.terminal_palette[4] = 0xFFFF00
            self.terminal_palette[5] = 0x4F4FFF
            self.terminal_palette[6] = 0xFF00FF
            self.terminal_palette[7] = 0x00FFFF
            self.terminal_palette[8] = 0xC9C9C9
        else:
            self.terminal_palette = custom_palette

        self.tpm = TilePaletteMapper(self.terminal_palette, 2)
        char_size = font.get_bounding_box()
        self.tilegrid = TileGrid(
            bitmap=font.bitmap,
            width=width,
            height=height,
            tile_width=char_size[0],
            tile_height=char_size[1],
            pixel_shader=self.tpm,
        )

        self.terminal = Terminal(self.tilegrid, font)

        self.old_cursor_x = None
        self.old_cursor_y = None

        self.cur_color_mapping = [0, 1]

        self.audio_interface = audio_interface
        if audio_interface is not None:
            beep_wave_file = open(bell_audio_file, "rb")
            self.beep_wave = WaveFile(beep_wave_file)

    @staticmethod
    def parse_ansi_colors(text):
        """
        Parse ANSI color escape codes from a string.

        Returns:
            tuple: (clean_string, color_map)
            - clean_string: string with all ANSI escape codes removed
            - color_map: dict mapping string indices to color codes (e.g., "32m", "0m")
        """
        color_map = {}
        clean_string = ""

        i = 0
        while i < len(text):
            # Look for ESC character (ASCII 27)
            if ord(text[i]) == 27 and i + 1 < len(text) and text[i + 1] == "[":
                # Found start of ANSI escape sequence
                escape_start = i
                i += 2  # Skip ESC and '['

                # Find the end of the escape sequence (look for 'm')
                while i < len(text) and text[i] != "m" and text[i] != chr(27):
                    i += 1

                if i < len(text) and text[i] == "m":
                    # Extract the color code (digits between '[' and 'm')
                    color_code = text[escape_start + 2 : i] + "m"
                    color_map[len(clean_string)] = color_code
                    i += 1  # Skip the 'm'
                else:
                    # Non-color escape, or malformed escape sequence, treat as regular text
                    clean_string += text[escape_start]
                    i = escape_start + 1
            else:
                # Regular character, add to clean string
                clean_string += text[i]
                i += 1
        return clean_string, color_map

    def get_color_mapping(self, color_code):
        """
        given an ANSI escape code like '32;45m' return the
        mapping used by TilePaletteMapper to represent the specified
        color code.

        :param string color_code: ANSI color escape code
        """
        background = self.cur_color_mapping[0]
        foreground = self.cur_color_mapping[1]

        # remove trailing m
        color_code = color_code[:-1]

        parts = color_code.split(";")

        for part in parts:
            if part.startswith("3") or part.startswith("9") and part in ANSI_TO_PALETTE_INDEX_MAP:
                foreground = ANSI_TO_PALETTE_INDEX_MAP[part]
            elif (
                part.startswith("4") or part.startswith("10") and part in ANSI_TO_PALETTE_INDEX_MAP
            ):
                background = ANSI_TO_PALETTE_INDEX_MAP[part]
            elif part == "0":
                background = 0
                foreground = 1
        return [background, foreground]

    def apply_color(self, string):
        """
        Set the current color into the TilePaletteMapper from the
        current cursor position to the end of the given string.

        :param string: The string that will have its color set
        """
        starting_x = self.terminal.cursor_x
        y = self.terminal.cursor_y

        for x in range(starting_x, starting_x + len(string)):
            self.tpm[x, y] = self.cur_color_mapping

    def write(self, s):
        """
        Write a string to the terminal. If it contains ANSI color escape codes
        then the TilePaletteMapper will be adjusted to map to the given colors
        for the specified subsets of text.

        :param s: The string to write.
        """
        clean_message, color_map = ColorTerminal.parse_ansi_colors(s)

        ordered_color_change_indexes = sorted(color_map.keys())
        cur_change_index = 0

        if not color_map:
            self.terminal.write(s)
            if (
                "\x07" in s
                and self.audio_interface is not None
                and not self.audio_interface.playing
            ):
                print("playing beep")
                self.audio_interface.play(self.beep_wave)
            return

        idx = 0
        while idx < len(clean_message):
            if idx in color_map:
                self.cur_color_mapping = self.get_color_mapping(color_map[idx])

            if cur_change_index < len(ordered_color_change_indexes):
                cur_slice = clean_message[idx : ordered_color_change_indexes[cur_change_index]]
                cur_change_index += 1
            else:
                cur_slice = clean_message[idx:]

            idx += len(cur_slice)

            if "\n" in cur_slice:
                lines = cur_slice.split("\n")
                for i, line in enumerate(lines):
                    self.apply_color(line)
                    if i < len(lines) - 1:
                        self.terminal.write(line + "\n")
                    else:
                        self.terminal.write(line)
                continue

            self.apply_color(cur_slice)
            self.terminal.write(cur_slice)
            if (
                "\x07" in cur_slice
                and self.audio_interface is not None
                and not self.audio_interface.playing
            ):
                self.audio_interface.play(self.beep_wave)

        # index after last can be in the color map if color code is last thing in string
        if idx in color_map:
            self.cur_color_mapping = self.get_color_mapping(color_map[idx])

    def update_visual_cursor(self):
        """
        Move the visible cursor to the current cursor location.
        Visible cursor is denoted by inverted color mapping.
        :return:
        """
        if self.old_cursor_x is not None and self.old_cursor_y is not None:
            highlighted = list(self.tpm[self.old_cursor_x, self.old_cursor_y])
            normal = list(reversed(highlighted))
            self.tpm[self.old_cursor_x, self.old_cursor_y] = normal

        normal = list(self.tpm[self.cursor_x, self.cursor_y])
        highlighted = list(reversed(normal))
        self.tpm[self.cursor_x, self.cursor_y] = highlighted
        self.old_cursor_x = self.cursor_x
        self.old_cursor_y = self.cursor_y

    @property
    def cursor_x(self):
        """
        The x position of the cursor
        :return:
        """
        return self.terminal.cursor_x

    @property
    def cursor_y(self):
        """
        The y position of the cursor
        :return:
        """
        return self.terminal.cursor_y
