# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
:py:class:`~adafruit_tmf8806.tmf8806`
================================================================================

CircuitPython driver for the Adafruit TMF8806 Time of Flight Distance Sensor - 10mm to 5m


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit TMF8806 Time of Flight Distance Sensor <https://www.adafruit.com/product/6523>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import gc
import struct
import sys
import time
from collections import namedtuple

from adafruit_bus_device import i2c_device
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import ROBits
from adafruit_register.i2c_struct import ROUnaryStruct, Struct, UnaryStruct
from micropython import const

try:
    from typing import List, Optional, Tuple

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_TMF8806.git"

_FW_ATTR = "tmf8806_firmware"
_FW_PACKAGE = __name__.rpartition(".")[0]
_FW_MODULE = f"{_FW_PACKAGE}.{_FW_ATTR}"

_DEFAULT_ADDR = const(0x41)

_APPID = const(0x00)
_REV_MAJOR = const(0x01)
_APPREQID = const(0x02)
_CMD_DATA9 = const(0x06)
_BL_CMD = const(0x08)
_HIST_CFG_DATA = const(0x0C)
_COMMAND = const(0x10)
_PREVIOUS = const(0x11)
_REV_MINOR = const(0x12)
_STATE = const(0x1C)
_STATUS = const(0x1D)
_CONTENTS = const(0x1E)
_CONFIG = const(0x20)
_RESULT_NUM = const(0x20)
_ENABLE = const(0xE0)
_INT_STATUS = const(0xE1)
_INT_ENABLE = const(0xE2)
_ID = const(0xE3)
_REVID = const(0xE4)
_RESET_REASON = const(0xF0)

_APP_BL = const(0x80)
_APP_MEAS = const(0xC0)
_CHIP_ID = const(0x09)

_PWR_ON = const(0x01)
_CPU_READY = const(0x40)
_CPU_RESET = const(0x80)
_SOFT_RESET_BIT = const(7)

_BL_INIT = const(0x14)
_BL_WRITE = const(0x41)
_BL_ADDR = const(0x43)
_BL_REMAP = const(0x11)
_BL_BUSY = const(0x10)
_BL_READY = const(0x00)
_BL_CHUNK = const(16)
_BL_SALT = const(0x29)
_BL_CKSUM_OK = const(0xFF)

_CMD_MEAS = const(0x02)
_CMD_CALIB = const(0x0A)
_CMD_HIST_CFG = const(0x30)
_CMD_HIST_CONTINUE = const(0x32)
_CMD_SERIAL = const(0x47)
_CMD_HIST_READ = const(0x80)
_CMD_STOP = const(0xFF)
_CMD_IDLE = const(0x00)

_CONTENT_CALIB = const(0x0A)
_CONTENT_SERIAL = const(0x47)
_CONTENT_RESULT = const(0x55)
_STATE_ERROR = const(0x02)

_INT_RESULT = const(0x01)
_INT_DIAGNOSTIC = const(0x02)

_DATA_CALIB = const(0x01)
_DATA_ALGO = const(0x02)
_DEADTIME_SHIFT = const(3)
_DEADTIME_MASK = const(0x07)
_SPAD_CONFIG_SHIFT = const(6)
_SPAD_CONFIG_MASK = const(0x03)

_ALGO_DISTANCE_ENABLED = const(0x02)
_ALGO_VCSEL_CLOCK_DIV2 = const(0x04)
_ALGO_LONG_RANGE = const(0x08)
_ALGO_10M_MODE = const(0x40)

_GPIO_MASK = const(0x0F)
_GPIO1_SHIFT = const(4)
_RELIABILITY_MASK = const(0x3F)
_MEAS_STATUS_SHIFT = const(6)
_THRESHOLD_MASK = const(0x3F)

_CALIB_SIZE = const(14)
_ALGO_SIZE = const(11)
_RESULT_HDR = const(4)
_CONTENTS_OFFSET = const(2)
_FRAME_SIZE = const(34)
_CMD_BLOCK_SIZE = const(11)
_SERIAL_OFFSET = const(8)
_CALIB_ITERATIONS = const(4000)

_HIST_BINS = const(128)
_HIST_CHUNK_BINS = const(64)
_HIST_CHUNK_BYTES = const(128)
_HIST_BLOCK = const(32)
_HIST_MAX_SCALE = const(8)
_HIST_CHUNK_FMT = "<64H"

MODE_SHORT_RANGE = 0
"""Proximity only, up to about 200 mm, with distance ranging switched off."""
MODE_2_5M = 1
"""Distance ranging up to about 2.5 m. The default."""
MODE_5M = 2
"""Distance ranging up to about 5 m."""
MODE_10M = 3
"""Distance ranging up to about 10 m. Requires :meth:`load_firmware_patch`."""

_DISTANCE_MODES = (MODE_SHORT_RANGE, MODE_2_5M, MODE_5M, MODE_10M)
_MAX_DISTANCE = (200, 2650, 5300, 10000)

SPAD_DEFAULT = 0
"""Optical stack with a 0.5 mm airgap and 0.55 mm cover glass."""
SPAD_LARGE_AIRGAP = 1
"""Optical stack with a 1 mm airgap. Minimum measurable distance is 20 mm."""
SPAD_THICK_GLASS = 2
"""Optical stack with 3.2 mm cover glass. Minimum measurable distance is 40 mm."""

_SPAD_CONFIGS = (SPAD_DEFAULT, SPAD_LARGE_AIRGAP, SPAD_THICK_GLASS)

DEADTIME_97NS = 0
"""97 ns SPAD dead time. Best short-range performance. The default."""
DEADTIME_48NS = 1
"""48 ns SPAD dead time."""
DEADTIME_32NS = 2
"""32 ns SPAD dead time."""
DEADTIME_24NS = 3
"""24 ns SPAD dead time."""
DEADTIME_16NS = 4
"""16 ns SPAD dead time. A balanced choice."""
DEADTIME_12NS = 5
"""12 ns SPAD dead time."""
DEADTIME_8NS = 6
"""8 ns SPAD dead time."""
DEADTIME_4NS = 7
"""4 ns SPAD dead time. Best ambient sunlight rejection."""

_DEADTIMES = (
    DEADTIME_97NS,
    DEADTIME_48NS,
    DEADTIME_32NS,
    DEADTIME_24NS,
    DEADTIME_16NS,
    DEADTIME_12NS,
    DEADTIME_8NS,
    DEADTIME_4NS,
)

GPIO_DISABLED = 0
"""GPIO is unused during capture."""
GPIO_INPUT_ACTIVE_LOW = 1
"""A low level on the GPIO pauses capture."""
GPIO_INPUT_ACTIVE_HIGH = 2
"""A high level on the GPIO pauses capture."""
GPIO_OUTPUT_VCSEL = 3
"""The GPIO follows VCSEL timing."""
GPIO_OUTPUT_LOW = 4
"""The GPIO is driven low."""
GPIO_OUTPUT_HIGH = 5
"""The GPIO is driven high."""
GPIO_OUTPUT_DETECT_HIGH = 6
"""The GPIO is driven high while an object is detected."""
GPIO_OUTPUT_DETECT_LOW = 7
"""The GPIO is driven low while an object is detected."""
GPIO_OPEN_DRAIN_NO_DETECT_LOW = 8
"""The GPIO pulls low while no object is detected, otherwise floats."""
GPIO_OPEN_DRAIN_DETECT_LOW = 9
"""The GPIO pulls low while an object is detected, otherwise floats."""

_GPIO_MODES = (
    GPIO_DISABLED,
    GPIO_INPUT_ACTIVE_LOW,
    GPIO_INPUT_ACTIVE_HIGH,
    GPIO_OUTPUT_VCSEL,
    GPIO_OUTPUT_LOW,
    GPIO_OUTPUT_HIGH,
    GPIO_OUTPUT_DETECT_HIGH,
    GPIO_OUTPUT_DETECT_LOW,
    GPIO_OPEN_DRAIN_NO_DETECT_LOW,
    GPIO_OPEN_DRAIN_DETECT_LOW,
)

HISTOGRAM_ELECTRICAL_CAL = 1
"""Electrical calibration histogram."""
HISTOGRAM_PROXIMITY = 4
"""Proximity histogram."""
HISTOGRAM_DISTANCE = 7
"""Distance histogram."""
HISTOGRAM_PILEUP = 16
"""Pile-up corrected histogram."""
HISTOGRAM_PILEUP_TDC_SUM = 17
"""Pile-up corrected TDC sum histogram."""

_HISTOGRAM_TYPES = (
    HISTOGRAM_ELECTRICAL_CAL,
    HISTOGRAM_PROXIMITY,
    HISTOGRAM_DISTANCE,
    HISTOGRAM_PILEUP,
    HISTOGRAM_PILEUP_TDC_SUM,
)

MEASUREMENT_NOT_INTERRUPTED = 0
"""The measurement completed normally."""
MEASUREMENT_INTERRUPTED_BY_GPIO = 2
"""The measurement was delayed by a GPIO input."""

RELIABILITY_LEVELS = 64
"""Number of distinct reliability values, from 0 (invalid) to 63 (best)."""

Result = namedtuple(
    "Result",
    (
        "number",
        "distance",
        "reliability",
        "status",
        "system_clock",
        "reference_hits",
        "object_hits",
        "temperature",
        "crosstalk",
    ),
)
"""One complete TMF8806 measurement.

``number`` is a rolling result counter, ``distance`` is in millimeters,
``reliability`` runs from 0 (invalid) to 63 (best), ``status`` is one of the
``MEASUREMENT_*`` constants, ``system_clock`` is the sensor clock captured with
the result, ``reference_hits`` and ``object_hits`` are raw SPAD hit counts,
``temperature`` is the die temperature in degrees Celsius, and ``crosstalk`` is
the measured optical crosstalk.

The first seven fields match the TMF8801 driver's ``Result``, so code that
unpacks or indexes those positions works against either sensor.
"""


class TMF8806:  # noqa: PLR0904
    """Driver for the ams OSRAM TMF8806 Time-of-Flight distance sensor.

    :param ~busio.I2C i2c: The I2C bus the TMF8806 is connected to.
    :param int address: The sensor's I2C address. Defaults to :const:`0x41`.
    """

    chip_id = ROBits(6, _ID, 0)
    """Chip ID, reads as ``0x09`` on the TMF8806."""

    revision_id = ROBits(3, _REVID, 0)
    """Hardware revision ID"""

    status = ROUnaryStruct(_STATUS, "<B")
    """The measurement application's status register."""

    _app_id = ROUnaryStruct(_APPID, "<B")
    _app_request = UnaryStruct(_APPREQID, "<B")
    _enable = UnaryStruct(_ENABLE, "<B")
    _cpu_powered = RWBit(_ENABLE, 0)
    _soft_reset = RWBit(_RESET_REASON, _SOFT_RESET_BIT)
    _app_state = ROUnaryStruct(_STATE, "<B")
    _contents = ROUnaryStruct(_CONTENTS, "<B")
    _int_status = UnaryStruct(_INT_STATUS, "<B")
    _int_enable = UnaryStruct(_INT_ENABLE, "<B")
    _command = UnaryStruct(_COMMAND, "<B")
    _previous_command = ROUnaryStruct(_PREVIOUS, "<B")
    _rev_major = ROUnaryStruct(_REV_MAJOR, "<B")
    _rev_minor_patch = Struct(_REV_MINOR, "<BB")

    def __init__(self, i2c: I2C, address: int = _DEFAULT_ADDR) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c, address)
        self._reg_buf = bytearray(1)
        self._poll_buf = bytearray(1)
        self._command_buf = bytearray(2)
        self._packet = bytearray(_BL_CHUNK + 4)
        self._frame = bytearray(_FRAME_SIZE)
        self._histogram_raw = None

        if self.chip_id != _CHIP_ID:
            raise RuntimeError("Failed to find TMF8806 - check your wiring!")

        self._distance_mode = MODE_2_5M
        self._kilo_iterations = 400
        self._repetition_period = 33
        self._noise_threshold = 6
        self._spad_deadtime = DEADTIME_97NS
        self._spad_config = SPAD_DEFAULT
        self._gpio_modes = [GPIO_DISABLED, GPIO_DISABLED]
        self._calibration_data = None
        self._algorithm_state = None
        self._calibration_enabled = False
        self._algorithm_state_enabled = False
        self._histogram_type = None
        self._firmware_patch_loaded = False
        self._last_temperature = None

        self._start_app()

    def reset(self) -> None:
        """Soft reset the sensor and restart its measurement application.

        :raises RuntimeError: if the sensor does not restart into the
            measurement application.
        """
        self._soft_reset = True
        time.sleep(0.005)
        self._firmware_patch_loaded = False
        self._start_app()

    def load_firmware_patch(self) -> None:
        """Upload the RAM firmware patch that :const:`MODE_10M` requires.

        :raises RuntimeError: if there is not enough free RAM for the firmware
            image, or if the sensor does not restart into the patched
            measurement application.
        """
        self._firmware_patch_loaded = False
        self._enable = _CPU_RESET | _PWR_ON
        time.sleep(0.002)
        self._enable = _PWR_ON
        self._wait_for_cpu(0.1)
        self._wait(_APPID, _APP_BL, 0.1, "the bootloader")
        self._upload_firmware()
        self._start_app()
        self._firmware_patch_loaded = True

    @property
    def firmware_patch_loaded(self) -> bool:
        """Whether the RAM firmware patch is currently running.

        :const:`MODE_10M` cannot be used unless this is ``True``.
        """
        return self._firmware_patch_loaded

    def start_measuring(self, continuous: bool = True) -> None:
        """Start distance measurements using the current configuration.

        :param bool continuous: Measure repeatedly at :attr:`repetition_period`
            when ``True``, or take a single measurement when ``False``.
        :raises RuntimeError: if :attr:`distance_mode` is :const:`MODE_10M`
            without the firmware patch loaded, or if the sensor does not accept
            the command.
        """
        if self._distance_mode == MODE_10M and not self._firmware_patch_loaded:
            raise RuntimeError("MODE_10M needs load_firmware_patch() first")

        use_calibration = self._calibration_enabled and self._calibration_data is not None
        use_state = (
            use_calibration and self._algorithm_state_enabled and self._algorithm_state is not None
        )
        if use_calibration:
            payload = self._calibration_data
            if use_state:
                payload += self._algorithm_state
            self._write_reg(_CONFIG, payload)

        command = bytearray(_CMD_BLOCK_SIZE)
        command[2] = (
            (_DATA_CALIB if use_calibration else 0)
            | (_DATA_ALGO if use_state else 0)
            | ((self._spad_deadtime & _DEADTIME_MASK) << _DEADTIME_SHIFT)
            | ((self._spad_config & _SPAD_CONFIG_MASK) << _SPAD_CONFIG_SHIFT)
        )
        command[3] = self._algorithm_config()
        command[4] = (self._gpio_modes[0] & _GPIO_MASK) | (
            (self._gpio_modes[1] & _GPIO_MASK) << _GPIO1_SHIFT
        )
        command[6] = self._noise_threshold & _THRESHOLD_MASK
        command[7] = self._repetition_period if continuous else 0
        command[8] = self._kilo_iterations & 0xFF
        command[9] = self._kilo_iterations >> 8
        command[10] = _CMD_MEAS

        self._write_reg(_CMD_DATA9, command)
        self._wait_for_command(_CMD_MEAS, 0.05)

    def stop_measuring(self) -> None:
        """Stop measurements and wait for the sensor to accept the command.

        :raises RuntimeError: if the sensor does not accept the stop command.
        """
        self._command = _CMD_STOP
        # A measurement in flight has to finish first, so the wait scales with
        # the integration time.
        self._wait_for_command(_CMD_STOP, 0.05 + self._kilo_iterations / 18000)

    def factory_calibrate(self, timeout: float = 30.0) -> bytes:
        """Run factory calibration and store the resulting data.

        :param float timeout: Seconds to wait for calibration to finish.
        :return: The 14 bytes of factory calibration data.
        :raises RuntimeError: if calibration does not complete in time or the
            sensor publishes something other than calibration data.
        """
        command = bytearray(_CMD_BLOCK_SIZE)
        command[2] = ((self._spad_deadtime & _DEADTIME_MASK) << _DEADTIME_SHIFT) | (
            (self._spad_config & _SPAD_CONFIG_MASK) << _SPAD_CONFIG_SHIFT
        )
        command[3] = _ALGO_DISTANCE_ENABLED
        command[6] = self._noise_threshold & _THRESHOLD_MASK
        command[8] = _CALIB_ITERATIONS & 0xFF
        command[9] = _CALIB_ITERATIONS >> 8
        command[10] = _CMD_CALIB

        self._write_reg(_CMD_DATA9, command)
        self._wait_for_command(_CMD_CALIB, 0.05)
        self._wait(_INT_STATUS, _INT_RESULT, timeout, "calibration to finish", mask=_INT_RESULT)

        if self._contents != _CONTENT_CALIB:
            raise RuntimeError("TMF8806 published a result instead of calibration data")

        self._calibration_data = bytes(self._read_reg(_CONFIG, _CALIB_SIZE))
        self._calibration_enabled = True
        self._int_status = _INT_RESULT
        return self._calibration_data

    @property
    def data_ready(self) -> bool:
        """Whether a new measurement result is waiting to be read."""
        return bool(self._int_status & _INT_RESULT)

    @property
    def result(self) -> Optional[Result]:
        """The latest complete measurement as a :data:`Result`."""
        if not self.data_ready:
            return None

        frame = self._frame
        self._reg_buf[0] = _STATE
        with self.i2c_device as i2c:
            i2c.write_then_readinto(self._reg_buf, frame)

        if frame[_CONTENTS_OFFSET] != _CONTENT_RESULT:
            return None

        number, quality, distance, clock = struct.unpack_from("<BBHI", frame, _RESULT_HDR)
        state_start = _RESULT_HDR + 8
        self._algorithm_state = bytes(frame[state_start : state_start + _ALGO_SIZE])
        temperature, reference_hits, object_hits, crosstalk = struct.unpack_from(
            "<bIIH", frame, state_start + _ALGO_SIZE
        )
        self._last_temperature = temperature
        self._int_status = _INT_RESULT

        reliability = quality & _RELIABILITY_MASK
        if distance > _MAX_DISTANCE[self._distance_mode]:
            distance = 0
            reliability = 0

        return Result(
            number,
            distance,
            reliability,
            quality >> _MEAS_STATUS_SHIFT,
            clock,
            reference_hits,
            object_hits,
            temperature,
            crosstalk,
        )

    @property
    def distance(self) -> Optional[int]:
        """The measured distance in millimeters."""
        result = self.result
        if result is None or result.reliability == 0:
            return None
        return result.distance

    @property
    def temperature(self) -> Optional[int]:
        """The die temperature in degrees Celsius from the last result read."""
        return self._last_temperature

    @property
    def distance_mode(self) -> int:
        """The ranging mode used when measuring starts.

        One of :const:`MODE_SHORT_RANGE`, :const:`MODE_2_5M` (the default),
        :const:`MODE_5M` or :const:`MODE_10M`. :const:`MODE_10M` also needs
        :meth:`load_firmware_patch`. Takes effect on the next
        :meth:`start_measuring` call.
        """
        return self._distance_mode

    @distance_mode.setter
    def distance_mode(self, mode: int) -> None:
        if mode not in _DISTANCE_MODES:
            raise ValueError(f"distance_mode must be one of {_DISTANCE_MODES}")
        self._distance_mode = mode

    @property
    def max_distance(self) -> int:
        """The largest distance in millimeters the current mode can report."""
        return _MAX_DISTANCE[self._distance_mode]

    @property
    def kilo_iterations(self) -> int:
        """Integration iterations per measurement, in thousands."""
        return self._kilo_iterations

    @kilo_iterations.setter
    def kilo_iterations(self, value: int) -> None:
        if not 10 <= value <= 4000:
            raise ValueError("kilo_iterations must be from 10 to 4000")
        self._kilo_iterations = value

    @property
    def repetition_period(self) -> int:
        """Requested interval between continuous results, in milliseconds.

        Defaults to 33 ms. Only used when measuring continuously.
        """
        return self._repetition_period

    @repetition_period.setter
    def repetition_period(self, value: int) -> None:
        if not 1 <= value <= 0xFF:
            raise ValueError("repetition_period must be from 1 to 255 ms")
        self._repetition_period = value

    @property
    def noise_threshold(self) -> int:
        """Object detection threshold, from 0 to 63. Zero uses the default."""
        return self._noise_threshold

    @noise_threshold.setter
    def noise_threshold(self, value: int) -> None:
        if not 0 <= value <= _THRESHOLD_MASK:
            raise ValueError(f"noise_threshold must be from 0 to {_THRESHOLD_MASK}")
        self._noise_threshold = value

    @property
    def spad_deadtime(self) -> int:
        """SPAD dead time, one of the ``DEADTIME_*`` constants.

        Longer dead times favor short-range accuracy; shorter ones reject
        ambient sunlight better. Defaults to :const:`DEADTIME_97NS`. Takes
        effect on the next :meth:`start_measuring` call.
        """
        return self._spad_deadtime

    @spad_deadtime.setter
    def spad_deadtime(self, value: int) -> None:
        if value not in _DEADTIMES:
            raise ValueError(f"spad_deadtime must be one of {_DEADTIMES}")
        self._spad_deadtime = value

    @property
    def optical_config(self) -> int:
        """The optical stack in front of the sensor.

        One of :const:`SPAD_DEFAULT`, :const:`SPAD_LARGE_AIRGAP` or
        :const:`SPAD_THICK_GLASS`. Takes effect on the next
        :meth:`start_measuring` call.
        """
        return self._spad_config

    @optical_config.setter
    def optical_config(self, value: int) -> None:
        if value not in _SPAD_CONFIGS:
            raise ValueError(f"optical_config must be one of {_SPAD_CONFIGS}")
        self._spad_config = value

    @property
    def gpio0_mode(self) -> int:
        """The function assigned to GPIO0 during capture.

        One of the ``GPIO_*`` constants. Takes effect on the next
        :meth:`start_measuring` call.
        """
        return self._gpio_modes[0]

    @gpio0_mode.setter
    def gpio0_mode(self, mode: int) -> None:
        self._gpio_modes[0] = self._checked_gpio_mode(mode)

    @property
    def gpio1_mode(self) -> int:
        """The function assigned to GPIO1 during capture.

        Takes the same values as :attr:`gpio0_mode`.
        """
        return self._gpio_modes[1]

    @gpio1_mode.setter
    def gpio1_mode(self, mode: int) -> None:
        self._gpio_modes[1] = self._checked_gpio_mode(mode)

    @property
    def calibration_data(self) -> Optional[bytes]:
        """The 14 bytes of stored factory calibration data.

        ``None`` until :meth:`factory_calibrate` runs or data is assigned.
        Saving these bytes and restoring them on the next run avoids
        recalibrating, since calibration does not survive a power cycle.
        """
        return self._calibration_data

    @calibration_data.setter
    def calibration_data(self, data: bytes) -> None:
        if len(data) != _CALIB_SIZE:
            raise ValueError(f"calibration_data must be exactly {_CALIB_SIZE} bytes")
        self._calibration_data = bytes(data)

    @property
    def calibration_enabled(self) -> bool:
        """Whether :attr:`calibration_data` is sent when measuring starts."""
        return self._calibration_enabled

    @calibration_enabled.setter
    def calibration_enabled(self, value: bool) -> None:
        self._calibration_enabled = bool(value)

    @property
    def algorithm_state(self) -> Optional[bytes]:
        """The 11 bytes of algorithm state from the most recent result."""
        return self._algorithm_state

    @algorithm_state.setter
    def algorithm_state(self, data: bytes) -> None:
        if len(data) != _ALGO_SIZE:
            raise ValueError(f"algorithm_state must be exactly {_ALGO_SIZE} bytes")
        self._algorithm_state = bytes(data)

    @property
    def algorithm_state_enabled(self) -> bool:
        """Whether :attr:`algorithm_state` is sent when measuring starts.

        The sensor only accepts algorithm state alongside calibration data, so
        this has no effect unless :attr:`calibration_enabled` is also set.
        """
        return self._algorithm_state_enabled

    @algorithm_state_enabled.setter
    def algorithm_state_enabled(self, value: bool) -> None:
        self._algorithm_state_enabled = bool(value)

    @property
    def firmware_version(self) -> Tuple[int, int, int]:
        """The measurement application version as ``(major, minor, patch)``."""
        minor, patch = self._rev_minor_patch
        return (self._rev_major, minor, patch)

    @property
    def serial_number(self) -> int:
        """The sensor's 32-bit serial number."""
        self._command = _CMD_SERIAL
        self._wait_for_command(_CMD_SERIAL, 0.05)
        self._wait(_CONTENTS, _CONTENT_SERIAL, 0.1, "the serial number")
        return struct.unpack_from("<I", self._read_reg(_RESULT_NUM + _SERIAL_OFFSET, 4))[0]

    @property
    def powered(self) -> bool:
        """Whether the sensor's CPU is powered.

        Setting this to ``False`` puts the sensor into its low-power state,
        where it draws a few microamps. Setting it back to ``True`` restarts
        the measurement application, and reloads the RAM firmware patch if one
        was loaded before sleeping.
        """
        return self._cpu_powered

    @powered.setter
    def powered(self, value: bool) -> None:
        if not value:
            self._cpu_powered = False
            return
        if self._firmware_patch_loaded:
            self.load_firmware_patch()
        else:
            self._start_app()

    def configure_histogram(self, histogram_type: int) -> None:
        """Enable raw histogram output alongside distance measurements.

        :param int histogram_type: One of the ``HISTOGRAM_*`` constants.
        :raises RuntimeError: if the sensor does not accept the command.
        """
        if histogram_type not in _HISTOGRAM_TYPES:
            raise ValueError(f"histogram_type must be one of {_HISTOGRAM_TYPES}")
        self._histogram_type = histogram_type
        if self._histogram_raw is None:
            self._histogram_raw = bytearray(_HIST_CHUNK_BYTES)
        self._write_histogram_mask(1 << histogram_type)
        self._int_enable |= _INT_DIAGNOSTIC

    def disable_histogram(self) -> None:
        """Stop histogram output and release the memory it used.

        :raises RuntimeError: if the sensor does not accept the command.
        """
        self._write_histogram_mask(0)
        self._int_enable &= ~_INT_DIAGNOSTIC
        self._histogram_type = None
        self._histogram_raw = None
        gc.collect()

    @property
    def histogram_ready(self) -> bool:
        """Whether a histogram is waiting to be read."""
        return bool(self._int_status & _INT_DIAGNOSTIC)

    def read_histogram(self) -> List[int]:
        """Read one 128-bin histogram and let the sensor continue.

        :return: 128 bin counts, already scaled by the sensor's reported shift.
        :raises RuntimeError: if :meth:`configure_histogram` has not run or the
            sensor does not accept the command.
        """
        if self._histogram_type is None:
            raise RuntimeError("call configure_histogram() before read_histogram()")

        self._command = _CMD_HIST_READ
        self._wait_for_command(_CMD_HIST_READ, 0.1)

        raw = self._histogram_raw
        bins = []
        self._read_histogram_chunk(raw)
        bins.extend(struct.unpack_from(_HIST_CHUNK_FMT, raw))

        # Reading STATE advances the sensor to the second sub-histogram.
        self._read_reg(_STATE, 4)
        self._read_histogram_chunk(raw)
        bins.extend(struct.unpack_from(_HIST_CHUNK_FMT, raw))

        if self._histogram_type == HISTOGRAM_PILEUP:
            scale = 1
        elif self._histogram_type == HISTOGRAM_PILEUP_TDC_SUM:
            scale = 2
        else:
            scale = raw[_HIST_CHUNK_BYTES - 2]
            if scale > _HIST_MAX_SCALE:
                scale = 0
        if scale:
            bins = [value << scale for value in bins]

        self._command = _CMD_HIST_CONTINUE
        self._wait_for_command(_CMD_HIST_CONTINUE, 0.1)
        self._int_status = _INT_DIAGNOSTIC
        return bins

    @staticmethod
    def _checked_gpio_mode(mode: int) -> int:
        if mode not in _GPIO_MODES:
            raise ValueError(f"GPIO mode must be one of {_GPIO_MODES}")
        return mode

    def _algorithm_config(self) -> int:
        if self._distance_mode == MODE_SHORT_RANGE:
            return 0
        config = _ALGO_DISTANCE_ENABLED
        if self._distance_mode in {MODE_5M, MODE_10M}:
            config |= _ALGO_VCSEL_CLOCK_DIV2 | _ALGO_LONG_RANGE
            if self._distance_mode == MODE_10M:
                config |= _ALGO_10M_MODE
        return config

    def _write_histogram_mask(self, mask: int) -> None:
        payload = bytearray(5)
        struct.pack_into("<I", payload, 0, mask)
        payload[4] = _CMD_HIST_CFG
        self._write_reg(_HIST_CFG_DATA, payload)
        self._wait_for_command(_CMD_HIST_CFG, 0.1)

    def _read_histogram_chunk(self, raw: bytearray) -> None:
        view = memoryview(raw)
        for block in range(_HIST_CHUNK_BYTES // _HIST_BLOCK - 1, -1, -1):
            start = block * _HIST_BLOCK
            self._reg_buf[0] = _RESULT_NUM + start
            with self.i2c_device as i2c:
                i2c.write_then_readinto(self._reg_buf, view[start : start + _HIST_BLOCK])

    def _write_reg(self, reg: int, data: bytes) -> None:
        buf = bytearray(len(data) + 1)
        buf[0] = reg
        buf[1:] = data
        with self.i2c_device as i2c:
            i2c.write(buf)

    def _read_reg(self, reg: int, length: int) -> bytearray:
        buf = bytearray(length)
        self._reg_buf[0] = reg
        with self.i2c_device as i2c:
            i2c.write_then_readinto(self._reg_buf, buf)
        return buf

    def _wait(
        self,
        reg: int,
        expected: int,
        timeout: float,
        description: str,
        *,
        mask: int = 0xFF,
    ) -> None:
        poll = 0.001 if timeout <= 1.0 else 0.01
        self._reg_buf[0] = reg
        value = self._poll_buf
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self.i2c_device as i2c:
                i2c.write_then_readinto(self._reg_buf, value)
            if value[0] & mask == expected:
                return
            time.sleep(poll)
        raise RuntimeError(f"TMF8806 timed out waiting for {description}")

    def _wait_for_cpu(self, timeout: float) -> None:
        self._wait(
            _ENABLE,
            _CPU_READY | _PWR_ON,
            timeout,
            "the CPU",
            mask=_CPU_READY | _PWR_ON,
        )

    def _wait_for_app(self, timeout: float) -> None:
        self._wait(_APPID, _APP_MEAS, timeout, "the measurement app")

    def _wait_for_command(self, command: int, timeout: float) -> None:
        poll = 0.001 if timeout <= 1.0 else 0.01
        state = self._poll_buf
        buf = self._command_buf
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._reg_buf[0] = _COMMAND
            with self.i2c_device as i2c:
                i2c.write_then_readinto(self._reg_buf, buf)
            if buf[0] == _CMD_IDLE and buf[1] == command:
                return
            self._reg_buf[0] = _STATE
            with self.i2c_device as i2c:
                i2c.write_then_readinto(self._reg_buf, state)
            if state[0] == _STATE_ERROR:
                raise RuntimeError(f"TMF8806 rejected command {command:#04x}")
            time.sleep(poll)
        raise RuntimeError(f"TMF8806 timed out waiting for command {command:#04x}")

    def _start_app(self) -> None:
        self._cpu_powered = True
        self._wait_for_cpu(0.1)
        if self._app_id != _APP_MEAS:
            self._app_request = _APP_MEAS
            self._wait_for_app(0.2)
        self._int_status = _INT_RESULT | _INT_DIAGNOSTIC
        self._int_enable = _INT_RESULT

    def _upload_firmware(self) -> None:
        gc.collect()  # give the image the best chance of fitting
        try:
            self._send_image()
        except MemoryError:
            raise RuntimeError(
                "TMF8806 firmware patch upload needs about 3 kB of free RAM, which this "
                "board cannot spare; the sensor still measures without it, but not in "
                "MODE_10M"
            ) from None
        finally:
            self._drop_firmware()

        # A RAM remap restarts the CPU, so there is no bootloader reply to read.
        self._write_reg(_BL_CMD, bytes((_BL_REMAP, 0, (~_BL_REMAP) & 0xFF)))
        self._wait_for_cpu(0.2)
        self._wait_for_app(0.2)

    @staticmethod
    def _drop_firmware() -> None:
        if sys.modules.pop(_FW_MODULE, None) is not None:
            package = sys.modules.get(_FW_PACKAGE)
            if package is not None:
                setattr(package, _FW_ATTR, None)
        gc.collect()

    def _send_image(self) -> None:
        try:
            from .tmf8806_firmware import FIRMWARE  # noqa: PLC0415
        except ImportError:
            raise RuntimeError(
                f"{_FW_MODULE} is missing; MODE_10M is unavailable without it"
            ) from None

        self._bootloader_command(_BL_INIT, bytes((_BL_SALT,)))
        self._bootloader_command(_BL_ADDR, b"\x00\x00")
        image = memoryview(FIRMWARE)
        for offset in range(0, len(image), _BL_CHUNK):
            self._bootloader_command(_BL_WRITE, image[offset : offset + _BL_CHUNK])

    def _bootloader_command(self, command: int, data: bytes) -> None:
        length = len(data)
        packet = self._packet
        packet[0] = _BL_CMD
        packet[1] = command
        packet[2] = length
        packet[3 : 3 + length] = data
        packet[3 + length] = ~(command + length + sum(data)) & 0xFF
        with self.i2c_device as i2c:
            i2c.write(packet, end=4 + length)

        deadline = time.monotonic() + 0.02
        while time.monotonic() < deadline:
            reply = self._read_reg(_BL_CMD, 3)
            if reply[0] >= _BL_BUSY:
                time.sleep(0.001)
                continue
            if reply[0] != _BL_READY or reply[1] != 0 or sum(reply) & 0xFF != _BL_CKSUM_OK:
                raise RuntimeError(f"TMF8806 bootloader rejected command {command:#04x}")
            return
        raise RuntimeError(f"TMF8806 bootloader stayed busy for command {command:#04x}")
