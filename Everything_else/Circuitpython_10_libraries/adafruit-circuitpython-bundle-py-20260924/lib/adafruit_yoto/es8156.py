# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
`adafruit_yoto.es8156`
================================================================================

CircuitPython driver for the ES8156 I2S DAC


* Author(s): Liz Clark

"""

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_struct import UnaryStruct
from micropython import const

_VOLUME_CONTROL = const(0x14)
_MUTE_CONTROL = const(0x13)
_ANALOG_SYSTEM_3 = const(0x22)
_PAGE_SELECT = const(0xFC)
_CHIP_ID1 = const(0xFD)
_CHIP_ID0 = const(0xFE)
_CHIP_VERSION = const(0xFF)
_CHIP_ID = const(0x8155)


class ES8156:
    """Driver for the ES8156 I2S DAC"""

    _page_select = RWBit(_PAGE_SELECT, 0, register_width=1)
    volume = UnaryStruct(_VOLUME_CONTROL, "B")
    """Volume level (0-255, where 0 is mute and 255 is maximum)"""
    left_mute = RWBit(_MUTE_CONTROL, 1, register_width=1)
    right_mute = RWBit(_MUTE_CONTROL, 2, register_width=1)
    _out_mute_bit = RWBit(_ANALOG_SYSTEM_3, 0, register_width=1)

    def __init__(self, i2c_bus, address=0x08):
        """Initialize the ES8156 DAC.

        :param ~busio.I2C i2c_bus: The I2C bus the device is connected to
        :param int address: The I2C device address (default: 0x08)
        """
        self.i2c_device = I2CDevice(i2c_bus, address)
        self._current_page = 0

        if self.chip_id != _CHIP_ID:
            raise RuntimeError(f"Failed to find ES8156! Chip ID: 0x{self.chip_id:04X}")

    def _select_page(self, page):
        if self._current_page != page:
            self._page_select = page
            self._current_page = page

    def _write_register(self, reg, value):
        with self.i2c_device as i2c:
            i2c.write(bytes([reg, value]))

    @property
    def chip_id(self):
        """Chip ID."""
        self._select_page(0)
        buf1 = bytearray(1)
        buf0 = bytearray(1)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([_CHIP_ID1]), buf1)
            i2c.write_then_readinto(bytes([_CHIP_ID0]), buf0)
        return (buf1[0] << 8) | buf0[0]

    @property
    def chip_version(self):
        """Chip version."""
        self._select_page(0)
        buf = bytearray(1)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([_CHIP_VERSION]), buf)
        return (buf[0] >> 4) & 0x0F

    @property
    def mute(self):
        """Mute for all outputs (True = muted, False = unmuted)"""
        return self.left_mute or self.right_mute or self._out_mute_bit

    @mute.setter
    def mute(self, value):
        self.left_mute = value
        self.right_mute = value
        self._out_mute_bit = value

    def configure(self, use_sclk_as_mclk=False):
        """Configure the ES8156 with default settings for I2S peripheral mode.

        :param bool use_sclk_as_mclk: Use SCLK as main clock source (default: False)

        This configures the ES8156 for:
        - I2S peripheral mode
        - 16-bit audio
        - Internal clock generation from SCLK (if use_sclk_as_mclk=True)
        - All analog outputs powered up and unmuted
        """
        self._select_page(0)

        self._write_register(0x00, 0b00000010)

        if use_sclk_as_mclk:
            self._write_register(0x02, 0b11000100)
            self._write_register(0x01, 0b11000001)
            self._write_register(0x09, 0b00100010)
            self._write_register(0x07, 0b00001100)
        else:
            self._write_register(0x02, 0b00000100)
            self._write_register(0x01, 0b00100000)
            self._write_register(0x09, 0b00000000)

        self._write_register(0x0A, 0x01)
        self._write_register(0x0B, 0x01)
        self._write_register(0x20, 0b00101010)
        self._write_register(0x21, 0b00111100)
        self._write_register(0x22, 0b00000000)
        self._write_register(0x23, 0b00000100)
        self._write_register(0x24, 0b00000111)
        self._write_register(0x11, 0b00110000)
        self._write_register(0x0D, 0b00010100)
        self._write_register(0x18, 0b00000000)
        self._write_register(0x08, 0b00111111)
        self._write_register(0x00, 0b00000011)
        self._write_register(0x25, 0b00100000)
        self._write_register(0x13, 0b00000000)

        self.volume = 180
