# SPDX-FileCopyrightText: Copyright (c) 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_pcm51xx`
================================================================================

CircuitPython driver for the Adafruit PCM51xx I2S DAC


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit PCM5122 I2S DAC with Line Level Output <https://www.adafruit.com/product/6421>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

import time

from adafruit_bus_device.i2c_device import I2CDevice
from micropython import const

try:
    import typing  # pylint: disable=unused-import

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_PCM51xx.git"

# I2C Address
PCM51XX_DEFAULT_ADDR = const(0x4C)

# Page 0 Register Addresses
_PAGE_SELECT = const(0x00)
_RESET = const(0x01)
_STANDBY = const(0x02)
_MUTE = const(0x03)
_PLL = const(0x04)
_DEEMPHASIS = const(0x07)
_GPIO_ENABLE = const(0x08)
_PLL_REF = const(0x0D)
_DAC_CLK_SRC = const(0x0E)
_ERROR_DETECT = const(0x25)
_I2S_CONFIG = const(0x28)
_AUTO_MUTE = const(0x41)
_GPIO5_OUTPUT = const(0x54)
_GPIO_CONTROL = const(0x56)
_DIGITAL_VOLUME_L = const(0x3D)
_DIGITAL_VOLUME_R = const(0x3E)
_POWER_STATE = const(0x76)
_GPIO_INPUT = const(0x77)

# Page 1 Register Addresses
_PAGE1_OUTPUT_AMP_TYPE = const(0x01)
_PAGE1_VCOM_POWER = const(0x09)

# I2S Data Format
I2S_FORMAT_I2S = const(0)
I2S_FORMAT_TDM = const(1)
I2S_FORMAT_RTJ = const(2)
I2S_FORMAT_LTJ = const(3)

# I2S Word Length
I2S_SIZE_16BIT = const(0)
I2S_SIZE_20BIT = const(1)
I2S_SIZE_24BIT = const(2)
I2S_SIZE_32BIT = const(3)

# PLL Reference Clock Source
PLL_REF_SCK = const(0)
PLL_REF_BCK = const(1)
PLL_REF_GPIO = const(3)

# DAC Clock Source
DAC_CLK_MASTER = const(0)
DAC_CLK_PLL = const(1)
DAC_CLK_SCK = const(3)
DAC_CLK_BCK = const(4)

# Power State
POWER_POWERDOWN = const(0)
POWER_WAIT_CP_VALID = const(1)
POWER_CALIBRATION_1 = const(2)
POWER_CALIBRATION_2 = const(3)
POWER_VOLUME_RAMP_UP = const(4)
POWER_RUN_PLAYING = const(5)
POWER_LINE_SHORT = const(6)
POWER_VOLUME_RAMP_DOWN = const(7)
POWER_STANDBY = const(8)

# GPIO5 Output Selection
GPIO5_OFF = const(0x00)
GPIO5_DSP_OUTPUT = const(0x01)
GPIO5_REGISTER_OUTPUT = const(0x02)
GPIO5_AUTO_MUTE_FLAG = const(0x03)
GPIO5_AUTO_MUTE_L = const(0x04)
GPIO5_AUTO_MUTE_R = const(0x05)
GPIO5_CLOCK_INVALID = const(0x06)
GPIO5_SDOUT = const(0x07)
GPIO5_ANALOG_MUTE_L = const(0x08)
GPIO5_ANALOG_MUTE_R = const(0x09)
GPIO5_PLL_LOCK = const(0x0A)
GPIO5_CHARGE_PUMP_CLK = const(0x0B)
GPIO5_UNDER_VOLT_07 = const(0x0E)
GPIO5_UNDER_VOLT_03 = const(0x0F)
GPIO5_PLL_OUT_DIV4 = const(0x10)


class PCM51XX:  # noqa: PLR0904
    """Driver for the PCM51xx I2S DAC.

    :param ~busio.I2C i2c_bus: The I2C bus the PCM51xx is connected to.
    :param int address: The I2C device address. Defaults to :const:`PCM51XX_DEFAULT_ADDR`
    """

    def __init__(self, i2c_bus: I2C, address: int = PCM51XX_DEFAULT_ADDR) -> None:
        self.i2c_device = I2CDevice(i2c_bus, address)
        self._current_page = 0xFF  # Initialize to invalid page to force first selection

        # Initialize the device
        self._init()

        # Create pin objects
        self.pin1 = self.Pin(self, 1)
        self.pin2 = self.Pin(self, 2)
        self.pin3 = self.Pin(self, 3)
        self.pin4 = self.Pin(self, 4)
        self.pin5 = self.Pin(self, 5)
        self.pin6 = self.Pin(self, 6)

    def _write_register(self, register: int, value: int) -> None:
        """Write a byte to a register."""
        with self.i2c_device as i2c:
            i2c.write(bytes([register | 0x80, value]))  # Set bit 7 for write

    def _read_register(self, register: int) -> int:
        """Read a byte from a register."""
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([register & 0x7F]), self._buf1)
        return self._buf1[0]

    def _select_page(self, page: int) -> None:
        """Select register page."""
        if self._current_page != page:
            self._write_register(_PAGE_SELECT, page)
            self._current_page = page

    def _write_register_bit(self, register: int, bit: int, value: bool) -> None:
        """Write a single bit in a register."""
        current = self._read_register(register)
        if value:
            current |= 1 << bit
        else:
            current &= ~(1 << bit)
        self._write_register(register, current)

    def _read_register_bit(self, register: int, bit: int) -> bool:
        """Read a single bit from a register."""
        return bool((self._read_register(register) >> bit) & 1)

    def _write_register_bits(self, register: int, bits: int, shift: int, value: int) -> None:
        """Write multiple bits in a register."""
        mask = ((1 << bits) - 1) << shift
        current = self._read_register(register)
        current = (current & ~mask) | ((value << shift) & mask)
        self._write_register(register, current)

    def _read_register_bits(self, register: int, bits: int, shift: int) -> int:
        """Read multiple bits from a register."""
        mask = (1 << bits) - 1
        return (self._read_register(register) >> shift) & mask

    def _init(self) -> None:
        """Initialize the device."""
        self._buf1 = bytearray(1)

        # Force page selection
        self._select_page(0)

        # Put device into standby before reset
        self.standby = True

        # Reset registers and modules
        self.reset_registers()
        self.reset_modules()

        # Take out of powerdown and standby
        self.powerdown = False
        self.standby = False

        # Configure error detection and default settings
        self.ignore_fs_detect = True
        self.ignore_bck_detect = True
        self.ignore_sck_detect = True
        self.ignore_clock_halt = True
        self.ignore_clock_missing = True
        self.disable_clock_autoset = False
        self.ignore_pll_unlock = True

        # Configure PLL and clocks
        self.pll_enabled = True
        self.pll_reference = PLL_REF_BCK
        self.dac_source = DAC_CLK_PLL

        # Configure I2S
        self.i2s_format = I2S_FORMAT_I2S
        self.i2s_size = I2S_SIZE_16BIT

        # Configure mute
        self.auto_mute = False
        self.mute = True

    def reset_modules(self) -> bool:
        """Reset interpolation filter and DAC modules.

        :return: True if successful, False if timeout
        """
        self._select_page(0)
        self._write_register_bit(_RESET, 4, True)

        # Wait for auto-clearing with timeout (max 100ms)
        timeout = time.monotonic() + 0.1
        while time.monotonic() < timeout:
            if not self._read_register_bit(_RESET, 4):
                return True
            time.sleep(0.001)

        return False

    def reset_registers(self) -> bool:
        """Reset registers back to their initial values.

        :return: True if successful, False if timeout
        """
        self._select_page(0)
        self._write_register_bit(_RESET, 0, True)

        # Wait for auto-clearing with timeout (max 100ms)
        timeout = time.monotonic() + 0.1
        while time.monotonic() < timeout:
            if not self._read_register_bit(_RESET, 0):
                return True
            time.sleep(0.001)

        return False

    @property
    def standby(self) -> bool:
        """Standby mode control."""
        self._select_page(0)
        return self._read_register_bit(_STANDBY, 4)

    @standby.setter
    def standby(self, value: bool) -> None:
        self._select_page(0)
        self._write_register_bit(_STANDBY, 4, value)

    @property
    def powerdown(self) -> bool:
        """Powerdown mode control."""
        self._select_page(0)
        return self._read_register_bit(_STANDBY, 0)

    @powerdown.setter
    def powerdown(self, value: bool) -> None:
        self._select_page(0)
        self._write_register_bit(_STANDBY, 0, value)

    @property
    def i2s_format(self) -> int:
        """I2S data format (I2S_FORMAT_*)."""
        self._select_page(0)
        return self._read_register_bits(_I2S_CONFIG, 2, 4)

    @i2s_format.setter
    def i2s_format(self, value: int) -> None:
        if value not in {I2S_FORMAT_I2S, I2S_FORMAT_TDM, I2S_FORMAT_RTJ, I2S_FORMAT_LTJ}:
            raise ValueError(f"Invalid I2S format: {value}. Must be one of I2S_FORMAT_*")
        self._select_page(0)
        self._write_register_bits(_I2S_CONFIG, 2, 4, value)

    @property
    def i2s_size(self) -> int:
        """I2S word length (I2S_SIZE_*)."""
        self._select_page(0)
        return self._read_register_bits(_I2S_CONFIG, 2, 0)

    @i2s_size.setter
    def i2s_size(self, value: int) -> None:
        if value not in {I2S_SIZE_16BIT, I2S_SIZE_20BIT, I2S_SIZE_24BIT, I2S_SIZE_32BIT}:
            raise ValueError(f"Invalid I2S size: {value}. Must be one of I2S_SIZE_*")
        self._select_page(0)
        self._write_register_bits(_I2S_CONFIG, 2, 0, value)

    @property
    def pll_reference(self) -> int:
        """PLL reference clock source (PLL_REF_*)."""
        self._select_page(0)
        return self._read_register_bits(_PLL_REF, 3, 4)

    @pll_reference.setter
    def pll_reference(self, value: int) -> None:
        if value not in {PLL_REF_SCK, PLL_REF_BCK, PLL_REF_GPIO}:
            raise ValueError(f"Invalid PLL reference: {value}. Must be one of PLL_REF_*")
        self._select_page(0)
        self._write_register_bits(_PLL_REF, 3, 4, value)

    @property
    def volume_db(self) -> tuple[float, float]:
        """Digital volume in dB for left and right channels.

        :return: Tuple of (left_db, right_db)
        """
        self._select_page(0)
        left_val = self._read_register(_DIGITAL_VOLUME_L)
        right_val = self._read_register(_DIGITAL_VOLUME_R)

        # Convert register values to dB
        left_db = 24.0 - (left_val * 0.5)
        right_db = 24.0 - (right_val * 0.5)

        return (left_db, right_db)

    @volume_db.setter
    def volume_db(self, values: tuple[float, float]) -> None:
        """Set digital volume in dB for both channels.

        :param values: Tuple of (left_db, right_db) from -103.5 to 24.0 dB
        """
        left_db, right_db = values

        # Convert dB to register values (0.5dB steps)
        left_val = int(max(0, min(255, (24.0 - left_db) / 0.5)))
        right_val = int(max(0, min(255, (24.0 - right_db) / 0.5)))

        self._select_page(0)
        self._write_register(_DIGITAL_VOLUME_L, left_val)
        self._write_register(_DIGITAL_VOLUME_R, right_val)

    @property
    def dsp_boot(self) -> bool:
        """Check if DSP boot is complete (read-only)."""
        self._select_page(0)
        return self._read_register_bit(_POWER_STATE, 7)

    @property
    def power_state(self) -> int:
        """Current power state (read-only, POWER_*)."""
        self._select_page(0)
        return self._read_register_bits(_POWER_STATE, 4, 0)

    @property
    def dac_source(self) -> int:
        """DAC clock source (DAC_CLK_*)."""
        self._select_page(0)
        return self._read_register_bits(_DAC_CLK_SRC, 3, 4)

    @dac_source.setter
    def dac_source(self, value: int) -> None:
        if value not in {DAC_CLK_MASTER, DAC_CLK_PLL, DAC_CLK_SCK, DAC_CLK_BCK}:
            raise ValueError(f"Invalid DAC clock source: {value}. Must be one of DAC_CLK_*")
        self._select_page(0)
        self._write_register_bits(_DAC_CLK_SRC, 3, 4, value)

    @property
    def auto_mute(self) -> bool:
        """Auto mute enable."""
        self._select_page(0)
        value = self._read_register_bits(_AUTO_MUTE, 3, 0)
        return value == 0x7

    @auto_mute.setter
    def auto_mute(self, enable: bool) -> None:
        self._select_page(0)
        self._write_register_bits(_AUTO_MUTE, 3, 0, 0x7 if enable else 0x0)

    @property
    def mute(self) -> bool:
        """Mute state for both channels."""
        self._select_page(0)
        left = self._read_register_bit(_MUTE, 4)
        right = self._read_register_bit(_MUTE, 0)
        return left and right

    @mute.setter
    def mute(self, value: bool) -> None:
        self._select_page(0)
        self._write_register_bit(_MUTE, 4, value)  # Left
        self._write_register_bit(_MUTE, 0, value)  # Right

    @property
    def pll_enabled(self) -> bool:
        """PLL enable."""
        self._select_page(0)
        return self._read_register_bit(_PLL, 0)

    @pll_enabled.setter
    def pll_enabled(self, value: bool) -> None:
        self._select_page(0)
        self._write_register_bit(_PLL, 0, value)

    @property
    def pll_locked(self) -> bool:
        """Check if PLL is locked (read-only)."""
        self._select_page(0)
        return not self._read_register_bit(_PLL, 4)  # 0 = locked

    @property
    def deemphasis(self) -> bool:
        """De-emphasis filter enable."""
        self._select_page(0)
        return self._read_register_bit(_DEEMPHASIS, 4)

    @deemphasis.setter
    def deemphasis(self, value: bool) -> None:
        self._select_page(0)
        self._write_register_bit(_DEEMPHASIS, 4, value)

    @property
    def vcom_enabled(self) -> bool:
        """VCOM mode enable (True for VCOM, False for VREF)."""
        self._select_page(1)
        return self._read_register_bit(_PAGE1_OUTPUT_AMP_TYPE, 0)

    @vcom_enabled.setter
    def vcom_enabled(self, value: bool) -> None:
        self._select_page(1)
        self._write_register_bit(_PAGE1_OUTPUT_AMP_TYPE, 0, value)

    @property
    def vcom_powered(self) -> bool:
        """VCOM power state."""
        self._select_page(1)
        return not self._read_register_bit(_PAGE1_VCOM_POWER, 0)  # 0 = on

    @vcom_powered.setter
    def vcom_powered(self, value: bool) -> None:
        self._select_page(1)
        self._write_register_bit(_PAGE1_VCOM_POWER, 0, not value)  # 0 = on

    @property
    def gpio5_output(self) -> int:
        """GPIO5 output function (GPIO5_*)."""
        self._select_page(0)
        return self._read_register_bits(_GPIO5_OUTPUT, 5, 0)

    @gpio5_output.setter
    def gpio5_output(self, value: int) -> None:
        # Define valid GPIO5 output values
        valid_gpio5_outputs = (
            GPIO5_OFF,
            GPIO5_DSP_OUTPUT,
            GPIO5_REGISTER_OUTPUT,
            GPIO5_AUTO_MUTE_FLAG,
            GPIO5_AUTO_MUTE_L,
            GPIO5_AUTO_MUTE_R,
            GPIO5_CLOCK_INVALID,
            GPIO5_SDOUT,
            GPIO5_ANALOG_MUTE_L,
            GPIO5_ANALOG_MUTE_R,
            GPIO5_PLL_LOCK,
            GPIO5_CHARGE_PUMP_CLK,
            GPIO5_UNDER_VOLT_07,
            GPIO5_UNDER_VOLT_03,
            GPIO5_PLL_OUT_DIV4,
        )
        if value not in valid_gpio5_outputs:
            raise ValueError(f"Invalid GPIO5 output: {value:#x}. Must be one of GPIO5_*")
        self._select_page(0)
        self._write_register_bits(_GPIO5_OUTPUT, 5, 0, value)

    # Error detection ignore properties
    @property
    def ignore_fs_detect(self) -> bool:
        """Ignore FS detection."""
        self._select_page(0)
        return self._read_register_bit(_ERROR_DETECT, 6)

    @ignore_fs_detect.setter
    def ignore_fs_detect(self, value: bool) -> None:
        self._select_page(0)
        self._write_register_bit(_ERROR_DETECT, 6, value)

    @property
    def ignore_bck_detect(self) -> bool:
        """Ignore BCK detection."""
        self._select_page(0)
        return self._read_register_bit(_ERROR_DETECT, 5)

    @ignore_bck_detect.setter
    def ignore_bck_detect(self, value: bool) -> None:
        self._select_page(0)
        self._write_register_bit(_ERROR_DETECT, 5, value)

    @property
    def ignore_sck_detect(self) -> bool:
        """Ignore SCK detection."""
        self._select_page(0)
        return self._read_register_bit(_ERROR_DETECT, 4)

    @ignore_sck_detect.setter
    def ignore_sck_detect(self, value: bool) -> None:
        self._select_page(0)
        self._write_register_bit(_ERROR_DETECT, 4, value)

    @property
    def ignore_clock_halt(self) -> bool:
        """Ignore clock halt detection."""
        self._select_page(0)
        return self._read_register_bit(_ERROR_DETECT, 3)

    @ignore_clock_halt.setter
    def ignore_clock_halt(self, value: bool) -> None:
        self._select_page(0)
        self._write_register_bit(_ERROR_DETECT, 3, value)

    @property
    def ignore_clock_missing(self) -> bool:
        """Ignore LRCK/BCK missing detection."""
        self._select_page(0)
        return self._read_register_bit(_ERROR_DETECT, 2)

    @ignore_clock_missing.setter
    def ignore_clock_missing(self, value: bool) -> None:
        self._select_page(0)
        self._write_register_bit(_ERROR_DETECT, 2, value)

    @property
    def disable_clock_autoset(self) -> bool:
        """Disable clock divider autoset mode."""
        self._select_page(0)
        return self._read_register_bit(_ERROR_DETECT, 1)

    @disable_clock_autoset.setter
    def disable_clock_autoset(self, value: bool) -> None:
        self._select_page(0)
        self._write_register_bit(_ERROR_DETECT, 1, value)

    @property
    def ignore_pll_unlock(self) -> bool:
        """Ignore PLL unlock detection."""
        self._select_page(0)
        return self._read_register_bit(_ERROR_DETECT, 0)

    @ignore_pll_unlock.setter
    def ignore_pll_unlock(self, value: bool) -> None:
        self._select_page(0)
        self._write_register_bit(_ERROR_DETECT, 0, value)

    def digital_read(self, pin: int) -> bool:
        """Read digital state of GPIO pin.

        :param pin: GPIO pin number (1-6)
        :return: True if pin is high, False if low
        :raises ValueError: If pin number is invalid
        """
        if not 1 <= pin <= 6:
            raise ValueError("Pin must be between 1 and 6")

        self._select_page(0)
        return self._read_register_bit(_GPIO_INPUT, pin - 1)

    def _set_gpio_direction(self, gpio: int, output: bool) -> None:
        """Set GPIO direction.

        :param gpio: GPIO pin number (1-6)
        :param output: True for output, False for input
        :raises ValueError: If gpio number is invalid
        """
        if not 1 <= gpio <= 6:
            raise ValueError("GPIO must be between 1 and 6")

        self._select_page(0)
        self._write_register_bit(_GPIO_ENABLE, gpio - 1, output)

    def _set_gpio_register_output(self, gpio: int, high: bool) -> None:
        """Set GPIO register output value.

        :param gpio: GPIO pin number (1-6)
        :param high: True for high, False for low
        :raises ValueError: If gpio number is invalid
        """
        if not 1 <= gpio <= 6:
            raise ValueError("GPIO must be between 1 and 6")

        self._select_page(0)
        self._write_register_bit(_GPIO_CONTROL, gpio - 1, high)

    class Pin:
        """Digitalio-style pin interface."""

        def __init__(self, pcm: "PCM51XX", pin: int) -> None:
            self._pcm = pcm
            self._pin = pin
            self._direction = None

        def switch_to_output(self, value: bool = False, drive_mode: int = None) -> None:
            """Switch the pin to output mode."""
            if self._pin == 5:
                # For GPIO5, set to register output mode
                self._pcm.gpio5_output = GPIO5_REGISTER_OUTPUT
            self._pcm._set_gpio_direction(self._pin, True)
            self._pcm._set_gpio_register_output(self._pin, value)
            self._direction = True

        def switch_to_input(self, pull: int = None) -> None:
            """Switch the pin to input mode."""
            self._pcm._set_gpio_direction(self._pin, False)
            self._direction = False

        @property
        def direction(self) -> int:
            """Get pin direction (0=INPUT, 1=OUTPUT)."""
            if self._direction is None:
                self._pcm._select_page(0)
                self._direction = self._pcm._read_register_bit(_GPIO_ENABLE, self._pin - 1)
            return 1 if self._direction else 0

        @property
        def value(self) -> bool:
            """Get or set the pin value."""
            if self.direction:  # Output mode
                self._pcm._select_page(0)
                return self._pcm._read_register_bit(_GPIO_CONTROL, self._pin - 1)
            else:  # Input mode
                return self._pcm.digital_read(self._pin)

        @value.setter
        def value(self, val: bool) -> None:
            """Set the pin value (output mode only)."""
            if not self.direction:
                raise AttributeError("Cannot set value when in input mode")
            self._pcm._set_gpio_register_output(self._pin, val)
