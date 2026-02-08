# SPDX-FileCopyrightText: 2017 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_ds2413`
====================================================

 CircuitPython driver for the DS2413 one wire 2 channel GPIO breakout.

* Author(s): Carter Nelson
"""

__version__ = "1.2.22"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_DS2413.git"

from adafruit_onewire.device import OneWireDevice
from micropython import const

try:
    import typing

    from adafruit_onewire.bus import OneWireBus
    from typing_extensions import Literal
except ImportError:
    pass

_DS2413_ACCESS_READ = b"\xf5"
_DS2413_ACCESS_WRITE = b"\x5a"
_DS2413_ACK_SUCCESS = b"\xaa"
_DS2413_ACK_ERROR = b"\xff"
INPUT = const(0)
OUTPUT = const(1)


class DS2413Pin:
    """Class which provides interface to single DS2413 GPIO pin."""

    def __init__(self, number: Literal[0, 1], host, direction: Literal[0, 1] = OUTPUT) -> None:
        if number not in {0, 1}:
            raise ValueError("Incorrect pin number.")
        self._number = number
        self._host = host
        self._mask = 1 << (number * 2)
        self._direction = None  # create it, and then...
        self.direction = direction  # set it through setter

    @property
    def direction(self) -> Literal[0, 1]:
        """The direction of the pin, either INPUT or OUTPUT."""
        return self._direction

    @direction.setter
    def direction(self, direction: Literal[0, 1]) -> None:
        if direction not in {INPUT, OUTPUT}:
            raise ValueError("Incorrect direction setting.")
        self._direction = OUTPUT
        self.value = False
        self._direction = direction

    @property
    def value(self) -> bool:
        """The pin state if configured as INPUT. The output latch state
        if configured as OUTPUT. True is HIGH/ON, False is LOW/OFF."""
        # return Pin State if configured for INPUT
        # return Latch State if configured for OUTPUT
        # NOTE: logic is re-inverted to make it more normally
        return not self._host.pio_state & (self._mask << self._direction)

    @value.setter
    def value(self, state: bool) -> None:
        # This only makes sense if the pin is configured for OUTPUT.
        if self._direction == INPUT:
            raise RuntimeError("Can't set value when pin is set to input.")
        # We jump through some hoops in order to only set/clear the bit
        # for the channel associated with this pin object.
        current = self._host.pio_state
        #       PIOB Output Latch       PIOA Output Latch
        new = (current >> 2 & 0x02) | (current >> 1 & 0x01)
        # To switch the output transistor on, the corresponding bit value is 0.
        # To switch the output transistor off (non-conducting) the bit must be 1.
        if state:
            # clear it (transistor = ON)
            new &= ~(1 << self._number)
        else:
            # set it (transistor = OFF)
            new |= 1 << self._number
        self._host.pio_state = new


class DS2413:
    """Class which provides interface to DS2413 GPIO breakout."""

    def __init__(self, bus: OneWireBus, address: int) -> None:
        if address.family_code == 0x3A:
            self._address = address
            self._device = OneWireDevice(bus, address)
            self._buf = bytearray(3)
            self._IOA = None
            self._IOB = None
        else:
            raise RuntimeError("Incorrect family code in device address.")

    @property
    def IOA(self) -> DS2413Pin:
        """The pin object for channel A."""
        if self._IOA is None:
            self._IOA = DS2413Pin(0, self)
        return self._IOA

    @property
    def IOB(self) -> DS2413Pin:
        """The pin object for channel B."""
        if self._IOB is None:
            self._IOB = DS2413Pin(1, self)
        return self._IOB

    @property
    def pio_state(self) -> int:
        """The state of both PIO channels."""
        return self._read_status()

    @pio_state.setter
    def pio_state(self, value: int) -> None:
        return self._write_latches(value)

    def _read_status(self) -> int:
        with self._device as dev:
            dev.write(_DS2413_ACCESS_READ)
            dev.readinto(self._buf, end=1)
        return self._buf[0]

    def _write_latches(self, value: int) -> None:
        # top six bits must be 1
        value |= 0xFC
        self._buf[0] = value
        self._buf[1] = ~value & 0xFF
        with self._device as dev:
            dev.write(_DS2413_ACCESS_WRITE)
            dev.write(self._buf, end=2)
            dev.readinto(self._buf, end=1)
        if not self._buf[0] == ord(_DS2413_ACK_SUCCESS):
            raise RuntimeError("ACK failure.")
