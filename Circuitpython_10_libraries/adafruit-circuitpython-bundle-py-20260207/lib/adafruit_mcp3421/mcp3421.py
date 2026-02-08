# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# Written by Liz Clark (Adafruit Industries)
# with OpenAI ChatGPT v4 November 21, 2023 build
# https://help.openai.com/en/articles/6825453-chatgpt-release-notes

# https://chat.openai.com/share/1fe7ea12-4f7c-493a-98d2-68210638292b
"""
:py:class:`~adafruit_mcp3421.mcp3421.MCP3421`
================================================================================

CircuitPython driver for the MCP3421 analog to digital converter


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit MCP3421 18-Bit ADC: <https://adafruit.com/product/5870>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

from adafruit_bus_device.i2c_device import I2CDevice

__version__ = "1.1.5"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_MCP3421.git"


class MCP3421:
    """Adafruit MCP3421 ADC driver"""

    MCP3421_GAIN = {
        1: 0b00,  # Gain set to 1X
        2: 0b01,  # Gain set to 2X
        4: 0b10,  # Gain set to 4X
        8: 0b11,  # Gain set to 8X
    }

    MCP3421_RESOLUTION = {
        12: 0b00,  # Resolution set to 12-bit (240 SPS)
        14: 0b01,  # Resolution set to 14-bit (60 SPS)
        16: 0b10,  # Resolution set to 16-bit (15 SPS)
        18: 0b11,  # Resolution set to 18-bit (3.75 SPS)
    }
    _gain = 1
    _resolution = 14
    _ready = 0b0  # Ready bit, defaulting to 0

    def __init__(self, i2c, address=0x68, gain=None, resolution=None, continuous_mode=True) -> None:
        """Initialization over I2C

        :param int address: I2C address (default 0x68)
        :param int gain: Select 1X, 2X, 4X or 8X gain (defaults to 1X)
        :param int resolution: Select 12, 14, 16 or 18 bit resolution (defaults to 14-bit)
        :param bool continuous_mode: Select continuous sampling or one shot sampling
        """
        self.i2c_device = I2CDevice(i2c, address)
        if gain is not None:
            self._gain = gain

        if resolution is not None:
            self._resolution = resolution

        self._mode = continuous_mode

        self.gain = self._gain
        self.resolution = self._resolution
        self.continuous_mode = self._mode

        self.adc_data = bytearray(4)

    def _read_data(self):
        buffer = bytearray(4)  # Buffer to read data
        with self.i2c_device as device:
            try:
                device.readinto(buffer)
            except Exception as error:
                raise OSError(f"{error}") from error

            # Extract ADC data
            self.adc_data = buffer[:3]

            # Initially, update the configuration from the fourth byte
            self._update_config(buffer[3])

            # For 12, 14, or 16-bit resolutions, update the config byte using the third byte
            if (self._resolution & 0b11) != self.MCP3421_RESOLUTION[18]:
                self._update_config(buffer[2])

    def _update_config(self, config_byte):
        self._gain = config_byte & 0b11  # Gain is in bits 1-0
        self._resolution = (config_byte >> 2) & 0b11  # Resolution is in bits 3-2
        self._mode = (config_byte >> 4) & 0b1  # Mode is in bit 4
        self._ready = (config_byte >> 7) & 0b1  # Ready bit is in bit 7

    @property
    def _register_value(self) -> int:
        """
        Combine all fields into a single byte

        :rtype: int
        """
        # Ensure that each field is within its valid range
        gain_bits = self._gain & 0b11  # Gain is in bits 1-0
        resolution_bits = self._resolution & 0b11  # Resolution is in bits 3-2
        mode_bit = 0b1 if self._mode else 0b0  # Mode is in bit 4

        # Combine the fields into a single configuration byte
        config_byte = (gain_bits) | (resolution_bits << 2) | (mode_bit << 4)
        return config_byte

    @property
    def gain(self) -> int:
        """
        The current gain setting from the device, translated to user-friendly value

        :rtype: int
        """
        self._read_data()  # Update data and check if read was successful
        # Translate the bit pattern back to the user-friendly gain value
        for gain_value, bit_pattern in self.MCP3421_GAIN.items():
            if self._gain == bit_pattern:
                return gain_value
        # Raise an exception if no match is found
        raise ValueError(f"Invalid gain bit pattern: {self._gain}")

    @gain.setter
    def gain(self, value: int) -> None:
        if value not in self.MCP3421_GAIN:
            raise ValueError("Invalid gain value")
        self._gain = self.MCP3421_GAIN[value]  # Translate to bit pattern
        config_byte = self._register_value
        with self.i2c_device as device:
            device.write(bytes([config_byte]))

    @property
    def resolution(self) -> int:
        """
        The current resolution setting from the device, translated to user-friendly value

        :rtype: int
        """
        self._read_data()  # Update data and check if read was successful
        # Translate the bit pattern back to the user-friendly resolution value
        for resolution_value, bit_pattern in self.MCP3421_RESOLUTION.items():
            if self._resolution == bit_pattern:
                return resolution_value
        # Raise an exception if no match is found
        raise ValueError(f"Invalid gain bit pattern: {self._resolution}")

    @resolution.setter
    def resolution(self, value: int) -> None:
        if value not in self.MCP3421_RESOLUTION:
            raise ValueError("Invalid resolution value")
        self._resolution = self.MCP3421_RESOLUTION[value]  # Translate to bit pattern
        config_byte = self._register_value
        with self.i2c_device as device:
            device.write(bytes([config_byte]))

    @property
    def continuous_mode(self) -> bool:
        """
        Current mode setting from the device

        :rtype: bool
        """
        try:
            self._read_data()  # Update data and check if read was successful
            return self._mode
        except Exception as error:
            raise OSError(f"Failed to read mode from device: {error}") from error

    @continuous_mode.setter
    def continuous_mode(self, value: bool) -> None:
        self._mode = value
        config_byte = self._register_value
        with self.i2c_device as device:
            device.write(bytes([config_byte]))

    def read(self) -> int:
        """ADC value

        :return: ADC value
        :rtype: int
        """
        try:
            self._read_data()
        except Exception as error:
            raise OSError(f"Failed to read from device: {error}") from error

        adc_value = 0
        if self._resolution in {
            self.MCP3421_RESOLUTION[12],
            self.MCP3421_RESOLUTION[14],
            self.MCP3421_RESOLUTION[16],
        }:
            # Directly cast the first two bytes to int16_t
            adc_value = (self.adc_data[0] << 8) | self.adc_data[1]
            if self.adc_data[0] & 0x80:  # Check if the top bit is set for sign extension
                adc_value -= 0x10000
        elif self._resolution == self.MCP3421_RESOLUTION[18]:
            # Use all three bytes, considering the differential nature
            adc_value = (self.adc_data[0] << 16) | (self.adc_data[1] << 8) | self.adc_data[2]
            if self.adc_data[0] & 0x80:  # Extend the sign if the top bit is set
                adc_value = adc_value - 0x1000000  # Sign-extend to 32 bits
        return adc_value
