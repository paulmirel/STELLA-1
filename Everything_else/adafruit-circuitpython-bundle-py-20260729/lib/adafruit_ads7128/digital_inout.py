# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
:py:class:`~adafruit_ads7128.digital_inout.DigitalInOut`
==============================================================

Digital input/output of the ADS7128.

* Author(s): Liz Clark

"""

import digitalio
from micropython import const

from adafruit_ads7128.ads7128 import ADS7128

try:
    from typing import Optional

    from digitalio import Direction, DriveMode, Pull
except ImportError:
    pass

__version__ = "1.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_ADS7128.git"


_ZCD_CFG_CH0_3 = const(0xE3)
_ZCD_CFG_CH4_7 = const(0xE4)


def _get_bit(val: int, bit: int) -> bool:
    return val & (1 << bit) > 0


def _enable_bit(val: int, bit: int) -> int:
    return val | (1 << bit)


def _clear_bit(val: int, bit: int) -> int:
    return val & ~(1 << bit) & 0xFF


class DigitalInOut:
    """Digital input/output of the ADS7128. The interface is the same as the
    ``digitalio.DigitalInOut`` class, however:

      * the ADS7128 does not support pull-up or pull-down resistors;
      * a channel used here is taken out of analog mode.

    Open-drain outputs are supported through :attr:`drive_mode`. A
    :exc:`ValueError` is raised when attempting to set an unsupported pull
    configuration.

    :param ADS7128 adc: The ADS7128 driver instance.
    :param int pin: Channel number (0-7).
    """

    def __init__(self, adc: ADS7128, pin: int) -> None:
        if not isinstance(adc, ADS7128):
            raise ValueError("adc must be an ADS7128 instance")
        if pin < 0 or pin > 7:
            raise ValueError("pin must be 0-7")
        self._adc = adc
        self._pin = pin

    def switch_to_output(
        self,
        value: bool = False,
        drive_mode: "DriveMode" = digitalio.DriveMode.PUSH_PULL,
        **kwargs,
    ) -> None:
        """Switch the pin to a digital output with the given starting value and
        drive mode (push-pull by default).

        :param bool value: Initial output level. Defaults to ``False`` (low).
        :param ~digitalio.DriveMode drive_mode: Output drive mode.
        """
        self.direction = digitalio.Direction.OUTPUT
        self.drive_mode = drive_mode
        self.value = value

    def switch_to_input(self, pull: "Pull" = None, **kwargs) -> None:
        """Switch the pin to a digital input.

        :param ~digitalio.Pull pull: Must be ``None``; pull resistors are not
            supported and any other value raises :exc:`ValueError`.
        """
        self.direction = digitalio.Direction.INPUT
        self.pull = pull

    @property
    def value(self) -> bool:
        """The value of the pin, either ``True`` for high or ``False`` for low.

        Configure the pin as an output or input before writing or reading this.
        """
        if _get_bit(self._adc.gpio_cfg, self._pin):
            return _get_bit(self._adc.gpo_value, self._pin)
        return _get_bit(self._adc.gpi_value, self._pin)

    @value.setter
    def value(self, val: bool) -> None:
        if val:
            self._adc.gpo_value = _enable_bit(self._adc.gpo_value, self._pin)
        else:
            self._adc.gpo_value = _clear_bit(self._adc.gpo_value, self._pin)

    @property
    def direction(self) -> "Direction":
        """The direction of the pin, either ``digitalio.Direction.INPUT`` or
        ``digitalio.Direction.OUTPUT``.
        """
        if _get_bit(self._adc.gpio_cfg, self._pin):
            return digitalio.Direction.OUTPUT
        return digitalio.Direction.INPUT

    @direction.setter
    def direction(self, val: "Direction") -> None:
        self._adc.pin_cfg = _enable_bit(self._adc.pin_cfg, self._pin)
        if val == digitalio.Direction.INPUT:
            self._adc.gpio_cfg = _clear_bit(self._adc.gpio_cfg, self._pin)
        elif val == digitalio.Direction.OUTPUT:
            self._adc.gpio_cfg = _enable_bit(self._adc.gpio_cfg, self._pin)
        else:
            raise ValueError("Expected INPUT or OUTPUT direction!")

    @property
    def drive_mode(self) -> "DriveMode":
        """The output drive mode, either ``digitalio.DriveMode.PUSH_PULL`` or
        ``digitalio.DriveMode.OPEN_DRAIN``.
        """
        if _get_bit(self._adc.gpo_drive_cfg, self._pin):
            return digitalio.DriveMode.PUSH_PULL
        return digitalio.DriveMode.OPEN_DRAIN

    @drive_mode.setter
    def drive_mode(self, val: "DriveMode") -> None:
        if val == digitalio.DriveMode.PUSH_PULL:
            self._adc.gpo_drive_cfg = _enable_bit(self._adc.gpo_drive_cfg, self._pin)
        elif val == digitalio.DriveMode.OPEN_DRAIN:
            self._adc.gpo_drive_cfg = _clear_bit(self._adc.gpo_drive_cfg, self._pin)
        else:
            raise ValueError("Expected PUSH_PULL or OPEN_DRAIN drive mode!")

    @property
    def zcd_output(self) -> int:
        """Zero-crossing-detector output mode mapped onto this GPO pin.

        0=low, 1=high, 2=ZCD signal, 3=inverted ZCD. Use with
        :attr:`zcd_output_enabled`.
        """
        if self._pin < 4:
            reg = _ZCD_CFG_CH0_3
            shift = self._pin * 2
        else:
            reg = _ZCD_CFG_CH4_7
            shift = (self._pin - 4) * 2
        return (self._adc._read_register(reg) >> shift) & 0x03

    @zcd_output.setter
    def zcd_output(self, mode: int) -> None:
        if not 0 <= mode <= 3:
            raise ValueError("zcd_output must be 0-3")
        if self._pin < 4:
            reg = _ZCD_CFG_CH0_3
            shift = self._pin * 2
        else:
            reg = _ZCD_CFG_CH4_7
            shift = (self._pin - 4) * 2
        val = self._adc._read_register(reg)
        val = (val & ~(0x03 << shift) & 0xFF) | (mode << shift)
        self._adc._write_register(reg, val)

    @property
    def zcd_output_enabled(self) -> bool:
        """Whether the zero-crossing detector drives this GPO pin."""
        return _get_bit(self._adc.gpo_zcd_update_en, self._pin)

    @zcd_output_enabled.setter
    def zcd_output_enabled(self, value: bool) -> None:
        if value:
            self._adc.gpo_zcd_update_en = _enable_bit(self._adc.gpo_zcd_update_en, self._pin)
        else:
            self._adc.gpo_zcd_update_en = _clear_bit(self._adc.gpo_zcd_update_en, self._pin)
