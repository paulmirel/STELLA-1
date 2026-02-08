# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_pca9554`
================================================================================

CircuitPython library for Adafruit PCA9554 GPIO expanders


* Author(s): Melissa LeBlanc-Williams

Implementation Notes
--------------------

**Hardware:**

* `Adafruit Qualia ESP32-S3 <https://www.adafruit.com/product/5800>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

try:
    # This is only needed for typing
    from typing import Optional

    from busio import I2C
except ImportError:
    pass


import digitalio
from adafruit_bus_device.i2c_device import I2CDevice
from micropython import const

__version__ = "1.0.7"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_PCA9554.git"


PCA9554_I2CADDR_DEFAULT: int = const(0x3F)  # Default I2C address

# PCA9554 Command Byte
INPUTPORT: int = const(0x00)
OUTPUTPORT: int = const(0x01)
POLINVPORT: int = const(0x02)
CONFIGPORT: int = const(0x03)


class PCA9554:
    """
    Interface library for PCA9554 GPIO expanders
    :param ~busio.I2C i2c_bus: The I2C bus the PCA9554 is connected to.
    :param int address: The I2C device address. Default is :const:`0x3F`
    """

    def __init__(self, i2c_bus: I2C, address: int = PCA9554_I2CADDR_DEFAULT) -> None:
        self.i2c_device = I2CDevice(i2c_bus, address)
        self._writebuf = bytearray([0] * 2)
        self._readbuf = bytearray([0])

    def get_pin(self, pin: int) -> "DigitalInOut":
        """Convenience function to create an instance of the DigitalInOut class
        pointing at the specified pin of this PCA9554 device.
        :param int pin: pin to use for digital IO, 0 to 7
        """
        assert 0 <= pin <= 7
        return DigitalInOut(pin, self)

    def write_gpio(self, register: int, val: int) -> None:
        """Write a full 8-bit value to the GPIO register"""
        self._writebuf[0] = register & 0xFF
        self._writebuf[1] = val & 0xFF
        with self.i2c_device as i2c:
            i2c.write(self._writebuf)

    def read_gpio(self, register: int) -> int:
        """Read the full 8-bits of data from the GPIO register"""
        self._readbuf[0] = register & 0xFF
        with self.i2c_device as i2c:
            i2c.write(self._readbuf)
            i2c.readinto(self._readbuf)
        return self._readbuf[0]

    def set_pin_mode(self, pin: int, val: bool) -> None:
        """Set a single GPIO pin as input (pulled-up) or output"""
        current_value = self.read_gpio(CONFIGPORT)
        if val:
            # Set as input and turn on the pullup
            self.write_gpio(CONFIGPORT, current_value | (1 << pin))
        else:
            # Set as output and turn off the pullup
            self.write_gpio(CONFIGPORT, current_value & ~(1 << pin))

    def get_pin_mode(self, pin: int) -> bool:
        """Get a single GPIO pin's mode"""
        return bool((self.read_gpio(CONFIGPORT) >> pin) & 0x1)

    def write_pin(self, pin: int, val: bool) -> None:
        """Set a single GPIO pin high/pulled-up or driven low"""
        current_value = self.read_gpio(OUTPUTPORT)
        if val:
            # turn on the pullup (write high)
            self.write_gpio(OUTPUTPORT, current_value | (1 << pin))
        else:
            # turn on the transistor (write low)
            self.write_gpio(OUTPUTPORT, current_value & ~(1 << pin))

    def read_pin(self, pin: int) -> bool:
        """Read a single GPIO pin as high/pulled-up or driven low"""
        return bool((self.read_gpio(INPUTPORT) >> pin) & 0x1)


"""
`digital_inout`
====================================================
Digital input/output of the PCA9554.
* Author(s): Melissa LeBlanc-Williams, Tony DiCola
"""


class DigitalInOut:
    """Digital input/output of the PCA9554.  The interface is exactly the
    same as the digitalio.DigitalInOut class, however:

      - PCA9554 does not support pull-down resistors
      - PCA9554 does not actually have a sourcing transistor, instead there's
        an internal pullup

    Exceptions will be thrown when attempting to set unsupported pull
    configurations.
    """

    def __init__(self, pin_number: int, pcf: PCA9554) -> None:
        """Specify the pin number of the PCA9554 0..7, and instance."""
        self._pin = pin_number
        self._pcf = pcf

    # kwargs in switch functions below are _necessary_ for compatibility
    # with DigitalInout class (which allows specifying pull, etc. which
    # is unused by this class).
    def switch_to_output(self, value: bool = False, **kwargs) -> None:
        """Switch the pin state to a digital output with the provided starting
        value (True/False for high or low, default is False/low).
        """
        self.direction = digitalio.Direction.OUTPUT
        self.value = value

    def switch_to_input(self, pull: Optional[digitalio.Pull] = None, **kwargs) -> None:
        """Switch the pin state to a digital input which is the same as
        setting the light pullup on.  Note that true tri-state or
        pull-down resistors are NOT supported!
        """
        self.direction = digitalio.Direction.INPUT
        self.pull = pull

    @property
    def value(self) -> bool:
        """The value of the pin, either True for high or False for
        low.
        """
        return self._pcf.read_pin(self._pin)

    @value.setter
    def value(self, val: bool) -> None:
        self._pcf.write_pin(self._pin, val)

    @property
    def direction(self) -> digitalio.Direction:
        """
        Setting a pin to OUTPUT drives it low, setting it to
        an INPUT enables the light pullup.
        """
        pinmode = self._pcf.get_pin_mode(self._pin, True)
        return digitalio.Direction.INPUT if pinmode else digitalio.Direction.OUTPUT

    @direction.setter
    def direction(self, val: digitalio.Direction) -> None:
        if val == digitalio.Direction.INPUT:
            # for inputs, turn on the pullup (write high)
            self._pcf.set_pin_mode(self._pin, True)
        elif val == digitalio.Direction.OUTPUT:
            # for outputs, turn on the transistor (write low)
            self._pcf.set_pin_mode(self._pin, False)
        else:
            raise ValueError("Expected INPUT or OUTPUT direction!")

    @property
    def pull(self) -> digitalio.Pull.UP:
        """
        Pull-up is always activated so always return the same thing
        """
        return digitalio.Pull.UP

    @pull.setter
    def pull(self, val: digitalio.Pull.UP) -> None:
        if val is digitalio.Pull.UP:
            # for inputs, turn on the pullup (write high)
            self._pcf.write_pin(self._pin, True)
        else:
            raise NotImplementedError("Pull-down resistors not supported.")
