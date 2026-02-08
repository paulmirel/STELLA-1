# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_epd.jd79667` - Adafruit JD79667 - quad-color ePaper display driver
====================================================================================
CircuitPython driver for Adafruit JD79667 quad-color display breakouts
* Author(s): Liz Clark
"""

import time

import adafruit_framebuf
from micropython import const

from adafruit_epd.epd import Adafruit_EPD

try:
    """Needed for type annotations"""
    import typing

    from busio import SPI
    from circuitpython_typing.pil import Image
    from digitalio import DigitalInOut
    from typing_extensions import Literal

except ImportError:
    pass

__version__ = "2.18"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_EPD.git"

# Command constants
_JD79667_PANEL_SETTING = const(0x00)
_JD79667_POWER_SETTING = const(0x01)
_JD79667_POWER_OFF = const(0x02)
_JD79667_POWER_ON = const(0x04)
_JD79667_BOOSTER_SOFTSTART = const(0x06)
_JD79667_DEEP_SLEEP = const(0x07)
_JD79667_DATA_START_XMIT = const(0x10)
_JD79667_DISPLAY_REFRESH = const(0x12)
_JD79667_PLL_CONTROL = const(0x30)
_JD79667_CDI = const(0x50)
_JD79667_RESOLUTION = const(0x61)

# Color constants for internal use (2-bit values)
_JD79667_BLACK = const(0b00)
_JD79667_WHITE = const(0b01)
_JD79667_YELLOW = const(0b10)
_JD79667_RED = const(0b11)

# Other command constants from init sequence
_JD79667_POFS = const(0x03)
_JD79667_TCON = const(0x60)
_JD79667_CMD_E7 = const(0xE7)
_JD79667_CMD_E3 = const(0xE3)
_JD79667_CMD_B4 = const(0xB4)
_JD79667_CMD_B5 = const(0xB5)
_JD79667_CMD_E9 = const(0xE9)
_JD79667_CMD_4D = const(0x4D)


class Adafruit_JD79667(Adafruit_EPD):
    """Driver for the JD79667 quad-color ePaper display breakouts"""

    BLACK = const(0)  # 0b00 in the display buffer
    WHITE = const(1)  # 0b01 in the display buffer
    YELLOW = const(2)  # 0b10 in the display buffer
    RED = const(3)  # 0b11 in the display buffer

    def __init__(
        self,
        width: int,
        height: int,
        spi: SPI,
        *,
        cs_pin: DigitalInOut,
        dc_pin: DigitalInOut,
        sramcs_pin: DigitalInOut,
        rst_pin: DigitalInOut,
        busy_pin: DigitalInOut,
    ) -> None:
        """Initialize the JD79667 quad-color display driver.

        Note: This driver uses a single buffer with 2 bits per pixel to represent 4 colors.
        Width must be divisible by 4 for proper pixel packing (4 pixels per byte).

        Args:
            width: Display width in pixels
            height: Display height in pixels
            spi: SPI bus object
            cs_pin: Chip select pin
            dc_pin: Data/command pin
            sramcs_pin: SRAM chip select pin (can be None)
            rst_pin: Reset pin
            busy_pin: Busy status pin
        """
        super().__init__(width, height, spi, cs_pin, dc_pin, sramcs_pin, rst_pin, busy_pin)

        stride = width
        if stride % 8 != 0:
            stride += 8 - stride % 8

        self._buffer1_size = int(stride * height / 4)
        self._buffer2_size = 0

        if sramcs_pin:
            self._buffer1 = self.sram.get_view(0)
            self._buffer2 = self._buffer1
        else:
            self._buffer1 = bytearray(self._buffer1_size)
            self._buffer2 = self._buffer1

        self._framebuf1 = adafruit_framebuf.FrameBuffer(
            self._buffer1,
            width,
            height,
            stride=stride,
            buf_format=adafruit_framebuf.MHMSB,
        )
        self._framebuf2 = self._framebuf1

        self._single_byte_tx = True

        self.set_black_buffer(0, False)
        self.set_color_buffer(0, False)

        self.fill(Adafruit_JD79667.WHITE)

    def begin(self, reset: bool = True) -> None:
        """Begin communication with the display and set basic settings"""
        if reset:
            self.hardware_reset()
        time.sleep(0.1)

    def busy_wait(self) -> None:
        """Wait for display to be done with current task."""
        if self._busy:
            while not self._busy.value:  # Wait for busy HIGH
                time.sleep(0.01)
        else:
            time.sleep(0.5)

    def hardware_reset(self) -> None:
        """Perform hardware reset sequence specific to JD79667"""
        if self._rst:
            # VDD goes high at start
            self._rst.value = True
            time.sleep(0.02)  # 20ms
            # Bring reset low
            self._rst.value = False
            time.sleep(0.04)  # 40ms
            # Bring out of reset
            self._rst.value = True
            time.sleep(0.05)  # 50ms

    def power_up(self) -> None:
        """Power up the display in preparation for writing RAM and updating"""
        self.hardware_reset()
        self.busy_wait()

        # Send initialization sequence
        time.sleep(0.01)  # Wait 10ms

        self.command(_JD79667_CMD_4D, bytearray([0x78]))
        self.command(
            _JD79667_PANEL_SETTING, bytearray([0x0F, 0x29])
        )  # Display resolution is 180x384
        self.command(_JD79667_POWER_SETTING, bytearray([0x07, 0x00]))
        self.command(_JD79667_POFS, bytearray([0x10, 0x54, 0x44]))
        self.command(
            _JD79667_BOOSTER_SOFTSTART,
            bytearray([0x05, 0x00, 0x3F, 0x0A, 0x25, 0x12, 0x1A]),
        )
        self.command(_JD79667_CDI, bytearray([0x37]))
        self.command(_JD79667_TCON, bytearray([0x02, 0x02]))
        self.command(_JD79667_RESOLUTION, bytearray([0, 180, 1, 128]))  # 180x384
        self.command(_JD79667_CMD_E7, bytearray([0x1C]))
        self.command(_JD79667_CMD_E3, bytearray([0x22]))
        self.command(_JD79667_CMD_B4, bytearray([0xD0]))
        self.command(_JD79667_CMD_B5, bytearray([0x03]))
        self.command(_JD79667_CMD_E9, bytearray([0x01]))
        self.command(_JD79667_PLL_CONTROL, bytearray([0x08]))
        self.command(_JD79667_POWER_ON)

        self.busy_wait()

    def power_down(self) -> None:
        """Power down the display"""
        if self._rst:
            self.command(_JD79667_POWER_OFF, bytearray([0x00]))
            self.busy_wait()
            time.sleep(0.1)
            self.command(_JD79667_DEEP_SLEEP, bytearray([0xA5]))

    def update(self) -> None:
        """Update the display from internal memory"""
        self.command(_JD79667_DISPLAY_REFRESH, bytearray([0x00]))
        self.busy_wait()
        if not self._busy:
            time.sleep(1)  # Wait 1 second if no busy pin

    def write_ram(self, index: Literal[0, 1]) -> int:
        """Send the one byte command for starting the RAM write process."""
        return self.command(_JD79667_DATA_START_XMIT, end=False)

    def set_ram_address(self, x: int, y: int) -> None:
        """Set the RAM address location."""
        pass

    def fill(self, color: int) -> None:
        """Fill the entire display with the specified color."""
        # Map colors to fill patterns (4 pixels per byte)
        color_map = {
            Adafruit_JD79667.BLACK: 0x00,  # 0b00000000 - all pixels black
            Adafruit_JD79667.WHITE: 0x55,  # 0b01010101 - all pixels white
            Adafruit_JD79667.YELLOW: 0xAA,  # 0b10101010 - all pixels yellow
            Adafruit_JD79667.RED: 0xFF,  # 0b11111111 - all pixels red
        }

        if color not in color_map:
            raise ValueError(
                f"Invalid color: {color}. Use BLACK (0), WHITE (1), YELLOW (2), or RED (3)."
            )

        fill_byte = color_map[color]

        if self.sram:
            self.sram.erase(0x00, self._buffer1_size, fill_byte)
        else:
            for i in range(self._buffer1_size):
                self._buffer1[i] = fill_byte

    def clear_buffer(self) -> None:
        """Clear the display buffer to white"""
        self.fill(Adafruit_JD79667.WHITE)

    def pixel(self, x: int, y: int, color: int) -> None:
        """Draw a single pixel in the display buffer."""
        if (x < 0) or (x >= self.width) or (y < 0) or (y >= self.height):
            return
        stride = self._width
        if stride % 4 != 0:
            stride += 4 - (stride % 4)
        if self.rotation == 1:
            x, y = y, x
            x = stride - x - 1
            x -= stride - self._width
        elif self.rotation == 2:
            x = stride - x - 1
            y = self._height - y - 1
            x += stride - self._width
        elif self.rotation == 3:
            x, y = y, x
            y = self._height - y - 1

        color_map = {
            Adafruit_JD79667.BLACK: _JD79667_BLACK,
            Adafruit_JD79667.WHITE: _JD79667_WHITE,
            Adafruit_JD79667.YELLOW: _JD79667_YELLOW,
            Adafruit_JD79667.RED: _JD79667_RED,
        }

        if color not in color_map:
            pixel_color = _JD79667_WHITE
        else:
            pixel_color = color_map[color]

        addr = (x + y * stride) // 4
        bit_offset = (3 - (x % 4)) * 2
        byte_mask = 0x3 << bit_offset
        byte_value = (pixel_color & 0x3) << bit_offset

        if self.sram:
            current = self.sram.read8(addr)
            current &= ~byte_mask
            current |= byte_value
            self.sram.write8(addr, current)
        else:
            self._buffer1[addr] &= ~byte_mask
            self._buffer1[addr] |= byte_value

    def rect(self, x: int, y: int, width: int, height: int, color: int) -> None:
        """Draw a rectangle."""
        for i in range(x, x + width):
            self.pixel(i, y, color)
            self.pixel(i, y + height - 1, color)
        for j in range(y + 1, y + height - 1):
            self.pixel(x, j, color)
            self.pixel(x + width - 1, j, color)

    def fill_rect(self, x: int, y: int, width: int, height: int, color: int) -> None:
        """Fill a rectangle with the passed color."""
        for i in range(x, x + width):
            for j in range(y, y + height):
                self.pixel(i, j, color)

    def line(self, x_0: int, y_0: int, x_1: int, y_1: int, color: int) -> None:
        """Draw a line from (x_0, y_0) to (x_1, y_1) in passed color."""
        dx = abs(x_1 - x_0)
        dy = abs(y_1 - y_0)
        sx = 1 if x_0 < x_1 else -1
        sy = 1 if y_0 < y_1 else -1
        err = dx - dy

        while True:
            self.pixel(x_0, y_0, color)
            if x_0 == x_1 and y_0 == y_1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x_0 += sx
            if e2 < dx:
                err += dx
                y_0 += sy

    def text(
        self,
        string: str,
        x: int,
        y: int,
        color: int,
        *,
        font_name: str = "font5x8.bin",
        size: int = 1,
    ) -> None:
        """Write text string at location (x, y) in given color, using font file."""
        color_map = {
            Adafruit_JD79667.BLACK: _JD79667_BLACK,
            Adafruit_JD79667.WHITE: _JD79667_WHITE,
            Adafruit_JD79667.YELLOW: _JD79667_YELLOW,
            Adafruit_JD79667.RED: _JD79667_RED,
        }
        if color not in color_map:
            raise ValueError(
                f"Invalid color: {color}. Use BLACK (0), WHITE (1), YELLOW (2), or RED (3)."
            )

        text_width = len(string) * 6 * size
        text_height = 8 * size

        text_width = min(text_width, self.width - x)
        text_height = min(text_height, self.height - y)

        if text_width <= 0 or text_height <= 0:
            return

        temp_buf_width = ((text_width + 7) // 8) * 8
        temp_buf = bytearray((temp_buf_width * text_height) // 8)

        temp_fb = adafruit_framebuf.FrameBuffer(
            temp_buf, temp_buf_width, text_height, buf_format=adafruit_framebuf.MHMSB
        )

        temp_fb.fill(0)
        temp_fb.text(string, 0, 0, 1, font_name=font_name, size=size)

        for j in range(text_height):
            for i in range(text_width):
                byte_index = (j * temp_buf_width + i) // 8
                bit_index = 7 - ((j * temp_buf_width + i) % 8)

                if byte_index < len(temp_buf):
                    if (temp_buf[byte_index] >> bit_index) & 1:
                        self.pixel(x + i, y + j, color)

    def image(self, image: Image) -> None:
        """Set buffer to value of Python Imaging Library image."""
        imwidth, imheight = image.size
        if imwidth != self.width or imheight != self.height:
            raise ValueError(
                f"Image must be same dimensions as display ({self.width}x{self.height})."
            )
        if self.sram:
            raise RuntimeError("PIL image is not for use with SRAM assist")
        pix = image.load()
        self.fill(Adafruit_JD79667.WHITE)

        if image.mode == "RGB":  # RGB Mode
            for y in range(image.size[1]):
                for x in range(image.size[0]):
                    pixel = pix[x, y]
                    r, g, b = pixel[0], pixel[1], pixel[2]
                    brightness = (r + g + b) / 3

                    if brightness >= 200:
                        pass
                    elif r >= 128 and g >= 128 and b < 80:
                        self.pixel(x, y, Adafruit_JD79667.YELLOW)
                    elif r >= 128 and g < 80 and b < 80:
                        self.pixel(x, y, Adafruit_JD79667.RED)
                    elif brightness < 80:
                        self.pixel(x, y, Adafruit_JD79667.BLACK)
                    elif r > g and r > b and r >= 100:
                        self.pixel(x, y, Adafruit_JD79667.RED)
                    elif r >= 100 and g >= 100:
                        self.pixel(x, y, Adafruit_JD79667.YELLOW)
                    elif brightness < 128:
                        self.pixel(x, y, Adafruit_JD79667.BLACK)

        elif image.mode == "L":
            for y in range(image.size[1]):
                for x in range(image.size[0]):
                    pixel = pix[x, y]
                    if pixel < 64:
                        self.pixel(x, y, Adafruit_JD79667.BLACK)
                    elif pixel < 128:
                        self.pixel(x, y, Adafruit_JD79667.RED)
                    elif pixel < 192:
                        self.pixel(x, y, Adafruit_JD79667.YELLOW)

        elif image.mode == "P":  # Palette Mode
            rgb_image = image.convert("RGB")
            self.image(rgb_image)

        else:
            raise ValueError("Image must be in mode RGB, L, or P.")
