# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_stcc4`
================================================================================

CircuitPython driver for the STCC4 and SHT41 - CO2, Temperature and Humidity Sensor


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit STCC4 and SHT41 - CO2, Temperature & Humidity Sensor <https://www.adafruit.com/product/6478>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

"""

import struct
import time

from adafruit_bus_device.i2c_device import I2CDevice
from micropython import const

try:
    from typing import Tuple

    from busio import I2C
except ImportError:
    pass

__version__ = "1.2.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_STCC4.git"

_STCC4_DEFAULT_ADDR = const(0x64)
_STCC4_PRODUCT_ID = const(0x0901018A)

_START_CONTINUOUS = const(0x218B)
_STOP_CONTINUOUS = const(0x3F86)
_READ_MEASUREMENT = const(0xEC05)
_SET_RHT_COMPENSATION = const(0xE000)
_SET_PRESSURE_COMPENSATION = const(0xE016)
_MEASURE_SINGLE_SHOT = const(0x219D)
_ENTER_SLEEP = const(0x3650)
_EXIT_SLEEP = const(0x00)
_PERFORM_CONDITIONING = const(0x29BC)
_SOFT_RESET = const(0x06)
_FACTORY_RESET = const(0x3632)
_SELF_TEST = const(0x278C)
_ENABLE_TESTING = const(0x3FBC)
_DISABLE_TESTING = const(0x3F3D)
_FORCED_RECALIBRATION = const(0x362F)
_GET_PRODUCT_ID = const(0x365B)

# Status bit masks
STATUS_VOLTAGE_ERROR = const(0x0001)
"""Supply voltage error flag."""
STATUS_DEBUG = const(0x000E)
"""Debug flags mask."""
STATUS_SHT_NOT_CONNECTED = const(0x0010)
"""SHT sensor not connected flag."""
STATUS_MEMORY_ERROR = const(0x0060)
"""Memory error flags mask."""
STATUS_TESTING_MODE = const(0x4000)
"""Testing mode active flag."""


class STCC4:
    """Driver for the STCC4 CO2 sensor with integrated SHT41.

    :param ~busio.I2C i2c_bus: The I2C bus the STCC4 is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x64`.
    """

    def __init__(self, i2c_bus: I2C, address: int = _STCC4_DEFAULT_ADDR) -> None:
        self.i2c_device = I2CDevice(i2c_bus, address)

        self.reset()
        pid = self.product_id
        if pid != _STCC4_PRODUCT_ID:
            raise RuntimeError(
                f"Failed to find STCC4 - expected product ID 0x{_STCC4_PRODUCT_ID:08X}, "
                + f"got 0x{pid:08X}"
            )

        self._co2 = 0
        self._temperature = 0.0
        self._humidity = 0.0
        self._status = 0
        self._continuous = False

    @staticmethod
    def _crc8(data: bytes) -> int:
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc <<= 1
                crc &= 0xFF
        return crc

    def _write_command(self, command: int) -> None:
        buf = struct.pack(">H", command)
        with self.i2c_device as i2c:
            i2c.write(buf)

    def _read_command(self, command: int, word_count: int) -> bytearray:
        cmd_buf = struct.pack(">H", command)
        read_len = word_count * 3
        reply = bytearray(read_len)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(cmd_buf, reply)

        for i in range(word_count):
            offset = i * 3
            if self._crc8(reply[offset : offset + 2]) != reply[offset + 2]:
                raise RuntimeError(
                    f"CRC mismatch at word {i} in response to command 0x{command:04X}"
                )
        return reply

    def _read_words(self, command: int, word_count: int) -> Tuple[int, ...]:
        """
        Send command to sensor and read word_count words back

        See _read_words_after_wait for when a subsequent read needs to happen after
        waiting a delay
        """
        raw = self._read_command(command, word_count)
        words = []
        for i in range(word_count):
            offset = i * 3
            words.append((raw[offset] << 8) | raw[offset + 1])
        return tuple(words)

    def _read_words_after_wait(self, command: int, word_count: int) -> Tuple[int, ...]:
        """
        Read ``word_count`` 16-bit words from the sensor *without* re-sending
        a command first.

        Used by commands that need a delay between the command write and the
        result read (e.g. :meth:`self_test`, :meth:`forced_recalibration`). The
        caller must already have written the command and slept for the required
        execution time. Using :meth:`_read_words` here would be wrong, because it
        re-issues the command via ``write_then_readinto`` before reading.
        """
        reply = bytearray(word_count * 3)
        with self.i2c_device as i2c:
            i2c.readinto(reply)
        words = []
        for i in range(word_count):
            offset = i * 3
            if self._crc8(reply[offset : offset + 2]) != reply[offset + 2]:
                raise RuntimeError(
                    f"CRC mismatch at word {i} in response to command 0x{command:04X}"
                )
            words.append((reply[offset] << 8) | reply[offset + 1])
        return tuple(words)

    def _write_command_with_arg(self, command: int, arg: int) -> None:
        arg_bytes = struct.pack(">H", arg)
        crc = self._crc8(arg_bytes)
        buf = struct.pack(">H", command) + arg_bytes + bytes([crc])
        with self.i2c_device as i2c:
            i2c.write(buf)

    def _read_measurement(self) -> None:
        # Continuous mode emits ~1 sample/sec and NACKs read_measurement when no
        # fresh data is ready (there's no data-ready command on the STCC4), which
        # shows up as OSError/EIO. Retry briefly before giving up.
        words = None
        for _ in range(15):  # ~1.5 s ceiling, covers one missed interval
            try:
                words = self._read_words(_READ_MEASUREMENT, 4)
                break
            except OSError:
                time.sleep(0.1)
        if words is None:
            raise RuntimeError("STCC4 measurement not ready")
        self._co2 = words[0]
        self._temperature = words[1] * 175.0 / 65535.0 - 45.0
        self._humidity = words[2] * 125.0 / 65535.0 - 6.0
        self._status = words[3]

    @property
    def CO2(self) -> int:
        """CO2 concentration in parts per million (ppm).

        If continuous measurement is not active, a single-shot measurement is
        triggered automatically.

        :return: CO2 concentration in ppm.
        :rtype: int
        """
        if not self._continuous:
            self.measure_single_shot()
        self._read_measurement()
        return self._co2

    @property
    def temperature(self) -> float:
        """Temperature in degrees Celsius.

        .. note::
            Call :attr:`CO2` first to trigger a fresh measurement, or use
            :meth:`measure_single_shot` / :meth:`continuous_measurement`.
            This property returns the value from the most recent reading.

        :return: Temperature in °C.
        :rtype: float
        """
        return self._temperature

    @property
    def relative_humidity(self) -> float:
        """Relative humidity as a percentage.

        .. note::
            Call :attr:`CO2` first to trigger a fresh measurement, or use
            :meth:`measure_single_shot` / :meth:`continuous_measurement`.
            This property returns the value from the most recent reading.

        :return: Relative humidity in %.
        :rtype: float
        """
        return self._humidity

    @property
    def status(self) -> int:
        """Raw status word from the most recent measurement.

        Compare against the ``STATUS_*`` constants to check for
        specific conditions.

        :return: 16-bit status word.
        :rtype: int
        """
        return self._status

    def measure_single_shot(self) -> None:
        """Trigger a single-shot measurement and wait for it to complete.

        After calling this method, read :attr:`CO2`, :attr:`temperature`,
        and :attr:`relative_humidity` to retrieve the results.
        """
        self._write_command(_MEASURE_SINGLE_SHOT)
        time.sleep(0.5)  # Single shot measurement time

    @property
    def continuous_measurement(self) -> bool:
        """Enable or disable continuous measurement with a 1 s sampling interval.

        :param bool value: ``True`` to start, ``False`` to stop.
        :return: Current continuous measurement state.
        :rtype: bool
        """
        return self._continuous

    @continuous_measurement.setter
    def continuous_measurement(self, value: bool) -> None:
        if value:
            self._write_command(_START_CONTINUOUS)
            time.sleep(1)  # Wait for first measurement
        else:
            self._write_command(_STOP_CONTINUOUS)
            time.sleep(1.2)  # Datasheet says wait 1200ms
        self._continuous = value

    def pressure_compensation(self, pressure_hpa: int) -> None:
        """Ambient pressure for CO2 compensation.

        :param int pressure_hpa: Ambient pressure in hPa (e.g. 1013 for sea level).
        """
        # STCC4 uses Pa/2 (e.g. 101300/2 = 50650) for its parameter per datasheet
        # Adafruit uses hPa (Pa = hPa * 100).  hPa * 100 / 2 = hPa * 50
        self._write_command_with_arg(_SET_PRESSURE_COMPENSATION, pressure_hpa * 50)

    def rht_compensation(self, temperature: float, relative_humidity: float) -> None:
        """Provide external RH/T compensation values for CO2 compensation.

        :param float temperature: Ambient temperature in °C.
        :param float relative_humidity: Ambient relative humidity in %.

        .. warning::
            Only for STCC4 boards **without** a directly-connected SHT4x. On Adafruit's
            STCC4 (which has an onboard SHT4x) the sensor handles RH/T compensation
            itself and this method should not be used.

        """
        raw_t = int(round((temperature + 45.0) * 65535.0 / 175.0)) & 0xFFFF
        raw_rh = int(round((relative_humidity + 6.0) * 65535.0 / 125.0)) & 0xFFFF
        # two words, each followed by its own CRC
        args = struct.pack(">H", raw_t) + bytes([self._crc8(struct.pack(">H", raw_t))])
        args += struct.pack(">H", raw_rh) + bytes([self._crc8(struct.pack(">H", raw_rh))])
        buf = struct.pack(">H", _SET_RHT_COMPENSATION) + args
        # The only multiple arg cmd so directly code write (vs _write_command_with arg)
        with self.i2c_device as i2c:
            i2c.write(buf)

    def perform_conditioning(self) -> None:
        """Run sensor conditioning to improve initial CO2 accuracy.

        .. warning::
            This blocks for approximately **22 seconds**.
        """
        self._write_command(_PERFORM_CONDITIONING)
        time.sleep(22)

    def forced_recalibration(self, reference_co2: int) -> int:
        """Perform forced recalibration (FRC) using a known CO2 reference.

        :param int reference_co2: Known CO2 concentration in ppm.
        :return: FRC correction value. ``0xFFFF`` indicates failure.
        :rtype: int

        .. warning::
            The sensor must be operated for at least 40 s in continuous mode
            (or held in idle after single-shot operation), then stopped with a
            full ``stop`` execution-time wait, before calling this. Calling it
            on an unconditioned sensor returns ``0xFFFF``.  See the datasheet
            for more specific requirements

        .. seealso:: :meth:\continuous_measurement
        """
        self._write_command_with_arg(_FORCED_RECALIBRATION, reference_co2)
        time.sleep(0.090)
        raw = self._read_words_after_wait(_FORCED_RECALIBRATION, 1)[0]
        if raw == 0xFFFF:  # Error Condition
            return raw
        return raw - 0x8000  # correction = return value - 32768 per datasheet

    @property
    def product_id(self) -> int:
        """32-bit product identifier.

        :return: Product ID read from the sensor.
        :rtype: int
        """
        words = self._read_words(_GET_PRODUCT_ID, 2)
        return (words[0] << 16) | words[1]

    @property
    def serial_number(self) -> bytearray:
        """64-bit unique serial number for this sensor

        :return: Serial Number
        :rtype: bytearray
        """
        words = self._read_words(_GET_PRODUCT_ID, 6)
        # Skip the first two words (product id); serial number is the next four words
        return bytearray(struct.pack(">HHHH", *words[2:6]))

    def reset(self) -> None:
        """Perform a soft reset of the sensor."""
        buf = bytes([_SOFT_RESET])
        with self.i2c_device as i2c:
            i2c.write(buf)
        time.sleep(0.01)

    def factory_reset(self) -> None:
        """Perform a factory reset, clearing FRC and ASC algorithm history."""
        self._write_command(_FACTORY_RESET)
        time.sleep(0.1)

    def self_test(self) -> int:
        """Run the built-in self-test.

        :return: Self-test result. ``0`` indicates no errors detected.
        :rtype: int
        """
        self._write_command(_SELF_TEST)
        time.sleep(0.36)
        return self._read_words_after_wait(_SELF_TEST, 1)[0]

    @property
    def sleep_mode(self) -> None:
        """Sleep mode is write-only; reading is not supported."""
        raise AttributeError("sleep_mode is write-only")

    @sleep_mode.setter
    def sleep_mode(self, enable: bool) -> None:
        """Enter or exit low-power sleep mode.

        :param bool enable: ``True`` to sleep, ``False`` to wake.
        """
        if enable:
            self._write_command(_ENTER_SLEEP)
            time.sleep(0.001)
        else:
            buf = bytes([_EXIT_SLEEP])
            with self.i2c_device as i2c:
                i2c.write(buf)
            time.sleep(0.005)
