# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_gp8403`
================================================================================

CircuitPython driver for the Adafruit GP8403 Breakout Board I2C DAC with 12V Booster + NVM


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit GP8403 Breakout Board I2C DAC <https://www.adafruit.com/product/6516>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import time

import digitalio
from adafruit_bus_device import i2c_device
from adafruit_register.i2c_struct import Struct, UnaryStruct
from micropython import const

try:
    from typing import Iterable, Optional, Tuple

    from busio import I2C
    from microcontroller import Pin
    from typing_extensions import Literal
except ImportError:
    pass

__version__ = "1.0.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_GP8403.git"

GP8403_DEFAULT_ADDRESS = 0x58

# Internal constants:
_RANGE = const(0x01)
_CH0 = const(0x02)
_CH1 = const(0x04)
_RANGE_5V_DATA = const(0x00)
_RANGE_10V_DATA = const(0x11)
_MAX_RAW = const(4095)

# NVM save waveform constants:
_NVM_HALF_PERIOD = 5e-6
_NVM_WRITE_TIME = 0.008
_NVM_CMD = const(0x10)
_NVM_ENTER = const(0x03)
_NVM_EXIT = const(0x00)
_NVM_DATA_CMD = const(0xB0)
_NVM_DATA_BYTES = const(8)


class CV:
    """struct helper"""

    @classmethod
    def add_values(cls, value_tuples: Iterable[Tuple[str, int, str, Optional[float]]]) -> None:
        """creates CV entries"""
        cls.string = {}
        cls.lsb = {}

        for value_tuple in value_tuples:
            name, value, string, lsb = value_tuple
            setattr(cls, name, value)
            cls.string[value] = string
            cls.lsb[value] = lsb

    @classmethod
    def is_valid(cls, value: int) -> bool:
        """Returns true if the given value is a member of the CV"""
        return value in cls.string


class Range(CV):
    """Options for ``output_range``"""


Range.add_values(
    (
        ("RANGE_5V", 0, "0V to 5V", None),
        ("RANGE_10V", 1, "0V to 10V", None),
    )
)


class _NVMWriter:
    def __init__(self, sda: Pin, scl: Pin) -> None:
        self._sda = digitalio.DigitalInOut(sda)
        self._scl = digitalio.DigitalInOut(scl)
        self.release_bus()

    def deinit(self) -> None:
        self._sda.deinit()
        self._scl.deinit()

    def release_bus(self) -> None:
        self._release(self._sda)
        self._release(self._scl)

    def start(self) -> bool:
        self.release_bus()
        time.sleep(_NVM_HALF_PERIOD)
        if not self._sda.value or not self._scl.value:
            return False
        self._drive_low(self._sda)
        time.sleep(_NVM_HALF_PERIOD)
        self._drive_low(self._scl)
        time.sleep(_NVM_HALF_PERIOD)
        return True

    def stop(self) -> bool:
        self._drive_low(self._sda)
        time.sleep(_NVM_HALF_PERIOD)
        self._release(self._scl)
        time.sleep(_NVM_HALF_PERIOD)
        clock_high = self._scl.value
        self._release(self._sda)
        time.sleep(_NVM_HALF_PERIOD)
        return clock_high and self._sda.value

    def write_bit(self, value: bool) -> bool:
        self._drive_low(self._scl)
        if value:
            self._release(self._sda)
        else:
            self._drive_low(self._sda)
        time.sleep(_NVM_HALF_PERIOD)
        self._release(self._scl)
        time.sleep(_NVM_HALF_PERIOD)
        clock_high = self._scl.value
        data_high = not value or self._sda.value
        self._drive_low(self._scl)
        time.sleep(_NVM_HALF_PERIOD)
        return clock_high and data_high

    def write_byte(self, value: int) -> bool:
        clocks_high = True
        for bit in range(7, -1, -1):
            clocks_high = self.write_bit(bool(value & (1 << bit))) and clocks_high
        return clocks_high

    def write_acked_byte(self, value: int) -> bool:
        clocks_high = self.write_byte(value)
        self._drive_low(self._scl)
        self._release(self._sda)
        time.sleep(_NVM_HALF_PERIOD)
        self._release(self._scl)
        time.sleep(_NVM_HALF_PERIOD)
        acknowledged = self._scl.value and not self._sda.value
        self._drive_low(self._scl)
        time.sleep(_NVM_HALF_PERIOD)
        return clocks_high and acknowledged

    def write_preamble(self) -> bool:
        if not self.start():
            return False
        waveform_ok = self.write_bit(False)
        waveform_ok = self.write_bit(True) and waveform_ok
        waveform_ok = self.write_bit(False) and waveform_ok
        return self.stop() and waveform_ok

    @staticmethod
    def _drive_low(pin: digitalio.DigitalInOut) -> None:
        pin.switch_to_output(value=False)

    @staticmethod
    def _release(pin: digitalio.DigitalInOut) -> None:
        pin.switch_to_input()


class GP8403:
    """Driver for the GP8403 dual channel 12-bit voltage output DAC.

    :param ~busio.I2C i2c_bus: The I2C bus the GP8403 is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x58`
    :param int output_range: The output range to select. Must be a ``Range``.
        Defaults to :const:`Range.RANGE_5V`
    """

    _range_reg = UnaryStruct(_RANGE, "<B")
    _ch0_reg = UnaryStruct(_CH0, "<H")
    _ch1_reg = UnaryStruct(_CH1, "<H")
    _both_reg = Struct(_CH0, "<HH")

    def __init__(
        self,
        i2c_bus: I2C,
        address: int = GP8403_DEFAULT_ADDRESS,
        output_range: int = Range.RANGE_5V,
    ) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)

        self._output_range = Range.RANGE_5V
        self.channel_0 = Channel(self, 0)
        self.channel_1 = Channel(self, 1)

        self.output_range = output_range

    def _full_scale_voltage(self) -> float:
        if self._output_range == Range.RANGE_10V:
            return 10.0
        return 5.0

    def _voltage_to_raw(self, volts: float) -> int:
        full_scale = self._full_scale_voltage()
        if not 0.0 <= volts <= full_scale:
            raise ValueError(f"`voltage` must be between 0.0 and {full_scale}")
        return int(volts * _MAX_RAW / full_scale + 0.5)

    def _set_value(self, channel: "Channel", value: int) -> None:
        if channel.channel_index:
            self._ch1_reg = value << 4
        else:
            self._ch0_reg = value << 4

    @property
    def output_range(self) -> Literal[0, 1]:
        """The output voltage range. Must be a ``Range``.  Both outputs are set to zero before
        the new range takes effect.
        """
        return self._output_range

    @output_range.setter
    def output_range(self, value: Literal[0, 1]) -> None:
        if not Range.is_valid(value):
            raise ValueError("`output_range` must be a `Range`")
        self.raw_values = (0, 0)
        self._range_reg = _RANGE_10V_DATA if value == Range.RANGE_10V else _RANGE_5V_DATA
        self._output_range = value

    @property
    def raw_values(self) -> Tuple[int, int]:
        """Both channels as native 12-bit values, as ``(channel_0, channel_1)``.  Setting this
        updates both outputs in a single I2C transaction, so they change together rather than
        one after the other.
        """
        return (self.channel_0.raw_value, self.channel_1.raw_value)

    @raw_values.setter
    def raw_values(self, values: Tuple[int, int]) -> None:
        value_0, value_1 = values
        for value in values:
            if value < 0 or value > _MAX_RAW:
                raise ValueError(f"`raw_values` must be 12-bit integers between 0 and {_MAX_RAW}")
        self._both_reg = (value_0 << 4, value_1 << 4)
        # writing through each channel's public setter would issue a second,
        # single channel write and break the simultaneous update
        self.channel_0._raw_value = value_0
        self.channel_1._raw_value = value_1

    @property
    def voltages(self) -> Tuple[float, float]:
        """Both channels as quantized voltages in volts, as ``(channel_0, channel_1)``.  Setting
        this updates both outputs in a single I2C transaction, so they change together rather
        than one after the other.
        """
        return (self.channel_0.voltage, self.channel_1.voltage)

    @voltages.setter
    def voltages(self, values: Tuple[float, float]) -> None:
        volts_0, volts_1 = values
        self.raw_values = (self._voltage_to_raw(volts_0), self._voltage_to_raw(volts_1))

    def save_to_nvm(self, sda: Pin, scl: Pin) -> None:  # noqa: PLR6301
        """Store the current output voltage data in the GP8403's NVM, setting it as the default
        on power up.

        The datasheet specifies a nonstandard bus waveform rather than an ordinary register
        write, so the sequence is bit banged on the supplied pins.  Deinitialize the
        :class:`busio.I2C` bus before calling this and recreate it afterwards, since the pins
        cannot be shared.  Bus pull up resistors are required.

        Returning without an exception confirms that the waveform was emitted and the
        documented entry and exit acknowledgments were observed.  It cannot verify persistence
        without a power cycle.

        :param ~microcontroller.Pin sda: The SDA pin of the I2C bus
        :param ~microcontroller.Pin scl: The SCL pin of the I2C bus
        """
        if sda is scl:
            raise ValueError("`sda` and `scl` must be different pins")

        writer = _NVMWriter(sda, scl)
        try:
            entry_preamble_ok = writer.write_preamble()
            entry_start_ok = entry_preamble_ok and writer.start()
            entry_command_ack = False
            entry_data_ack = False
            if entry_start_ok:
                entry_command_ack = writer.write_acked_byte(_NVM_CMD)
                entry_data_ack = writer.write_acked_byte(_NVM_ENTER)
            entry_stop_ok = entry_start_ok and writer.stop()
            entered = (
                entry_preamble_ok
                and entry_start_ok
                and entry_command_ack
                and entry_data_ack
                and entry_stop_ok
            )

            data_waveform_ok = False
            if entered:
                data_waveform_ok = writer.start()
                if data_waveform_ok:
                    data_waveform_ok = writer.write_byte(_NVM_DATA_CMD) and data_waveform_ok
                    data_waveform_ok = writer.write_bit(True) and data_waveform_ok
                    for _ in range(_NVM_DATA_BYTES):
                        data_waveform_ok = writer.write_byte(0x00) and data_waveform_ok
                        data_waveform_ok = writer.write_bit(True) and data_waveform_ok
                    data_waveform_ok = writer.stop() and data_waveform_ok
                time.sleep(_NVM_WRITE_TIME)

            exit_preamble_ok = entry_start_ok and writer.write_preamble()
            exit_start_ok = False
            exit_command_ack = False
            exit_data_ack = False
            exit_stop_ok = False
            if exit_preamble_ok:
                exit_start_ok = writer.start()
                if exit_start_ok:
                    exit_command_ack = writer.write_acked_byte(_NVM_CMD)
                    exit_data_ack = writer.write_acked_byte(_NVM_EXIT)
                    exit_stop_ok = writer.stop()
            exited = (
                exit_preamble_ok
                and exit_start_ok
                and exit_command_ack
                and exit_data_ack
                and exit_stop_ok
            )
            writer.release_bus()
        finally:
            writer.deinit()

        if not (entered and data_waveform_ok and exited):
            raise RuntimeError("GP8403 did not acknowledge the NVM save sequence")


class Channel:
    """An instance of a single channel for a multi-channel DAC.

    :param dac_instance: Instance of the DAC the channel belongs to
    :param index: Index of the channel

    .. note::
        All available channels are created automatically
        and should not be created by the user

    """

    def __init__(self, dac_instance: GP8403, index: Literal[0, 1]) -> None:
        self._raw_value = 0
        self._dac = dac_instance
        self.channel_index = index

    @property
    def value(self) -> int:
        """The 16-bit scaled current value for the channel. Note that the GP8403 is a 12-bit
        piece so quantization errors will occur"""
        return self._raw_value << 4

    @value.setter
    def value(self, value: int) -> None:
        if value < 0 or value > 65535:
            raise ValueError("`value` must be a 16-bit integer between 0 and 65535")
        # Scale from 16-bit to 12-bit value (quantization errors will occur!).
        self.raw_value = value >> 4

    @property
    def raw_value(self) -> int:
        """The native 12-bit value used by the DAC.  The GP8403 cannot be read back, so this is
        the value most recently written to the channel"""
        return self._raw_value

    @raw_value.setter
    def raw_value(self, value: int) -> None:
        if value < 0 or value > _MAX_RAW:
            raise ValueError(f"`raw_value` must be a 12-bit integer between 0 and {_MAX_RAW}")
        self._dac._set_value(self, value)
        self._raw_value = value

    @property
    def voltage(self) -> float:
        """The quantized output voltage in volts, from 0.0 to the full scale voltage of the
        DAC's selected output range"""
        return self._raw_value * self._dac._full_scale_voltage() / _MAX_RAW

    @voltage.setter
    def voltage(self, value: float) -> None:
        self.raw_value = self._dac._voltage_to_raw(value)
