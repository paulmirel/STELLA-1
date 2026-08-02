# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_as7331`
================================================================================

CircuitPython driver for the Adafruit AS7331 UV / UVA / UVB / UVC Sensor Breakout


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit AS7331 UV / UVA / UVB / UVC Sensor Breakout <https://www.adafruit.com/product/6476>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import struct
import time

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_struct import UnaryStruct
from micropython import const

try:
    from typing import Tuple

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.2"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_AS7331.git"

_DEFAULT_ADDRESS = const(0x74)
_REG_OSR = const(0x00)
_REG_TEMP = const(0x01)
_REG_AGEN = const(0x02)
_REG_MRES1 = const(0x02)
_REG_MRES2 = const(0x03)
_REG_MRES3 = const(0x04)
_REG_CREG1 = const(0x06)
_REG_CREG2 = const(0x07)
_REG_CREG3 = const(0x08)
_REG_BREAK = const(0x09)
_REG_EDGES = const(0x0A)
_STATUS_OUTCONVOF = const(0x80)
_STATUS_MRESOF = const(0x40)
_STATUS_ADCOF = const(0x20)
_STATUS_LDATA = const(0x10)
_STATUS_NDATA = const(0x08)
_STATUS_NOTREADY = const(0x04)
_PART_ID = const(0x21)
_SENS_UVA = 385.0
_SENS_UVB = 347.0
_SENS_UVC = 794.0

# Gain settings
GAIN_2048X = const(0)
"""2048x gain (highest sensitivity)."""
GAIN_1024X = const(1)
"""1024x gain."""
GAIN_512X = const(2)
"""512x gain."""
GAIN_256X = const(3)
"""256x gain."""
GAIN_128X = const(4)
"""128x gain."""
GAIN_64X = const(5)
"""64x gain."""
GAIN_32X = const(6)
"""32x gain."""
GAIN_16X = const(7)
"""16x gain."""
GAIN_8X = const(8)
"""8x gain."""
GAIN_4X = const(9)
"""4x gain."""
GAIN_2X = const(10)
"""2x gain."""
GAIN_1X = const(11)
"""1x gain (lowest sensitivity)."""

# Integration time settings
TIME_1MS = const(0)
"""1 ms integration time."""
TIME_2MS = const(1)
"""2 ms integration time."""
TIME_4MS = const(2)
"""4 ms integration time."""
TIME_8MS = const(3)
"""8 ms integration time."""
TIME_16MS = const(4)
"""16 ms integration time."""
TIME_32MS = const(5)
"""32 ms integration time."""
TIME_64MS = const(6)
"""64 ms integration time."""
TIME_128MS = const(7)
"""128 ms integration time."""
TIME_256MS = const(8)
"""256 ms integration time."""
TIME_512MS = const(9)
"""512 ms integration time."""
TIME_1024MS = const(10)
"""1024 ms integration time."""
TIME_2048MS = const(11)
"""2048 ms integration time."""
TIME_4096MS = const(12)
"""4096 ms integration time."""
TIME_8192MS = const(13)
"""8192 ms integration time."""
TIME_16384MS = const(14)
"""16384 ms integration time."""

# Measurement modes
MODE_CONT = const(0)
"""Continuous measurement mode."""
MODE_CMD = const(1)
"""Command mode (single measurement)."""
MODE_SYNS = const(2)
"""Synchronized start mode."""
MODE_SYND = const(3)
"""Synchronized data mode."""

# Clock frequency settings
CLOCK_1024KHZ = const(0)
"""1.024 MHz clock."""
CLOCK_2048KHZ = const(1)
"""2.048 MHz clock."""
CLOCK_4096KHZ = const(2)
"""4.096 MHz clock."""
CLOCK_8192KHZ = const(3)
"""8.192 MHz clock."""


class AS7331:  # noqa: PLR0904
    """Driver for the AS7331 UV Spectral Sensor.

    :param ~busio.I2C i2c_bus: The I2C bus the sensor is connected to
    :param int address: The I2C address of the sensor. Defaults to 0x74.
    """

    _osr = UnaryStruct(_REG_OSR, "B")
    _start_stop = RWBit(_REG_OSR, 7)
    _power_down = RWBit(_REG_OSR, 6)
    _dos = RWBits(3, _REG_OSR, 0)
    _gain = RWBits(4, _REG_CREG1, 4)
    _integration_time = RWBits(4, _REG_CREG1, 0)
    _enable_divider = RWBit(_REG_CREG2, 3)
    _divider = RWBits(3, _REG_CREG2, 0)
    _measurement_mode = RWBits(2, _REG_CREG3, 6)
    _standby = RWBit(_REG_CREG3, 4)
    _ready_pin_open_drain = RWBit(_REG_CREG3, 3)
    _clock_freq = RWBits(2, _REG_CREG3, 0)
    _break_time = UnaryStruct(_REG_BREAK, "B")
    _edge_count = UnaryStruct(_REG_EDGES, "B")

    def __init__(self, i2c_bus, address=_DEFAULT_ADDRESS):
        self.i2c_device = I2CDevice(i2c_bus, address)

        self.reset()
        self.gain = GAIN_4X
        self.integration_time = TIME_64MS
        self.measurement_mode = MODE_CONT
        self.clock_frequency = CLOCK_1024KHZ
        self.break_time = 25
        self.standby = False
        self.ready_pin_open_drain = False

        if self.device_id != _PART_ID:
            raise RuntimeError("Failed to find AS7331 - check wiring!")

    def reset(self):
        """Perform a software reset, returning the sensor to configuration state."""
        self._osr = 0x0A
        time.sleep(0.01)

    @property
    def device_id(self) -> int:
        """The device part ID. Expected value is 0x21 for the AS7331."""
        buf = bytearray(1)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([_REG_AGEN]), buf)
        return buf[0]

    @property
    def measurement_mode(self) -> int:
        """The measurement mode. Must be one of ``MODE_CONT``, ``MODE_CMD``,
        ``MODE_SYNS``, or ``MODE_SYND``."""
        return self._measurement_mode

    @measurement_mode.setter
    def measurement_mode(self, mode):
        if mode not in {MODE_CONT, MODE_CMD, MODE_SYNS, MODE_SYND}:
            raise ValueError("Invalid measurement mode")
        self._measurement_mode = mode

    @property
    def gain(self) -> int:
        """The sensor gain setting. Must be one of the ``GAIN_*`` constants,
        from ``GAIN_1X`` (lowest) to ``GAIN_2048X`` (highest)."""
        return self._gain

    @gain.setter
    def gain(self, value):
        if not 0 <= value <= 11:
            raise ValueError("Gain must be 0-11")
        self._gain = value
        self._cached_gain = value

    @property
    def integration_time(self) -> int:
        """The integration time setting. Must be one of the ``TIME_*`` constants,
        from ``TIME_1MS`` to ``TIME_16384MS``."""
        return self._integration_time

    @integration_time.setter
    def integration_time(self, value):
        if not 0 <= value <= 14:
            raise ValueError("Integration time must be 0-14")
        self._integration_time = value
        self._cached_time = value

    @property
    def clock_frequency(self) -> int:
        """The internal clock frequency. Must be one of the ``CLOCK_*`` constants."""
        return self._clock_freq

    @clock_frequency.setter
    def clock_frequency(self, value):
        if not 0 <= value <= 3:
            raise ValueError("Clock frequency must be 0-3")
        self._clock_freq = value

    @property
    def power_down(self) -> bool:
        """Whether the sensor is in power-down mode."""
        return self._power_down

    @power_down.setter
    def power_down(self, value):
        if value:
            self._start_stop = False
            self._power_down = True
            self._dos = 0x02
        else:
            self._power_down = False
            self._dos = 0x03
            self._start_stop = True
            time.sleep(0.002)

    @property
    def standby(self) -> bool:
        """Whether standby mode is enabled."""
        return self._standby

    @standby.setter
    def standby(self, value):
        self._standby = value

    @property
    def ready_pin_open_drain(self) -> bool:
        """The READY pin drive mode. ``True`` for open-drain, ``False`` for push-pull."""
        return self._ready_pin_open_drain

    @ready_pin_open_drain.setter
    def ready_pin_open_drain(self, value):
        self._ready_pin_open_drain = value

    @property
    def break_time(self) -> int:
        """The break time for SYNS/SYND modes (0-255). Actual time = value * 8µs."""
        return self._break_time

    @break_time.setter
    def break_time(self, value):
        self._break_time = value

    @property
    def edge_count(self) -> int:
        """The edge count for SYND mode (0-255). 0 is treated as 1."""
        return self._edge_count

    @edge_count.setter
    def edge_count(self, value):
        self._edge_count = value

    @property
    def divider_enabled(self) -> bool:
        """Whether the result divider is enabled."""
        return self._enable_divider

    @divider_enabled.setter
    def divider_enabled(self, value):
        self._enable_divider = value

    @property
    def divider(self) -> int:
        """The divider value (0-7). Division factor = 2^(1+value)."""
        return self._divider

    @divider.setter
    def divider(self, value):
        if not 0 <= value <= 7:
            raise ValueError("Divider must be 0-7")
        self._divider = value

    def start_measurement(self):
        """Start measurements by setting the SS bit."""
        self._start_stop = True

    def stop_measurement(self):
        """Stop measurements by clearing the SS bit."""
        self._start_stop = False

    @property
    def status(self) -> int:
        """The status register byte (high byte of 16-bit OSR read)."""
        buf = bytearray(2)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([_REG_OSR]), buf)
        return buf[1]

    @property
    def data_ready(self) -> bool:
        """Whether new measurement data is ready to read."""
        buf = bytearray(2)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([_REG_OSR]), buf)
        # NREADY bit is bit 2 of the high byte (bit 10 of 16-bit value)
        return not bool(buf[1] & 0x04)

    @property
    def overflow(self) -> bool:
        """Whether any overflow condition is present."""
        s = self.status
        return bool(s & (_STATUS_OUTCONVOF | _STATUS_MRESOF | _STATUS_ADCOF))

    @property
    def new_data(self) -> bool:
        """Whether new data is available (NDATA flag)."""
        return bool(self.status & _STATUS_NDATA)

    @property
    def lost_data(self) -> bool:
        """Whether data was lost (LDATA flag)."""
        return bool(self.status & _STATUS_LDATA)

    @property
    def temperature(self) -> float:
        """The sensor temperature in degrees Celsius."""
        buf = bytearray(2)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([_REG_TEMP]), buf)
        raw = (buf[1] << 8 | buf[0]) & 0x0FFF
        return raw * 0.05 - 66.9

    def _read_all_uv(self):
        """Read all three UV channel raw ADC counts in a single I2C transaction.

        This is an internal method — it reads whatever is currently in the MRES
        registers without triggering a measurement. Use :meth:`one_shot` or
        :meth:`one_shot_irradiance` for a complete measurement cycle.

        :returns: Tuple of (uva, uvb, uvc) raw ADC counts.
        :rtype: tuple
        """
        buf = bytearray(6)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([_REG_MRES1]), buf)
        uva = buf[1] << 8 | buf[0]
        uvb = buf[3] << 8 | buf[2]
        uvc = buf[5] << 8 | buf[4]
        return (uva, uvb, uvc)

    def _counts_to_irradiance(self, counts, base_sensitivity):
        """Convert raw ADC counts to irradiance in µW/cm².

        Algorithm from AS7331 datasheet (DS001047 v4-00), Section 7.4.

        The effective sensitivity scales with gain and integration time:
          effective_sens = base_sens * (gain_factor / 2048) * time_factor

        Where:
          - base_sens: Responsivity at GAIN=2048x, TIME=64ms
          - gain_factor = 2^(11 - gain_setting)
          - time_factor = 2^time_setting / 64

        :param int counts: Raw ADC value from MRES register.
        :param float base_sensitivity: Base responsivity for the channel.
        :returns: Irradiance in µW/cm².
        :rtype: float
        """
        gain_factor = 1 << (11 - self._cached_gain)
        time_factor = (1 << self._cached_time) / 64.0

        effective_sens = base_sensitivity * (gain_factor / 2048.0) * time_factor

        if effective_sens < 0.001:
            return 0.0
        return counts / effective_sens

    def _one_shot_raw(self):
        """Internal helper that triggers a single CMD mode measurement
        and returns raw ADC counts.

        :returns: Tuple of (uva, uvb, uvc) raw ADC counts.
        :rtype: tuple
        :raises RuntimeError: If the measurement times out.
        """
        self.power_down = True
        self.measurement_mode = MODE_CMD
        self.power_down = False

        self.start_measurement()

        start = time.monotonic()
        while not self.data_ready:
            if time.monotonic() - start > 20.0:
                raise RuntimeError("Measurement timed out")
            time.sleep(0.001)

        return self._read_all_uv()

    def raw_one_shot(self) -> Tuple[float, float, float]:
        """Perform a single measurement in command mode and return raw counts.

        Configures the sensor for CMD mode, triggers a measurement,
        waits for completion, and returns raw ADC counts.

        :returns: Tuple of (uva, uvb, uvc) raw ADC counts.
        :rtype: tuple
        :raises RuntimeError: If the measurement times out.
        """
        return self._one_shot_raw()

    def one_shot(self) -> Tuple[float, float, float]:
        """Perform a single measurement in command mode and return irradiance.

        Configures the sensor for CMD mode, triggers a measurement,
        waits for completion, and converts results to µW/cm².

        :returns: Tuple of (uva, uvb, uvc) irradiance in µW/cm².
        :rtype: tuple
        :raises RuntimeError: If the measurement times out.
        """
        uva, uvb, uvc = self._one_shot_raw()
        return (
            self._counts_to_irradiance(uva, _SENS_UVA),
            self._counts_to_irradiance(uvb, _SENS_UVB),
            self._counts_to_irradiance(uvc, _SENS_UVC),
        )
