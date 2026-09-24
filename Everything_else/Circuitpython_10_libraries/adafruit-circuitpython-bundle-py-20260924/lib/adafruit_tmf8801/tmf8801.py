# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
:py:class:`~adafruit_tmf8801.tmf8801`
================================================================================

CircuitPython driver for the Adafruit TMF8801 Time of Flight Distance Sensor - 20mm to 2.5m


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit TMF8801 Time of Flight Distance Sensor - 20mm to 2.5m <https://www.adafruit.com/product/6522>`_

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
from adafruit_register.i2c_struct import ROUnaryStruct, Struct, UnaryStruct
from micropython import const

try:
    from typing import Optional, Tuple

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_TMF8801.git"

# Derived rather than hardcoded so renaming the package cannot silently break
# the cleanup in _drop_firmware(), which would leak the image into RAM.
_FW_ATTR = "tmf8801_firmware"
_FW_PACKAGE = __name__.rpartition(".")[0]
_FW_MODULE = f"{_FW_PACKAGE}.{_FW_ATTR}"

_DEFAULT_ADDR = const(0x41)

_APPID = const(0x00)
_REV_MAJOR = const(0x01)
_APPREQID = const(0x02)
_CMD_DATA9 = const(0x06)
_BL_CMD = const(0x08)
_COMMAND = const(0x10)
_PREVIOUS = const(0x11)
_REV_MINOR = const(0x12)
_STATE = const(0x1C)
_STATUS = const(0x1D)
_CONTENTS = const(0x1E)
_RESULT_NUM = const(0x20)
_ENABLE = const(0xE0)
_INT_STATUS = const(0xE1)
_INT_ENABLE = const(0xE2)
_ID = const(0xE3)
_REVID = const(0xE4)

_APP_BL = const(0x80)
_APP_MEAS = const(0xC0)
_CHIP_ID = const(0x07)

_PWR_ON = const(0x01)
_CPU_READY = const(0x40)
_CPU_RESET = const(0x80)

_BL_INIT = const(0x14)
_BL_WRITE = const(0x41)
_BL_ADDR = const(0x43)
_BL_REMAP = const(0x11)
_BL_BUSY = const(0x10)
_BL_READY = const(0x00)
_BL_CHUNK = const(16)
_BL_SALT = const(0x29)
_BL_CKSUM_OK = const(0xFF)

_CMD_MEAS_CAL = const(0x02)
_CMD_MEAS = const(0x03)
_CMD_CALIB = const(0x0A)
_CMD_SERIAL = const(0x47)
_CMD_STOP = const(0xFF)

_CONTENT_CALIB = const(0x0A)
_CONTENT_RESULT = const(0x55)
_STATE_IDLE = const(0x01)

_INT_RESULT = const(0x01)
_INT_ERROR = const(0x04)

_DATA_CALIB = const(0x01)
_DATA_ALGO = const(0x02)
_ALGO_DEFAULT = const(0x23)

_GPIO_MASK = const(0x0F)
_GPIO1_SHIFT = const(4)
_RELIABILITY_MASK = const(0x3F)
_MEAS_STATUS_SHIFT = const(6)

_CALIB_SIZE = const(14)
_ALGO_SIZE = const(11)
_ALGO_SEED_SIZE = const(3)
_RESULT_HDR = const(3)
_CONTENTS_OFFSET = const(1)
_FRAME_SIZE = const(30)
_CMD_BLOCK_SIZE = const(11)
_SERIAL_OFFSET = const(8)

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

_GPIO_MODES = (
    GPIO_DISABLED,
    GPIO_INPUT_ACTIVE_LOW,
    GPIO_INPUT_ACTIVE_HIGH,
    GPIO_OUTPUT_VCSEL,
    GPIO_OUTPUT_LOW,
    GPIO_OUTPUT_HIGH,
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
    ),
)
"""One complete TMF8801 measurement.

``number`` is a rolling result counter, ``distance`` is in millimeters,
``reliability`` runs from 0 (invalid) to 63 (best), ``status`` is one of the
``MEASUREMENT_*`` constants, ``system_clock`` is the sensor clock captured with
the result, and ``reference_hits`` and ``object_hits`` are raw SPAD hit counts.
"""


class TMF8801:
    """Driver for the ams OSRAM TMF8801 Time-of-Flight distance sensor.

    :param ~busio.I2C i2c: The I2C bus the TMF8801 is connected to.
    :param int address: The sensor's I2C address. Defaults to :const:`0x41`.

    Construction uploads about 11.6 kB of firmware to the sensor, which takes
    roughly a second and needs about 12 kB of free RAM.
    """

    chip_id = ROUnaryStruct(_ID, "<B")
    """The sensor's chip ID, which reads as ``0x07`` on the TMF8801."""

    revision_id = ROUnaryStruct(_REVID, "<B")
    """The sensor's hardware revision ID."""

    status = ROUnaryStruct(_STATUS, "<B")
    """The measurement application's status register."""

    _app_id = ROUnaryStruct(_APPID, "<B")
    _app_request = UnaryStruct(_APPREQID, "<B")
    _enable = UnaryStruct(_ENABLE, "<B")
    _cpu_powered = RWBit(_ENABLE, 0)
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
        self._packet = bytearray(_BL_CHUNK + 4)
        self._frame = bytearray(_FRAME_SIZE)

        if self.chip_id != _CHIP_ID:
            raise RuntimeError("Failed to find TMF8801 - check your wiring!")

        self._kilo_iterations = 900
        self._repetition_period = 33
        self._noise_threshold = 0
        self._gpio_modes = [GPIO_DISABLED, GPIO_DISABLED]
        self._calibration_data = None
        self._algorithm_state = None
        self._calibration_enabled = False
        self._algorithm_state_enabled = False

        self.reset()

    def reset(self) -> None:
        """Reset the sensor and reload its RAM measurement firmware.

        :raises RuntimeError: if there is not enough free RAM for the firmware
            image, or if the sensor does not restart into the measurement
            application.
        """
        self._enable = _CPU_RESET | _PWR_ON
        time.sleep(0.002)
        self._enable = _PWR_ON
        self._wait_for_cpu(0.1)
        self._wait(_APPID, _APP_BL, 0.1, "the bootloader")
        self._upload_firmware()
        self._start_app()

    def start_measuring(self, continuous: bool = True) -> None:
        """Start distance measurements using the current configuration.

        Stored calibration data and algorithm state are sent to the sensor
        first if they are available and enabled.

        :param bool continuous: Measure repeatedly at :attr:`repetition_period`
            when ``True``, or take a single measurement when ``False``.
        :raises RuntimeError: if the sensor does not accept the command.
        """
        use_calibration = self._calibration_enabled and self._calibration_data is not None
        use_state = (
            use_calibration and self._algorithm_state_enabled and self._algorithm_state is not None
        )

        flags = 0
        if use_calibration:
            self._write_reg(_RESULT_NUM, self._calibration_data)
            flags |= _DATA_CALIB
        if use_state:
            # Only the first three bytes seed the algorithm; the rest must be
            # zeroed or the sensor rejects the replayed state.
            seed = bytearray(_ALGO_SIZE)
            seed[:_ALGO_SEED_SIZE] = self._algorithm_state[:_ALGO_SEED_SIZE]
            self._write_reg(_RESULT_NUM + _CALIB_SIZE, seed)
            flags |= _DATA_ALGO

        command = bytearray(_CMD_BLOCK_SIZE)
        command[2] = flags
        command[3] = _ALGO_DEFAULT
        command[4] = (self._gpio_modes[0] & _GPIO_MASK) | (
            (self._gpio_modes[1] & _GPIO_MASK) << _GPIO1_SHIFT
        )
        command[6] = self._noise_threshold
        command[7] = self._repetition_period if continuous else 0
        command[8] = self._kilo_iterations & 0xFF
        command[9] = self._kilo_iterations >> 8
        command[10] = _CMD_MEAS_CAL if flags else _CMD_MEAS

        self._write_reg(_CMD_DATA9, command)
        self._wait_for_command(command[10], 0.02)

    def stop_measuring(self) -> None:
        """Stop measurements and wait for the sensor to become idle.

        :raises RuntimeError: if the sensor does not return to its idle state.
        """
        self._command = _CMD_STOP
        self._wait_for_command(_CMD_STOP, 0.25)
        self._wait(_STATE, _STATE_IDLE, 0.25, "the idle state")

    def factory_calibrate(self, timeout: float = 30.0) -> bytes:
        """Run factory calibration and store the resulting data.

        Calibration should be run with the sensor pointed at empty space, with
        no target within about 40 cm. On success the new data is stored and
        :attr:`calibration_enabled` is turned on.

        :param float timeout: Seconds to wait for calibration to finish.
        :return: The 14 bytes of factory calibration data.
        :raises RuntimeError: if calibration does not complete in time or the
            sensor publishes something other than calibration data.
        """
        command = bytearray(_CMD_BLOCK_SIZE)
        command[10] = _CMD_CALIB
        self._write_reg(_CMD_DATA9, command)
        self._wait_for_command(_CMD_CALIB, 0.02)
        self._wait(_INT_STATUS, _INT_RESULT, timeout, "calibration to finish", mask=_INT_RESULT)

        if self._contents != _CONTENT_CALIB:
            raise RuntimeError("TMF8801 published a result instead of calibration data")

        self._calibration_data = bytes(self._read_reg(_RESULT_NUM, _CALIB_SIZE))
        self._calibration_enabled = True
        self._int_status = _INT_RESULT
        return self._calibration_data

    @property
    def data_ready(self) -> bool:
        """Whether a new measurement result is waiting to be read."""
        return bool(self._int_status & _INT_RESULT)

    @property
    def result(self) -> Optional[Result]:
        """The latest complete measurement as a :data:`Result`.

        ``None`` if no result is ready or if the sensor is currently publishing
        something other than a distance result. Reading this clears the result
        interrupt and stores the algorithm state that comes with the result, so
        each measurement can only be read once.
        """
        if not self.data_ready:
            return None

        # STATUS through the end of the result is read in one transaction; the
        # sensor uses that block read to latch the result and system clock
        # together.
        frame = self._frame
        self._reg_buf[0] = _STATUS
        with self.i2c_device as i2c:
            i2c.write_then_readinto(self._reg_buf, frame)

        if frame[_CONTENTS_OFFSET] != _CONTENT_RESULT:
            return None

        number, quality, distance, clock = struct.unpack_from("<BBHI", frame, _RESULT_HDR)
        state_start = _RESULT_HDR + 8
        self._algorithm_state = bytes(frame[state_start : state_start + _ALGO_SIZE])
        reference_hits, object_hits = struct.unpack_from("<II", frame, state_start + _ALGO_SIZE)
        self._int_status = _INT_RESULT

        return Result(
            number,
            distance,
            quality & _RELIABILITY_MASK,
            quality >> _MEAS_STATUS_SHIFT,
            clock,
            reference_hits,
            object_hits,
        )

    @property
    def distance(self) -> Optional[int]:
        """The measured distance in millimeters.

        ``None`` when no result is ready or the result had a reliability of
        zero. Like :attr:`result`, reading this consumes the measurement.
        """
        result = self.result
        if result is None or result.reliability == 0:
            return None
        return result.distance

    @property
    def kilo_iterations(self) -> int:
        """Integration iterations per measurement, in thousands.

        Higher values trade measurement rate for range and accuracy. Defaults
        to 900, meaning 900,000 iterations.
        """
        return self._kilo_iterations

    @kilo_iterations.setter
    def kilo_iterations(self, value: int) -> None:
        if not 0 <= value <= 0xFFFF:
            raise ValueError("kilo_iterations must be from 0 to 65535")
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
        """Object detection noise threshold, from 0 to 255.

        Zero, the default, lets the sensor use its own threshold.
        """
        return self._noise_threshold

    @noise_threshold.setter
    def noise_threshold(self, value: int) -> None:
        if not 0 <= value <= 0xFF:
            raise ValueError("noise_threshold must be from 0 to 255")
        self._noise_threshold = value

    @property
    def gpio0_mode(self) -> int:
        """The function assigned to GPIO0 during capture.

        One of :const:`GPIO_DISABLED`, :const:`GPIO_INPUT_ACTIVE_LOW`,
        :const:`GPIO_INPUT_ACTIVE_HIGH`, :const:`GPIO_OUTPUT_VCSEL`,
        :const:`GPIO_OUTPUT_LOW` or :const:`GPIO_OUTPUT_HIGH`.
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
        """The 11 bytes of algorithm state from the most recent result.

        ``None`` until a result has been read or state is assigned. Replaying
        this on the next run lets the sensor skip part of its warm-up.
        """
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
        """The sensor's 16-bit serial number.

        Reading this issues a command to the sensor, so it should be read while
        the sensor is idle rather than mid-measurement.
        """
        self._command = _CMD_SERIAL
        self._wait_for_command(_CMD_SERIAL, 0.1)
        self._wait(_CONTENTS, _CMD_SERIAL, 0.1, "the serial number")
        return struct.unpack_from("<H", self._read_reg(_RESULT_NUM + _SERIAL_OFFSET, 2))[0]

    @property
    def powered(self) -> bool:
        """Whether the sensor's CPU is powered.

        Setting this to ``False`` puts the sensor into its low-power state.
        Setting it back to ``True`` waits for the CPU to become ready again;
        the uploaded firmware survives, so no reset is needed.
        """
        return self._cpu_powered

    @powered.setter
    def powered(self, value: bool) -> None:
        self._cpu_powered = bool(value)
        if value:
            self._wait_for_cpu(0.1)

    @staticmethod
    def _checked_gpio_mode(mode: int) -> int:
        if mode not in _GPIO_MODES:
            raise ValueError(f"GPIO mode must be one of {_GPIO_MODES}")
        return mode

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
        # Short waits poll hard; a long one (factory calibration) backs off so
        # that 30 s does not become 30,000 I2C transactions.
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
        raise RuntimeError(f"TMF8801 timed out waiting for {description}")

    def _wait_for_cpu(self, timeout: float) -> None:
        self._wait(_ENABLE, _CPU_READY | _PWR_ON, timeout, "the CPU")

    def _wait_for_app(self, timeout: float) -> None:
        self._wait(_APPID, _APP_MEAS, timeout, "the measurement app")

    def _wait_for_command(self, command: int, timeout: float) -> None:
        self._wait(_PREVIOUS, command, timeout, f"command {command:#04x}")

    def _start_app(self) -> None:
        self._cpu_powered = True
        self._wait_for_cpu(0.1)
        if self._app_id != _APP_MEAS:
            self._app_request = _APP_MEAS
            self._wait_for_app(0.2)
        self._int_status = _INT_RESULT | _INT_ERROR
        self._int_enable = _INT_RESULT | _INT_ERROR

    def _upload_firmware(self) -> None:
        gc.collect()  # give the image the best chance of fitting
        try:
            self._send_image()
        except MemoryError:
            raise RuntimeError(
                "TMF8801 firmware upload needs about 12 kB of free RAM, which this board "
                "cannot spare; the sensor cannot measure without it"
            ) from None
        finally:
            # _send_image()'s reference is gone by now, so this is what actually
            # releases the ~11.6 kB image.
            self._drop_firmware()

        # A RAM remap restarts the CPU, so there is no bootloader reply to read.
        self._write_reg(_BL_CMD, bytes((_BL_REMAP, 0, (~_BL_REMAP) & 0xFF)))
        self._wait_for_cpu(0.2)
        self._wait_for_app(0.2)

    @staticmethod
    def _drop_firmware() -> None:
        # Importing a submodule also binds it as an attribute of its package, so
        # the image only becomes collectable once both references are cleared.
        if sys.modules.pop(_FW_MODULE, None) is not None:
            package = sys.modules.get(_FW_PACKAGE)
            if package is not None:
                setattr(package, _FW_ATTR, None)
        gc.collect()

    def _send_image(self) -> None:
        try:
            # Deferred on purpose: see _drop_firmware() for why the image must
            # not be held by this module.
            from .tmf8801_firmware import FIRMWARE  # noqa: PLC0415
        except ImportError:
            raise RuntimeError(
                f"{_FW_MODULE} is missing; the sensor cannot measure without it"
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
                raise RuntimeError(f"TMF8801 bootloader rejected command {command:#04x}")
            return
        raise RuntimeError(f"TMF8801 bootloader stayed busy for command {command:#04x}")
