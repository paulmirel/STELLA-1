# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_epd.uc8253` - Adafruit UC8253 - ePaper display driver
====================================================================================
CircuitPython driver for Adafruit UC8253 display breakouts
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
    from digitalio import DigitalInOut
    from typing_extensions import Literal

except ImportError:
    pass

__version__ = "2.18"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_EPD.git"

_UC8253_PANELSETTING = const(0x00)
_UC8253_POWEROFF = const(0x02)
_UC8253_POWERON = const(0x04)
_UC8253_DEEPSLEEP = const(0x07)
_UC8253_DISPLAYREFRESH = const(0x12)
_UC8253_WRITE_RAM1 = const(0x10)
_UC8253_WRITE_RAM2 = const(0x13)
_UC8253_VCOM_CDI = const(0x50)
_UC8253_GET_STATUS = const(0x71)

_BUSY_WAIT = const(500)


class Adafruit_UC8253(Adafruit_EPD):
    """Base driver class for Adafruit UC8253 ePaper display breakouts"""

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
        super().__init__(width, height, spi, cs_pin, dc_pin, sramcs_pin, rst_pin, busy_pin)

        self._single_byte_tx = True

        stride = height
        if stride % 8 != 0:
            stride += 8 - stride % 8

        self._buffer1_size = int(width * stride / 8)
        self._buffer2_size = self._buffer1_size

        if sramcs_pin:
            self._buffer1 = self.sram.get_view(0)
            self._buffer2 = self.sram.get_view(self._buffer1_size)
        else:
            self._buffer1 = bytearray(self._buffer1_size)
            self._buffer2 = bytearray(self._buffer2_size)

        self._framebuf1 = adafruit_framebuf.FrameBuffer(
            self._buffer1,
            width,
            height,
            buf_format=adafruit_framebuf.MHMSB,
        )
        self._framebuf2 = adafruit_framebuf.FrameBuffer(
            self._buffer2,
            width,
            height,
            buf_format=adafruit_framebuf.MHMSB,
        )

        self.set_black_buffer(0, True)
        self.set_color_buffer(1, False)

    def begin(self, reset: bool = True) -> None:
        """Begin communication with the display and set basic settings"""
        if reset:
            self.hardware_reset()
        self.power_up()
        self.power_down()

    def busy_wait(self) -> None:
        """Wait for display to be done with current task, either by polling the
        busy pin, or pausing"""
        if self._busy:
            while not self._busy.value:  # UC8253 waits for busy HIGH
                self.command(_UC8253_GET_STATUS)
                time.sleep(0.05)
        else:
            time.sleep(_BUSY_WAIT / 1000.0)  # Convert ms to seconds

    def power_up(self) -> None:
        """Power up the display in preparation for writing RAM and updating"""
        self.hardware_reset()
        # Default initialization sequence
        self.command(_UC8253_POWERON)
        self.busy_wait()
        # Panel settings with default values
        self.command(_UC8253_PANELSETTING, bytearray([0xCF, 0x8D]))
        self.busy_wait()

    def power_down(self) -> None:
        """Power down the display - required when not actively displaying!"""
        self.command(_UC8253_POWEROFF)
        self.busy_wait()
        time.sleep(1.0)

        if self._rst:
            self.command(_UC8253_DEEPSLEEP, bytearray([0xA5]))

    def update(self) -> None:
        """Update the display from internal memory"""
        self.command(_UC8253_DISPLAYREFRESH)
        time.sleep(0.1)
        self.busy_wait()

        if not self._busy:
            refresh_delay = getattr(self, "_refresh_delay", 1.0)
            time.sleep(refresh_delay)

    def write_ram(self, index: Literal[0, 1]) -> int:
        """Send the one byte command for starting the RAM write process. Returns
        the byte read at the same time over SPI. index is the RAM buffer, can be
        0 or 1 for tri-color displays."""
        if index == 0:
            return self.command(_UC8253_WRITE_RAM1, end=False)
        if index == 1:
            return self.command(_UC8253_WRITE_RAM2, end=False)
        raise RuntimeError("RAM index must be 0 or 1")

    def set_ram_address(self, x: int, y: int) -> None:
        """Set the RAM address location, not used on UC8253 but required by
        the superclass"""
        # UC8253 doesn't use RAM address setting
        pass


class Adafruit_UC8253_Mono(Adafruit_UC8253):
    """Driver for UC8253 monochrome ePaper displays (370 Mono BAAMFGN)"""

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
        super().__init__(
            width,
            height,
            spi,
            cs_pin=cs_pin,
            dc_pin=dc_pin,
            sramcs_pin=sramcs_pin,
            rst_pin=rst_pin,
            busy_pin=busy_pin,
        )
        # Set refresh delay for monochrome
        self._refresh_delay = 1.0  # 1000ms

    def begin(self, reset: bool = True) -> None:
        """Begin communication with the monochrome display"""
        if reset:
            self.hardware_reset()

        self.set_color_buffer(1, True)
        self.set_black_buffer(1, True)

    def power_up(self) -> None:
        """Power up the monochrome display with specific initialization"""
        self.hardware_reset()

        # Soft reset sequence
        self.command(_UC8253_POWERON)
        time.sleep(0.05)  # 50ms busy wait

        # VCOM CDI setting for monochrome
        self.command(_UC8253_VCOM_CDI, bytearray([0x97]))

        # Panel settings for monochrome: 0b11011111 = 0xDF
        self.command(_UC8253_PANELSETTING, bytearray([0xDF, 0x8D]))

        self.busy_wait()


class Adafruit_UC8253_Tricolor(Adafruit_UC8253):
    """Driver for UC8253 tricolor ePaper displays (370 Tricolor BABMFGNR)"""

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
        super().__init__(
            width,
            height,
            spi,
            cs_pin=cs_pin,
            dc_pin=dc_pin,
            sramcs_pin=sramcs_pin,
            rst_pin=rst_pin,
            busy_pin=busy_pin,
        )
        # Set refresh delay for tricolor
        self._refresh_delay = 13.0  # 13000ms

    def begin(self, reset: bool = True) -> None:
        """Begin communication with the tricolor display"""
        if reset:
            self.hardware_reset()

        self.set_color_buffer(0, True)  # Red/color buffer in RAM1, inverted
        self.set_black_buffer(1, False)  # Black buffer in RAM2, not inverted

    def power_up(self) -> None:
        """Power up the tricolor display with specific initialization"""
        self.hardware_reset()

        # Soft reset sequence
        self.command(_UC8253_POWERON)
        time.sleep(0.05)  # 50ms busy wait

        # Panel settings for tricolor: 0b11001111 = 0xCF
        self.command(_UC8253_PANELSETTING, bytearray([0xCF, 0x8D]))

        self.busy_wait()
