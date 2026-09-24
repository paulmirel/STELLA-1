# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_tcs3448`
================================================================================

CircuitPython driver for the Adafruit TCS3448 14-Channel Light / Color Sensor Breakout


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit TCS3448 14-Channel Light / Color Sensor Breakout <https://www.adafruit.com/product/6525>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import time

from adafruit_bus_device import i2c_device
from adafruit_register.i2c_bit import ROBit, RWBit
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_struct import Struct, UnaryStruct
from adafruit_register.i2c_struct_array import StructArray
from micropython import const

try:
    from typing import List, Tuple

    import busio
except ImportError:
    pass

__version__ = "1.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_TCS3448.git"

_I2C_ADDR = const(0x59)
_CHIP_ID = const(0x81)
_AUXID = const(0x58)
_REVID = const(0x59)
_ID = const(0x5A)
_CFG12 = const(0x66)
_GPIO = const(0x6B)
_ENABLE = const(0x80)
_ATIME = const(0x81)
_WTIME = const(0x83)
_TH_L = const(0x84)
_TH_H = const(0x86)
_STATUS2 = const(0x90)
_STATUS = const(0x93)
_ASTATUS = const(0x94)
_DATA = const(0x95)
_CFG0 = const(0xBF)
_CFG1 = const(0xC6)
_LED = const(0xCD)
_PERS = const(0xCF)
_ASTEP = const(0xD4)
_CFG20 = const(0xD6)
_AZ_CFG = const(0xDE)
_FD_STATUS = const(0xE3)
_INTENAB = const(0xF9)
_CONTROL = const(0xFA)


class CV:
    """Constant-value helper used as an enum base class.

    Subclasses define integer class attributes; :meth:`valid` and
    :meth:`get_name` provide validation and reverse-lookup.
    """

    @classmethod
    def valid(cls, value: int) -> bool:
        """Return ``True`` if *value* is a defined member of this class."""
        for name, member in cls.__dict__.items():
            if name.startswith("_") or callable(member):
                continue
            if member == value:
                return True
        return False

    @classmethod
    def get_name(cls, value: int) -> str:
        """Return the attribute name whose value equals *value*."""
        for name, member in cls.__dict__.items():
            if name.startswith("_") or callable(member):
                continue
            if member == value:
                return name
        raise KeyError(value)


class Gain(CV):
    """Analog gain settings for the ALS engines

    Higher gain increases sensitivity in low light but saturates sooner in
    bright light.  The multiplier for a gain code is ``0.5 * 2 ** code``.

    +---------------------------+----------+
    | Setting                   | Gain     |
    +===========================+==========+
    | :py:const:`Gain.X0_5`     | 0.5x     |
    +---------------------------+----------+
    | :py:const:`Gain.X1`       | 1x       |
    +---------------------------+----------+
    | :py:const:`Gain.X2`       | 2x       |
    +---------------------------+----------+
    | :py:const:`Gain.X4`       | 4x       |
    +---------------------------+----------+
    | :py:const:`Gain.X8`       | 8x       |
    +---------------------------+----------+
    | :py:const:`Gain.X16`      | 16x      |
    +---------------------------+----------+
    | :py:const:`Gain.X32`      | 32x      |
    +---------------------------+----------+
    | :py:const:`Gain.X64`      | 64x      |
    +---------------------------+----------+
    | :py:const:`Gain.X128`     | 128x     |
    +---------------------------+----------+
    | :py:const:`Gain.X256`     | 256x     |
    +---------------------------+----------+
    | :py:const:`Gain.X512`     | 512x     |
    +---------------------------+----------+
    | :py:const:`Gain.X1024`    | 1024x    |
    +---------------------------+----------+
    | :py:const:`Gain.X2048`    | 2048x    |
    +---------------------------+----------+

    Default applied by the driver.
    """

    X0_5 = 0
    X1 = 1
    X2 = 2
    X4 = 3
    X8 = 4
    X16 = 5
    X32 = 6
    X64 = 7
    X128 = 8
    X256 = 9  # driver default
    X512 = 10
    X1024 = 11
    X2048 = 12


class SmuxMode(CV):
    """Automatic SMUX channel-cycling mode (CFG20 bits 6:5).

    The auto-SMUX hardware cycles through several SMUX configurations within a
    single measurement, filling six data registers per cycle.

    +-----------------------------+--------------------------------------------+
    | Setting                     | Results produced                           |
    +=============================+============================================+
    | :py:const:`SmuxMode.CH6`    | 6 results (1 cycle)                        |
    +-----------------------------+--------------------------------------------+
    | :py:const:`SmuxMode.CH12`   | 12 results (2 cycles)                      |
    +-----------------------------+--------------------------------------------+
    | :py:const:`SmuxMode.CH18`   | 18 results (3 cycles) *                    |
    +-----------------------------+--------------------------------------------+

    Default applied by the driver.
    """

    CH6 = 0  # FZ, FY, FXL, NIR, 2x VIS
    CH12 = 2  # adds F2, F3, F4, F6, 2x VIS
    CH18 = 3  # adds F1, F7, F8, F5, 2x VIS — driver default


class Channel(CV):
    """Result index within the 18-result automatic SMUX data array.

    The index is the position in the data registers, which follows the order
    the auto-SMUX engine fills them rather than wavelength order.  The index
    order matches the Arduino driver's channel constants.

    +----------------------------------+--------+---------------+-------------+
    | Setting                          | Index  | Peak          | FWHM        |
    +==================================+========+===============+=============+
    | :py:const:`Channel.FZ`           | 0      | 450 nm        | 67 nm       |
    +----------------------------------+--------+---------------+-------------+
    | :py:const:`Channel.FY`           | 1      | 560 nm        | 123 nm      |
    +----------------------------------+--------+---------------+-------------+
    | :py:const:`Channel.FXL`          | 2      | 596 nm        | 93 nm       |
    +----------------------------------+--------+---------------+-------------+
    | :py:const:`Channel.NIR`          | 3      | 855 nm        | 61 nm       |
    +----------------------------------+--------+---------------+-------------+
    | :py:const:`Channel.VIS_TL_0`     | 4      | clear, top-left, cycle 1    |
    +----------------------------------+--------+-----------------------------+
    | :py:const:`Channel.VIS_BR_0`     | 5      | clear, both-right, cycle 1  |
    +----------------------------------+--------+---------------+-------------+
    | :py:const:`Channel.F2`           | 6      | 424 nm        | 29 nm       |
    +----------------------------------+--------+---------------+-------------+
    | :py:const:`Channel.F3`           | 7      | 473 nm        | 38 nm       |
    +----------------------------------+--------+---------------+-------------+
    | :py:const:`Channel.F4`           | 8      | 516 nm        | 48 nm       |
    +----------------------------------+--------+---------------+-------------+
    | :py:const:`Channel.F6`           | 9      | 636 nm        | 58 nm       |
    +----------------------------------+--------+---------------+-------------+
    | :py:const:`Channel.VIS_TL_1`     | 10     | clear, top-left, cycle 2    |
    +----------------------------------+--------+-----------------------------+
    | :py:const:`Channel.VIS_BR_1`     | 11     | clear, both-right, cycle 2  |
    +----------------------------------+--------+---------------+-------------+
    | :py:const:`Channel.F1`           | 12     | 407 nm        | 28 nm       |
    +----------------------------------+--------+---------------+-------------+
    | :py:const:`Channel.F7`           | 13     | 687 nm        | 63 nm       |
    +----------------------------------+--------+---------------+-------------+
    | :py:const:`Channel.F8`           | 14     | 748 nm        | 77 nm       |
    +----------------------------------+--------+---------------+-------------+
    | :py:const:`Channel.F5`           | 15     | 546 nm        | 44 nm       |
    +----------------------------------+--------+---------------+-------------+
    | :py:const:`Channel.VIS_TL_2`     | 16     | clear, top-left, cycle 3    |
    +----------------------------------+--------+-----------------------------+
    | :py:const:`Channel.VIS_BR_2`     | 17     | clear, both-right, cycle 3  |
    +----------------------------------+--------+-----------------------------+

    In :py:const:`SmuxMode.CH12` only indices 0-11 are produced, and in
    :py:const:`SmuxMode.CH6` only indices 0-5.
    """

    FZ = 0
    FY = 1
    FXL = 2
    NIR = 3
    VIS_TL_0 = 4
    VIS_BR_0 = 5
    F2 = 6
    F3 = 7
    F4 = 8
    F6 = 9
    VIS_TL_1 = 10
    VIS_BR_1 = 11
    F1 = 12
    F7 = 13
    F8 = 14
    F5 = 15
    VIS_TL_2 = 16
    VIS_BR_2 = 17


class FlickerFreq(CV):
    """Flicker detection result returned by :attr:`TCS3448.flicker_frequency`.

    +-------------------------------+----------------------------+
    | Setting                       | Meaning                    |
    +===============================+============================+
    | :py:const:`FlickerFreq.NONE`  | No flicker detected        |
    +-------------------------------+----------------------------+
    | :py:const:`FlickerFreq.HZ100` | 100 Hz mains flicker       |
    +-------------------------------+----------------------------+
    | :py:const:`FlickerFreq.HZ120` | 120 Hz mains flicker       |
    +-------------------------------+----------------------------+
    """

    NONE = 0
    HZ100 = 100
    HZ120 = 120


class Measurement:
    """One set of spectral results.

    Supports indexing and ``len()``, so a :class:`Channel` constant can be
    used directly::

        blue = sensor.measurement[Channel.FZ]

    :param tuple channels: Raw ADC counts in auto-SMUX storage order.
    :param int gain: Gain code that was applied to these counts.
    :param bool saturated: ``True`` when the frame is affected by saturation.
    """

    def __init__(self, channels: Tuple[int, ...], gain: int, saturated: bool) -> None:
        self.channels = channels
        """Raw 16-bit ADC counts indexed by :class:`Channel`."""

        self.gain = gain
        """:class:`Gain` code reported for this exact frame."""

        self.saturated = saturated
        """``True`` when analog or digital saturation affected this frame."""

    @property
    def gain_multiplier(self) -> float:
        """Gain applied to this frame as a multiplier, e.g. ``256.0``."""
        return 0.5 * (2**self.gain)

    def __getitem__(self, index: int) -> int:
        """Return the count for *index*, a :class:`Channel` constant."""
        return self.channels[index]

    def __len__(self) -> int:
        """Return the number of results in this frame."""
        return len(self.channels)

    def __repr__(self) -> str:
        """Return a readable one-line summary of the frame."""
        gain = self.gain_multiplier
        return f"<Measurement gain={gain}x saturated={self.saturated} {self.channels}>"


class _Bank1:
    def __init__(self, sensor: "TCS3448") -> None:
        self._sensor = sensor

    def __enter__(self) -> None:
        self._sensor._reg_bank = True

    def __exit__(self, *args) -> None:
        self._sensor._reg_bank = False


class TCS3448:  # noqa: PLR0904
    """CircuitPython driver for the ams OSRAM TCS3448 multi-spectral sensor.

    :param ~busio.I2C i2c_bus: The I2C bus the device is connected to.
    :param int address: I2C address.  Defaults to :const:`0x59`.
    """

    _reg_bank = RWBit(_CFG0, 4)  # 1 = bank 1, 0 = bank 0

    low_power_enabled = RWBit(_CFG0, 5)
    """``True`` when the sensor idles in low-power mode between measurements."""

    power_enabled = RWBit(_ENABLE, 0)
    """``True`` when the internal oscillator is running (PON)."""

    spectral_measurement_enabled = RWBit(_ENABLE, 1)
    """``True`` when the spectral measurement engine is running (ALS_EN)."""

    wait_enabled = RWBit(_ENABLE, 3)
    """``True`` when the :attr:`wtime` delay between measurements is applied."""

    flicker_detection_enabled = RWBit(_ENABLE, 6)
    """``True`` when flicker detection is enabled."""

    atime = UnaryStruct(_ATIME, "B")
    """Number of integration steps, 0-255."""

    wtime = UnaryStruct(_WTIME, "B")
    """Delay between consecutive measurements, 0-255."""

    spectral_threshold_low = UnaryStruct(_TH_L, "<H")
    """16-bit low threshold for the spectral interrupt."""

    spectral_threshold_high = UnaryStruct(_TH_H, "<H")
    """16-bit high threshold for the spectral interrupt."""

    data_ready = ROBit(_STATUS2, 6)
    """``True`` when a complete measurement is available (AVALID)."""

    digital_saturated = ROBit(_STATUS2, 4)
    """``True`` when an ADC counter hit its maximum during the last integration."""

    analog_saturated = ROBit(_STATUS2, 3)
    """``True`` when the analogue front end saturated during the last integration."""

    status = UnaryStruct(_STATUS, "B")
    """Raw value of the main STATUS register."""

    _astatus = UnaryStruct(_ASTATUS, "B")
    _frame_6ch = Struct(_ASTATUS, "<B6H")
    _frame_12ch = Struct(_ASTATUS, "<B12H")
    _frame_18ch = Struct(_ASTATUS, "<B18H")
    _channel_data = StructArray(_DATA, "<H", 18)

    _again = RWBits(5, _CFG1, 0)
    _auto_smux = RWBits(2, _CFG20, 5)

    led_enabled = RWBit(_LED, 7)
    """``True`` when the LED driver sinks current through the LDR pin."""

    _led_drive = RWBits(7, _LED, 0)
    _persistence = RWBits(4, _PERS, 0)
    _astep = UnaryStruct(_ASTEP, "<H")
    _az_config = UnaryStruct(_AZ_CFG, "B")

    flicker_status = UnaryStruct(_FD_STATUS, "B")
    """Raw value of the flicker detection status register.

    :attr:`flicker_frequency` decodes the detection bits.
    """

    system_interrupt_enabled = RWBit(_INTENAB, 0)
    """``True`` when flicker-status and SMUX-completion interrupts are enabled."""

    fifo_interrupt_enabled = RWBit(_INTENAB, 2)
    """``True`` when the FIFO threshold interrupt is enabled."""

    spectral_interrupt_enabled = RWBit(_INTENAB, 3)
    """``True`` when the spectral threshold interrupt is enabled."""

    _sw_reset = RWBit(_CONTROL, 3)
    _part_id = UnaryStruct(_ID, "B")
    _revid = UnaryStruct(_REVID, "B")
    _auxid = UnaryStruct(_AUXID, "B")
    _gpio_in = ROBit(_GPIO, 0)
    _gpio_out = RWBit(_GPIO, 1)
    _gpio_in_en = RWBit(_GPIO, 2)
    _gpio_inv = RWBit(_GPIO, 3)
    _th_ch = RWBits(3, _CFG12, 0)

    def __init__(self, i2c_bus: "busio.I2C", address: int = _I2C_ADDR) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
        self._bank1 = _Bank1(self)

        time.sleep(0.001)

        with self._bank1:
            chip_id = self._part_id

        if chip_id != _CHIP_ID:
            raise RuntimeError(
                f"Failed to find TCS3448 at 0x{address:02X} - check wiring! Got ID 0x{chip_id:02X}"
            )

        self.read_timeout: int = 1000
        """Milliseconds :attr:`measurement` waits for :attr:`data_ready`."""

        self.reset()

    def reset(self) -> None:
        """Force a power-on reset and re-apply the driver defaults.

        :raises RuntimeError: If the sensor does not answer after the reset.
        """
        self._sw_reset = True

        time.sleep(0.001)
        for _ in range(250):
            try:
                _ = self._reg_bank
                break
            except OSError:
                time.sleep(0.001)
        else:
            raise RuntimeError("TCS3448 did not respond after a software reset")

        self.power_enabled = True
        self.gain = Gain.X256
        self.atime = 29
        self.astep = 599

        self.smux_mode = SmuxMode.CH18

        with self._bank1:
            self._gpio_in_en = False  # output mode

        self.led_enabled = False

    @property
    def gain(self) -> int:
        """Analog gain applied to the spectral measurement.

        Must be a :class:`Gain` constant, e.g. ``Gain.X256``.  Defaults to
        :attr:`Gain.X256`.  The gain in effect for a particular frame is
        reported by :attr:`Measurement.gain`.
        """
        return self._again

    @gain.setter
    def gain(self, value: int) -> None:
        if not Gain.valid(value):
            raise ValueError("gain must be a Gain constant")
        self._again = value

    @property
    def astep(self) -> int:
        """Integration step size, 0-65534.

        Each step is ``(astep + 1) * 2.78 us``.  65535 is reserved by the
        hardware.  See :attr:`integration_time_ms` for the resulting time.
        """
        return self._astep

    @astep.setter
    def astep(self, value: int) -> None:
        if not 0 <= value <= 65534:
            raise ValueError("astep must be 0-65534 (65535 is reserved)")
        self._astep = value

    @property
    def integration_time_ms(self) -> float:
        """Integration time in milliseconds (read-only).

        ``(atime + 1) * (astep + 1) * 2.78 us``.  Change it by setting
        :attr:`atime` or :attr:`astep`.
        """
        return (self.atime + 1) * (self._astep + 1) * 0.00278

    @property
    def smux_mode(self) -> int:
        """Automatic SMUX cycling mode.

        Must be a :class:`SmuxMode` constant.  Defaults to
        :attr:`SmuxMode.CH18`.  Only change this while no measurement is
        running.
        """
        return self._auto_smux

    @smux_mode.setter
    def smux_mode(self, value: int) -> None:
        if not SmuxMode.valid(value):
            raise ValueError("smux_mode must be a SmuxMode constant")
        self._auto_smux = value

    @property
    def channel_count(self) -> int:
        """Number of results the current :attr:`smux_mode` produces (read-only)."""
        mode = self._auto_smux
        if mode == SmuxMode.CH18:
            return 18
        if mode == SmuxMode.CH12:
            return 12
        return 6

    @property
    def measurement(self) -> Measurement:
        """Run one measurement and return it as a :class:`Measurement`.

        Stops any measurement in progress, clears stale status, triggers a
        single measurement and waits for :attr:`data_ready` before reading.
        The number of results follows :attr:`channel_count`.

        :raises TimeoutError: If no result arrives within :attr:`read_timeout`
            milliseconds.
        """
        self.spectral_measurement_enabled = False
        self.clear_status()
        _ = self._astatus

        self.spectral_measurement_enabled = True

        deadline = time.monotonic() + self.read_timeout / 1000
        while not self.data_ready:
            if time.monotonic() > deadline:
                self.spectral_measurement_enabled = False
                raise TimeoutError("Timed out waiting for TCS3448 data ready")
            time.sleep(0.001)

        frame = self.last_measurement

        self.spectral_measurement_enabled = False
        return frame

    @property
    def last_measurement(self) -> Measurement:
        """The frame currently held in the data registers, read without waiting."""
        count = self.channel_count
        if count == 18:
            frame = self._frame_18ch
        elif count == 12:
            frame = self._frame_12ch
        else:
            frame = self._frame_6ch

        astatus = frame[0]
        return Measurement(frame[1:], astatus & 0x0F, bool(astatus & 0x80))

    @property
    def all_channels(self) -> List[int]:
        """Run one measurement and return just the raw counts.

        :raises TimeoutError: If no result arrives within :attr:`read_timeout`
            milliseconds.
        """
        return list(self.measurement.channels)

    def channel(self, channel: int) -> int:
        """A single result from the data registers without waiting.

        :param int channel: Result index, a :class:`Channel` constant (0-17).
        :returns: Raw 16-bit ADC count.
        """
        if not 0 <= channel <= 17:
            raise ValueError("channel must be 0-17 (use Channel constants)")

        _ = self._astatus  # latch the data registers
        return self._channel_data[channel][0]

    @property
    def led_current_ma(self) -> int:
        """LED drive current in milliamps, 4-258.

        The hardware steps in 2 mA increments as ``4 + register * 2``, so odd
        values round down.  Enable the driver with :attr:`led_enabled`.
        """
        return 4 + (self._led_drive * 2)

    @led_current_ma.setter
    def led_current_ma(self, current_ma: int) -> None:
        current_ma = max(4, min(258, current_ma))
        self._led_drive = (current_ma - 4) // 2

    @property
    def flicker_frequency(self) -> int:
        """Detected flicker frequency as a :class:`FlickerFreq` value.

        Returns :attr:`FlickerFreq.HZ100`, :attr:`FlickerFreq.HZ120` or
        :attr:`FlickerFreq.NONE`, reporting a frequency only when the
        matching valid bit is also set.  Requires
        :attr:`flicker_detection_enabled`.
        """
        status = self.flicker_status
        if (status & 0x08) and (status & 0x02):
            return FlickerFreq.HZ120
        if (status & 0x04) and (status & 0x01):
            return FlickerFreq.HZ100
        return FlickerFreq.NONE

    def clear_status(self) -> None:
        """Clear all flags in the main STATUS register."""
        self.status = self.status

    @property
    def persistence(self) -> int:
        """Consecutive out-of-threshold measurements needed to raise an interrupt.

        Valid range 0-15.  0 raises an interrupt on every cycle.
        """
        return self._persistence

    @persistence.setter
    def persistence(self, value: int) -> None:
        if not 0 <= value <= 15:
            raise ValueError("persistence must be 0-15")
        self._persistence = value

    @property
    def auto_zero_frequency(self) -> int:
        """Measurement cycles between automatic zero-offset calibrations, 0-255.

        * ``0`` — never, which is not recommended
        * ``1`` — every cycle
        * ``255`` — only before the first measurement, the hardware default
        """
        return self._az_config

    @auto_zero_frequency.setter
    def auto_zero_frequency(self, value: int) -> None:
        if not 0 <= value <= 255:
            raise ValueError("auto_zero_frequency must be 0-255")
        self._az_config = value

    @property
    def threshold_channel(self) -> int:
        """ADC channel 0-5 compared against the spectral interrupt thresholds."""
        with self._bank1:
            return self._th_ch

    @threshold_channel.setter
    def threshold_channel(self, channel: int) -> None:
        if not 0 <= channel <= 5:
            raise ValueError("threshold_channel must be 0-5")
        with self._bank1:
            self._th_ch = channel

    @property
    def gpio_output_mode(self) -> bool:
        """``True`` when the GPIO pin is an output, ``False`` when an input."""
        with self._bank1:
            return not self._gpio_in_en

    @gpio_output_mode.setter
    def gpio_output_mode(self, output: bool) -> None:
        with self._bank1:
            self._gpio_in_en = not output

    @property
    def gpio_value(self) -> bool:
        """State of the GPIO pin."""
        with self._bank1:
            return self._gpio_in

    @gpio_value.setter
    def gpio_value(self, high: bool) -> None:
        with self._bank1:
            self._gpio_out = high

    @property
    def gpio_inverted(self) -> bool:
        """``True`` when the GPIO output polarity is inverted."""
        with self._bank1:
            return self._gpio_inv

    @gpio_inverted.setter
    def gpio_inverted(self, invert: bool) -> None:
        with self._bank1:
            self._gpio_inv = invert

    @property
    def part_id(self) -> int:
        """Part ID register value, ``0x81`` on the TCS3448."""
        with self._bank1:
            return self._part_id

    @property
    def revision_id(self) -> int:
        """Silicon revision."""
        with self._bank1:
            return self._revid & 0x07

    @property
    def aux_id(self) -> int:
        """Auxiliary ID."""
        with self._bank1:
            return self._auxid & 0x0F
