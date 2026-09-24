# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_sgp41`
================================================================================

CircuitPython driver for the SGP41 Multi-Pixel Gas Sensor Breakout


* Author(s): Liz Clark

Implementation Notes
--------------------

**Hardware:**

* `Adafruit SGP41 Gas Sensor Breakout <https://www.adafruit.com/product/6455>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

import time

from adafruit_bus_device.i2c_device import I2CDevice
from micropython import const

try:
    from typing import List, Tuple

    from busio import I2C
except ImportError:
    pass

__version__ = "1.0.2"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_SGP41.git"

_SGP41_DEFAULT_ADDR = const(0x59)

_SGP41_CMD_EXECUTE_CONDITIONING = const(0x2612)
_SGP41_CMD_MEASURE_RAW_SIGNALS = const(0x2619)
_SGP41_CMD_EXECUTE_SELF_TEST = const(0x280E)
_SGP41_CMD_TURN_HEATER_OFF = const(0x3615)
_SGP41_CMD_GET_SERIAL_NUMBER = const(0x3682)
_SGP41_CMD_SOFT_RESET = const(0x0006)

_SGP41_CONDITIONING_DELAY = 0.05  # 50ms
_SGP41_MEASUREMENT_DELAY = 0.05  # 50ms
_SGP41_SELF_TEST_DELAY = 0.32  # 320ms

_SGP41_SELF_TEST_OK = const(0xD400)

_SGP41_GENERAL_CALL_ADDR = const(0x00)


class SGP41:
    """Driver for the SGP41 gas sensor."""

    def __init__(self, i2c_bus: I2C, address: int = _SGP41_DEFAULT_ADDR) -> None:
        """
        Initialize the SGP41 sensor.

        :param i2c_bus: The I2C bus the SGP41 is connected to
        :param address: The I2C device address. Default is 0x59
        """
        self.i2c_device = I2CDevice(i2c_bus, address)
        self._i2c_bus = i2c_bus
        self._humidity = 50.0
        self._temperature = 25.0
        self._voc_algorithm = None
        self._nox_algorithm = None

        # Verify device is present and working
        serial = self.serial_number
        if serial in {(0x0000, 0x0000, 0x0000), (0xFFFF, 0xFFFF, 0xFFFF)}:
            raise RuntimeError("Failed to find SGP41 sensor - check your wiring!")

    @property
    def serial_number(self) -> Tuple[int, int, int]:
        """
        The 48-bit serial number as a tuple of three 16-bit words.

        :return: Tuple of (word0, word1, word2)
        """
        self._write_command(_SGP41_CMD_GET_SERIAL_NUMBER)
        time.sleep(0.001)  # 1ms delay
        return tuple(self._read_words(3))

    @property
    def self_test_result(self) -> int:
        """
        Execute the built-in self-test and return the raw result.

        :return: Raw 16-bit test result (0xD400 = pass)
        """
        self._write_command(_SGP41_CMD_EXECUTE_SELF_TEST)
        time.sleep(_SGP41_SELF_TEST_DELAY)
        return self._read_words(1)[0]

    @property
    def self_test_passed(self) -> bool:
        """
        Execute self-test and return True if passed, False otherwise.

        :return: True if self-test passed
        """
        result = self.self_test_result
        return result == _SGP41_SELF_TEST_OK

    def measure_raw(
        self,
        humidity: float = None,
        temperature: float = None,
    ) -> Tuple[int, int]:
        """
        Measure raw VOC and NOx signals from the sensor.

        :param humidity: Relative humidity in percent (0-100). If None, uses stored value.
        :param temperature: Temperature in degrees Celsius (-45 to 130). If None, uses stored value.
        :return: Tuple of (voc_raw, nox_raw) tick values
        """
        if humidity is None:
            humidity = self._humidity
        if temperature is None:
            temperature = self._temperature

        rh_ticks = self._humidity_to_ticks(humidity)
        t_ticks = self._temperature_to_ticks(temperature)

        self._write_command(_SGP41_CMD_MEASURE_RAW_SIGNALS, [rh_ticks, t_ticks])
        time.sleep(_SGP41_MEASUREMENT_DELAY)

        results = self._read_words(2)
        return results[0], results[1]

    def conditioning(
        self,
        humidity: float = None,
        temperature: float = None,
    ) -> int:
        """
        Execute the conditioning command for the sensor.

        The SGP41 sensor requires a conditioning period when first powered on.
        This should be called once per second for the first 10 seconds after power-up.

        :param humidity: Relative humidity in percent (0-100). If None, uses stored value.
        :param temperature: Temperature in degrees Celsius (-45 to 130). If None, uses stored value.
        :return: VOC raw tick value
        """
        if humidity is None:
            humidity = self._humidity
        if temperature is None:
            temperature = self._temperature

        rh_ticks = self._humidity_to_ticks(humidity)
        t_ticks = self._temperature_to_ticks(temperature)

        self._write_command(_SGP41_CMD_EXECUTE_CONDITIONING, [rh_ticks, t_ticks])
        time.sleep(_SGP41_CONDITIONING_DELAY)

        return self._read_words(1)[0]

    @property
    def raw_voc(self) -> int:
        """
        The raw VOC signal from the sensor using stored compensation values.

        :return: VOC raw tick value
        """
        voc_raw, _ = self.measure_raw()
        return voc_raw

    @property
    def raw_nox(self) -> int:
        """
        The raw NOx signal from the sensor using stored compensation values.

        :return: NOx raw tick value
        """
        _, nox_raw = self.measure_raw()
        return nox_raw

    def measure_index(
        self,
        humidity: float = None,
        temperature: float = None,
    ) -> Tuple[int, int]:
        """
        Measure humidity-compensated VOC and NOx index values.

        The Sensirion gas index algorithm expects a 1 Hz sampling rate; call
        this method once per second. During the first 45 seconds the algorithm
        is warming up and returns ``0`` for both indices; afterwards each index
        is in the range ``1..500`` with ``100`` representing typical indoor air
        for VOC and ``1`` for NOx.

        :param humidity: Relative humidity in percent (0-100). If None, uses stored value.
        :param temperature: Temperature in degrees Celsius (-45 to 130). If None, uses stored value.
        :return: Tuple of (voc_index, nox_index)
        """
        if self._voc_algorithm is None:
            from adafruit_sgp41.gas_index_algorithm import (
                ALGORITHM_TYPE_NOX,
                ALGORITHM_TYPE_VOC,
                GasIndexAlgorithm,
            )

            self._voc_algorithm = GasIndexAlgorithm(ALGORITHM_TYPE_VOC)
            self._nox_algorithm = GasIndexAlgorithm(ALGORITHM_TYPE_NOX)

        voc_raw, nox_raw = self.measure_raw(humidity=humidity, temperature=temperature)
        voc_index = self._voc_algorithm.process(voc_raw)
        nox_index = self._nox_algorithm.process(nox_raw)
        return voc_index, nox_index

    def heater_off(self) -> None:
        """
        Turn off the integrated heater and enter idle mode.

        Note: The sensor will need conditioning again after turning the heater back on.
        """
        self._write_command(_SGP41_CMD_TURN_HEATER_OFF)
        time.sleep(0.001)

    def reset(self) -> None:
        """
        Perform a soft reset.
        """
        buffer = bytearray(2)
        buffer[0] = (_SGP41_CMD_SOFT_RESET >> 8) & 0xFF
        buffer[1] = _SGP41_CMD_SOFT_RESET & 0xFF

        with I2CDevice(self._i2c_bus, _SGP41_GENERAL_CALL_ADDR) as device:
            device.write(buffer)

        time.sleep(0.02)  # 20ms delay for device to recover

    @property
    def relative_humidity(self) -> float:
        """
        The relative humidity value used for compensation.

        :return: Relative humidity in percent (0-100)
        """
        return self._humidity

    @relative_humidity.setter
    def relative_humidity(self, value: float) -> None:
        """
        Set the relative humidity value for compensation.

        :param value: Relative humidity in percent (0-100)
        """
        self._humidity = max(0.0, min(100.0, value))

    @property
    def temperature(self) -> float:
        """
        The temperature value used for compensation.

        :return: Temperature in degrees Celsius
        """
        return self._temperature

    @temperature.setter
    def temperature(self, value: float) -> None:
        """
        Set the temperature value for compensation.

        :param value: Temperature in degrees Celsius (-45 to 130)
        """
        self._temperature = max(-45.0, min(130.0, value))

    @staticmethod
    def _humidity_to_ticks(humidity: float) -> int:
        humidity = max(0.0, min(100.0, humidity))
        return int(humidity * 65535.0 / 100.0 + 0.5)

    @staticmethod
    def _temperature_to_ticks(temperature: float) -> int:
        temperature = max(-45.0, min(130.0, temperature))
        return int((temperature + 45.0) * 65535.0 / 175.0 + 0.5)

    def _write_command(self, command: int, data: List[int] = None) -> None:
        buffer = bytearray(2)
        buffer[0] = (command >> 8) & 0xFF
        buffer[1] = command & 0xFF

        if data:
            for word in data:
                buffer.append((word >> 8) & 0xFF)
                buffer.append(word & 0xFF)
                buffer.append(self._crc8(word))

        with self.i2c_device as i2c:
            i2c.write(buffer)

    def _read_words(self, num_words: int) -> List[int]:
        """
        Read data words from the sensor with CRC verification.

        :param num_words: Number of 16-bit words to read
        :return: List of data words
        :raises RuntimeError: If CRC check fails
        """
        if num_words == 0:
            return []

        buffer = bytearray(num_words * 3)  # Each word is 2 bytes + 1 CRC byte

        with self.i2c_device as i2c:
            i2c.readinto(buffer)

        words = []
        for i in range(num_words):
            offset = i * 3
            word = (buffer[offset] << 8) | buffer[offset + 1]
            crc = buffer[offset + 2]

            if self._crc8(word) != crc:
                raise RuntimeError("CRC check failed while reading from SGP41")

            words.append(word)

        return words

    @staticmethod
    def _crc8(word: int) -> int:
        """
        Calculate CRC-8 checksum for a 16-bit word.

        :param word: 16-bit data word
        :return: 8-bit CRC checksum
        """
        crc = 0xFF
        bytes_to_check = [(word >> 8) & 0xFF, word & 0xFF]

        for byte in bytes_to_check:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc <<= 1
                crc &= 0xFF  # Keep it 8-bit

        return crc
