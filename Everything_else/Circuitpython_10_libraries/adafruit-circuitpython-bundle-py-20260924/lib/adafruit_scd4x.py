# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_scd4x`
================================================================================

Driver for Sensirion SCD4X CO2 sensor


* Author(s): ladyada

Implementation Notes
--------------------

**Hardware:**

* `Adafruit SCD4X breakout board <https://www.adafruit.com/product/5187>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

import struct
import time

from adafruit_bus_device import i2c_device
from micropython import const

try:
    from typing import Tuple, Union

    from busio import I2C
except ImportError:
    pass

__version__ = "1.4.13"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_SCD4X.git"

SCD4X_DEFAULT_ADDR = 0x62
_SCD4X_REINIT = const(0x3646)
_SCD4X_FACTORYRESET = const(0x3632)
_SCD4X_FORCEDRECAL = const(0x362F)
_SCD4X_SELFTEST = const(0x3639)
_SCD4X_DATAREADY = const(0xE4B8)
_SCD4X_STOPPERIODICMEASUREMENT = const(0x3F86)
_SCD4X_STARTPERIODICMEASUREMENT = const(0x21B1)
_SCD4X_STARTLOWPOWERPERIODICMEASUREMENT = const(0x21AC)
_SCD4X_READMEASUREMENT = const(0xEC05)
_SCD4X_SERIALNUMBER = const(0x3682)
_SCD4X_GETTEMPOFFSET = const(0x2318)
_SCD4X_SETTEMPOFFSET = const(0x241D)
_SCD4X_GETALTITUDE = const(0x2322)
_SCD4X_SETALTITUDE = const(0x2427)
_SCD4X_SETPRESSURE = const(0xE000)
_SCD4X_PERSISTSETTINGS = const(0x3615)
_SCD4X_GETASCE = const(0x2313)
_SCD4X_SETASCE = const(0x2416)
_SCD4X_MEASURESINGLESHOT = const(0x219D)
_SCD4X_MEASURESINGLESHOTRHTONLY = const(0x2196)
_SCD4X_POWERDOWN = const(0x36E0)
_SCD4X_WAKEUP = const(0x36F6)
_SCD4X_GETPRESSURE = const(0xE000)  # shares its opcode with _SCD4X_SETPRESSURE
_SCD4X_GETASCTARGET = const(0x233F)
_SCD4X_SETASCTARGET = const(0x243A)
_SCD4X_GETASCINITIALPERIOD = const(0x2340)
_SCD4X_SETASCINITIALPERIOD = const(0x2445)
_SCD4X_GETASCSTANDARDPERIOD = const(0x234B)
_SCD4X_SETASCSTANDARDPERIOD = const(0x244E)
_SCD4X_GETSENSORVARIANT = const(0x202F)

# Variant code (bits 15:12 of the get_sensor_variant word) to ASCII name,
# per the SCD4x datasheet v1.7 Table 31.
_SCD4X_VARIANTS = {0x0: "SCD40", 0x1: "SCD41", 0x5: "SCD43"}


class SCD4X:
    """
    CircuitPython helper class for using the SCD4X CO2 sensor

    :param ~busio.I2C i2c_bus: The I2C bus the SCD4X is connected to.
    :param int address: The I2C device address for the sensor. Default is :const:`0x62`

    **Quickstart: Importing and using the SCD4X**

        Here is an example of using the :class:`SCD4X` class.
        First you will need to import the libraries to use the sensor

        .. code-block:: python

            import board
            import adafruit_scd4x

        Once this is done you can define your `board.I2C` object and define your sensor object

        .. code-block:: python

            i2c = board.I2C()   # uses board.SCL and board.SDA
            scd = adafruit_scd4x.SCD4X(i2c)
            scd.start_periodic_measurement()

        Now you have access to the CO2, temperature and humidity using
        the :attr:`CO2`, :attr:`temperature` and :attr:`relative_humidity` attributes

        .. code-block:: python

            if scd.data_ready:
                temperature = scd.temperature
                relative_humidity = scd.relative_humidity
                co2_ppm_level = scd.CO2

    .. note::

        Once :meth:`start_periodic_measurement` or :meth:`start_low_periodice_measurement`
        are run most of the functions and properties except: read_measurement,
        get_data_ready_status, stop_periodic_measurement, set_ambient_pressure and
        get_ambient_pressure cause an error when accessed.  If using these after starting
        measurement first run :meth:`stop_periodic_measurement`

        Some features are available on the **SCD41 and SCD43 only**, not the base
        SCD40:

        * :meth:`measure_single_shot`
        * :meth:`measure_single_shot_rht_only`
        * :meth:`power_down`
        * :meth:`wake_up`

        A base SCD40 may execute these commands without raising, but the results
        are unspecified. Use :attr:`sensor_variant_name` to detect the part at
        runtime before relying on them.

    """

    def __init__(self, i2c_bus: I2C, address: int = SCD4X_DEFAULT_ADDR) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
        self._buffer = bytearray(18)
        self._cmd = bytearray(2)
        self._crc_buffer = bytearray(2)

        # cached readings
        self._temperature = None
        self._relative_humidity = None
        self._co2 = None

        self.stop_periodic_measurement()

    @property
    def CO2(self) -> int:  # pylint:disable=invalid-name
        """Returns the CO2 concentration in PPM (parts per million)

        .. note::
            Between measurements, the most recent reading will be cached and returned.

        """
        if self.data_ready:
            self._read_data()
        return self._co2

    @property
    def temperature(self) -> float:
        """Returns the current temperature in degrees Celsius

        .. note::
            Between measurements, the most recent reading will be cached and returned.

        """
        if self.data_ready:
            self._read_data()
        return self._temperature

    @property
    def relative_humidity(self) -> float:
        """Returns the current relative humidity in %rH.

        .. note::
            Between measurements, the most recent reading will be cached and returned.

        """
        if self.data_ready:
            self._read_data()
        return self._relative_humidity

    def measure_single_shot(self) -> None:
        """On-demand measurement of CO2 concentration, relative humidity, and temperature.

        Single shot measurement is available on the **SCD41 and SCD43 only**. A
        base SCD40 may execute this command without raising, but the returned
        values are unspecified and uncalibrated; confirm the part with
        :attr:`sensor_variant_name` before relying on it.
        """
        self._send_command(_SCD4X_MEASURESINGLESHOT, cmd_delay=5)

    def measure_single_shot_rht_only(self) -> None:
        """On-demand measurement of relative humidity and temperature only.

        Available on the **SCD41 and SCD43 only** (see :meth:`measure_single_shot`
        for the variant caveat). This command does not produce a CO2 value.
        """
        self._send_command(_SCD4X_MEASURESINGLESHOTRHTONLY, cmd_delay=0.05)

    def power_down(self) -> None:
        """Put the sensor from idle into sleep mode to reduce current draw.

        Intended for power-cycled single shot operation (SCD41/SCD43). The
        sensor must be in the idle state when this is called. Wake it again
        with :meth:`wake_up`.
        """
        self._send_command(_SCD4X_POWERDOWN, cmd_delay=0.001)

    def wake_up(self) -> None:
        """Wake the sensor from sleep mode back into the idle state (SCD41/SCD43).

        The SCD4x does not acknowledge this command, so the resulting I2C NACK
        is expected and ignored here. To confirm the sensor actually reached the
        idle state, read :attr:`serial_number` afterwards. Call this before
        :meth:`measure_single_shot` if the sensor was previously powered down.
        """
        self._cmd[0] = (_SCD4X_WAKEUP >> 8) & 0xFF
        self._cmd[1] = _SCD4X_WAKEUP & 0xFF
        try:
            with self.i2c_device as i2c:
                i2c.write(self._cmd, end=2)
        except OSError:
            # The sensor does not ACK wake_up; the NACK is expected, not an error.
            pass
        time.sleep(0.03)  # wake_up execution time

    def reinit(self) -> None:
        """Reinitializes the sensor by reloading user settings from EEPROM.

        .. note::
            Stops periodic_measurement as a side-effect.  Restart if desired.

        """
        self.stop_periodic_measurement()
        # Execution time raised from 20 ms to 30 ms in the v1.7 datasheet (Table 9).
        self._send_command(_SCD4X_REINIT, cmd_delay=0.03)

    def factory_reset(self) -> None:
        """Resets all configuration settings stored in the EEPROM and erases the
        FRC and ASC algorithm history.

        .. note::
            Stops periodic_measurement as a side-effect.  Restart if desired.

        """
        self.stop_periodic_measurement()
        self._send_command(_SCD4X_FACTORYRESET, cmd_delay=1.2)

    def force_calibration(self, target_co2: int) -> int:
        """Forces the sensor to recalibrate to a known CO2 level in PPM.

        Returns the FRC correction the sensor applied, in PPM (this value may be
        negative). Before calling, the sensor must have been operated in a
        measurement mode for more than 3 minutes in a stable, homogeneous CO2
        environment, otherwise the recalibration will fail.

        :raises RuntimeError: if the sensor reports that the recalibration failed.

        .. note::
            Stops periodic_measurement as a side-effect.  Restart if desired.

        """
        self.stop_periodic_measurement()
        self._set_command_value(_SCD4X_FORCEDRECAL, target_co2, cmd_delay=0.5)
        self._read_reply(self._buffer, 3)
        # The raw word is unsigned; a value of 0xffff signals a failed FRC, and
        # the correction is the raw word minus the 0x8000 bias (datasheet 3.8.1).
        correction = struct.unpack_from(">H", self._buffer[0:2])[0]
        if correction == 0xFFFF:
            raise RuntimeError(
                "Forced recalibration failed. Make sure sensor is active for 3 minutes first"
            )
        return correction - 0x8000

    @property
    def self_calibration_enabled(self) -> bool:
        """Enables or disables automatic self calibration (ASC). To work correctly, the sensor must
        be on and active for 7 days after enabling ASC, and exposed to fresh air for at least 1 hour
        per day. Consult the manufacturer's documentation for more information.

        .. note::
            This value will NOT be saved and will be reset on boot unless
            saved with persist_settings().

        """
        self._send_command(_SCD4X_GETASCE, cmd_delay=0.001)
        self._read_reply(self._buffer, 3)
        return self._buffer[1] == 1

    @self_calibration_enabled.setter
    def self_calibration_enabled(self, enabled: bool) -> None:
        self._set_command_value(_SCD4X_SETASCE, enabled)

    @property
    def self_calibration_target(self) -> int:
        """The ASC baseline target CO2 concentration in PPM. Default is 400.

        This is the lower-bound background CO2 level the ASC algorithm assumes
        the sensor is regularly exposed to within one ASC period.

        .. note::
            Only available in idle mode. This value will NOT be saved and will
            be reset on boot unless saved with persist_settings().

        """
        self._send_command(_SCD4X_GETASCTARGET, cmd_delay=0.001)
        self._read_reply(self._buffer, 3)
        return (self._buffer[0] << 8) | self._buffer[1]

    @self_calibration_target.setter
    def self_calibration_target(self, target_co2: int) -> None:
        self._set_command_value(_SCD4X_SETASCTARGET, target_co2)

    @property
    def self_calibration_initial_period(self) -> int:
        """The ASC initial period in hours. Default is 44. Must be a multiple of 4.

        Mainly relevant for single shot operation, where the parameter assumes a
        5 minute measurement interval and must be scaled for other intervals
        (see datasheet v1.7 Section 3.11.5). A value of 0 forces an immediate
        correction.

        .. note::
            Only available in idle mode. This value will NOT be saved and will
            be reset on boot unless saved with persist_settings().

        """
        self._send_command(_SCD4X_GETASCINITIALPERIOD, cmd_delay=0.001)
        self._read_reply(self._buffer, 3)
        return (self._buffer[0] << 8) | self._buffer[1]

    @self_calibration_initial_period.setter
    def self_calibration_initial_period(self, hours: int) -> None:
        self._set_command_value(_SCD4X_SETASCINITIALPERIOD, hours)

    @property
    def self_calibration_standard_period(self) -> int:
        """The ASC standard period in hours. Default is 156. Must be a multiple of 4.

        Mainly relevant for single shot operation, where the parameter assumes a
        5 minute measurement interval and must be scaled for other intervals
        (see datasheet v1.7 Section 3.11.7). A value of 0 forces an immediate
        correction.

        .. note::
            Only available in idle mode. This value will NOT be saved and will
            be reset on boot unless saved with persist_settings().

        """
        self._send_command(_SCD4X_GETASCSTANDARDPERIOD, cmd_delay=0.001)
        self._read_reply(self._buffer, 3)
        return (self._buffer[0] << 8) | self._buffer[1]

    @self_calibration_standard_period.setter
    def self_calibration_standard_period(self, hours: int) -> None:
        self._set_command_value(_SCD4X_SETASCSTANDARDPERIOD, hours)

    def self_test(self) -> None:
        """Performs a self test, takes up to 10 seconds"""
        self.stop_periodic_measurement()
        self._send_command(_SCD4X_SELFTEST, cmd_delay=10)
        self._read_reply(self._buffer, 3)
        if (self._buffer[0] != 0) or (self._buffer[1] != 0):
            raise RuntimeError("Self test failed")

    def _read_data(self) -> None:
        """Reads the temp/hum/co2 from the sensor and caches it"""
        self._send_command(_SCD4X_READMEASUREMENT, cmd_delay=0.001)
        self._read_reply(self._buffer, 9)
        # CO2 = word[0]
        self._co2 = (self._buffer[0] << 8) | self._buffer[1]
        temp = (self._buffer[3] << 8) | self._buffer[4]
        # T = -45 + 175 * (word[1] / 2**16 - 1)
        self._temperature = -45 + 175 * (temp / 65535)
        humi = (self._buffer[6] << 8) | self._buffer[7]
        # RH = 100 * (word[2] / (2**16 - 1))
        self._relative_humidity = 100 * (humi / 65535)

    @property
    def data_ready(self) -> bool:
        """Check the sensor to see if new data is available"""
        self._send_command(_SCD4X_DATAREADY, cmd_delay=0.001)
        self._read_reply(self._buffer, 3)
        return not ((self._buffer[0] & 0x07 == 0) and (self._buffer[1] == 0))

    @property
    def serial_number(self) -> Tuple[int, int, int, int, int, int]:
        """Request a 6-tuple containing the unique serial number for this sensor"""
        self._send_command(_SCD4X_SERIALNUMBER, cmd_delay=0.001)
        self._read_reply(self._buffer, 9)
        return (
            self._buffer[0],
            self._buffer[1],
            self._buffer[3],
            self._buffer[4],
            self._buffer[6],
            self._buffer[7],
        )

    @property
    def sensor_variant(self) -> int:
        """Read the sensor variant code (bits 15:12 of the variant word).

        Returns the 4-bit code: ``0`` = SCD40, ``1`` = SCD41, ``5`` = SCD43.
        See :attr:`sensor_variant_name` for the ASCII name.

        .. note::
            Only available in idle mode.

            The SCD43 is listed with a code of 5 - per the datasheet.  This property is for
            reading the raw variant code.  Please use
            :attr:`sensor_variant_name <adafruit_scd4x.SCD4X.sensor_variant_name>`
            for a translated version of the model number that shows "SCD43".

        """
        self._send_command(_SCD4X_GETSENSORVARIANT, cmd_delay=0.001)
        self._read_reply(self._buffer, 3)
        # Variant is in bits 15:12 of word[0]; bits 11:0 are reserved.
        return self._buffer[0] >> 4

    @property
    def sensor_variant_name(self) -> str:
        """Read the sensor variant and return its ASCII name.

        Returns ``"SCD40"``, ``"SCD41"`` or ``"SCD43"``. Any undocumented
        variant code is returned as ``"SCD4x (0x<code>)"``.

        .. note::
            Only available in idle mode.

        """
        code = self.sensor_variant
        return _SCD4X_VARIANTS.get(code, f"SCD4x (0x{code:X})")

    def stop_periodic_measurement(self) -> None:
        """Stop measurement mode"""
        self._send_command(_SCD4X_STOPPERIODICMEASUREMENT, cmd_delay=0.5)

    def start_periodic_measurement(self) -> None:
        """Put sensor into periodic measurement mode, about 5s per measurement

        .. note::
            Only the following commands will work once in periodic measurement mode:

            * :attr:`CO2 <adafruit_scd4x.SCD4X.CO2>`
            * :attr:`temperature <adafruit_scd4x.SCD4X.temperature>`
            * :attr:`relative_humidity <adafruit_scd4x.SCD4X.relative_humidity>`
            * :attr:`data_ready <adafruit_scd4x.SCD4X.data_ready>`
            * :meth:`reinit() <adafruit_scd4x.SCD4X.reinit>`
            * :meth:`factory_reset() <adafruit_scd4x.SCD4X.factory_reset>`
            * :meth:`force_calibration() <adafruit_scd4x.SCD4X.force_calibration>`
            * :meth:`self_test() <adafruit_scd4x.SCD4X.self_test>`
            * :attr:`ambient_pressure <adafruit_scd4x.SCD4X.ambient_pressure>`

        """
        self._send_command(_SCD4X_STARTPERIODICMEASUREMENT)

    def start_low_periodic_measurement(self) -> None:
        """Put sensor into low power periodic measurement mode, about 30s per measurement. See
        :meth:`start_periodic_measurement() <adafruit_scd4x.SCD4X.start_perodic_measurement>`
        for more details.
        """
        self._send_command(_SCD4X_STARTLOWPOWERPERIODICMEASUREMENT)

    def persist_settings(self) -> None:
        """Save temperature offset, altitude offset, and selfcal enable settings to EEPROM"""
        self._send_command(_SCD4X_PERSISTSETTINGS, cmd_delay=0.8)

    @property
    def ambient_pressure(self) -> int:
        """The ambient pressure in hPa used to compensate CO2 measurements.

        Setting this enables continuous pressure compensation and may be done at
        any time, including during periodic measurement. Valid values are ``0``
        (compensation disabled) through ``65535`` hPa. Setting an ambient
        pressure overrides any compensation based on a previously set
        :attr:`altitude`. Multiply by 100 to convert to Pa.

        Get and set share the I2C command ``0xe000``; the read/write bit in the
        I2C header selects which operation runs.

        .. note::
            This value will NOT be saved and will be reset on boot unless
            saved with persist_settings().

        :return: the configured ambient pressure compensation, in hPa
        :rtype: int
        :raises AttributeError: if set outside the range 0-65535 hPa
        """
        self._send_command(_SCD4X_GETPRESSURE, cmd_delay=0.001)
        self._read_reply(self._buffer, 3)
        return (self._buffer[0] << 8) | self._buffer[1]

    @ambient_pressure.setter
    def ambient_pressure(self, pressure_hpa: int) -> None:
        if pressure_hpa < 0 or pressure_hpa > 65535:
            raise AttributeError("`ambient_pressure` must be from 0~65535 hPascals")
        self._set_command_value(_SCD4X_SETPRESSURE, pressure_hpa)

    # Keep previous method to not break previous compatibility
    def set_ambient_pressure(self, ambient_pressure: int) -> None:
        """Set the ambient pressure in hPa at any time to adjust CO2 calculations

        Deprecated in favor of :attr:`ambient_pressure <adafruit_scd4x.SCD4X.ambient_pressure>`"""
        self.ambient_pressure = ambient_pressure

    @property
    def temperature_offset(self) -> float:
        """Specifies the offset to be added to the reported measurements to account for a bias in
        the measured signal. Value is in degrees Celsius with a resolution of 0.01 degrees and a
        maximum value of 374 C.

        .. note::
            This value will NOT be saved and will be reset on boot unless saved with
            persist_settings().

        """
        self._send_command(_SCD4X_GETTEMPOFFSET, cmd_delay=0.001)
        self._read_reply(self._buffer, 3)
        temp = (self._buffer[0] << 8) | self._buffer[1]
        return temp * 175.0 / 65535  # T_offset = word[0] * (175 / (2**16 - 1))

    @temperature_offset.setter
    def temperature_offset(self, offset: Union[int, float]) -> None:
        if offset > 374:
            raise AttributeError("Offset value must be less than or equal to 374 degrees Celsius")
        temp = int(offset * 65535 / 175)  # word[0] = T_offset * ((2**16 - 1) / 175)
        self._set_command_value(_SCD4X_SETTEMPOFFSET, temp)

    @property
    def altitude(self) -> int:
        """Specifies the altitude at the measurement location in meters above sea level. Setting
        this value adjusts the CO2 measurement calculations to account for the air pressure's effect
        on readings.

        .. note::
            This value will NOT be saved and will be reset on boot unless saved with
            persist_settings().
        """
        self._send_command(_SCD4X_GETALTITUDE, cmd_delay=0.001)
        self._read_reply(self._buffer, 3)
        return (self._buffer[0] << 8) | self._buffer[1]

    @altitude.setter
    def altitude(self, height: int) -> None:
        if height > 65535:
            raise AttributeError("Height must be less than or equal to 65535 meters")
        self._set_command_value(_SCD4X_SETALTITUDE, height)

    def _check_buffer_crc(self, buf: bytearray) -> bool:
        for i in range(0, len(buf), 3):
            self._crc_buffer[0] = buf[i]
            self._crc_buffer[1] = buf[i + 1]
            if self._crc8(self._crc_buffer) != buf[i + 2]:
                raise RuntimeError("CRC check failed while reading data")
        return True

    def _send_command(self, cmd: int, cmd_delay: float = 0) -> None:
        self._cmd[0] = (cmd >> 8) & 0xFF
        self._cmd[1] = cmd & 0xFF

        try:
            with self.i2c_device as i2c:
                i2c.write(self._cmd, end=2)
        except OSError as err:
            raise RuntimeError(
                "Could not communicate via I2C, some commands/settings "
                "are not available in periodic measurement mode"
            ) from err
        time.sleep(cmd_delay)

    def _set_command_value(self, cmd, value, cmd_delay=0.001):
        # Make cmd_delay 1ms by default. In table 9 of DS virtually every command lists a
        # 1ms delay unless they specify longer so this catches cmds without a specific delay.
        self._buffer[0] = (cmd >> 8) & 0xFF
        self._buffer[1] = cmd & 0xFF
        self._crc_buffer[0] = self._buffer[2] = (value >> 8) & 0xFF
        self._crc_buffer[1] = self._buffer[3] = value & 0xFF
        self._buffer[4] = self._crc8(self._crc_buffer)
        try:
            with self.i2c_device as i2c:
                i2c.write(self._buffer, end=5)
        except OSError as err:
            raise RuntimeError(
                "Could not communicate via I2C, some commands/settings "
                "are not available in periodic measurement mode"
            ) from err
        time.sleep(cmd_delay)

    def _read_reply(self, buff, num):
        with self.i2c_device as i2c:
            i2c.readinto(buff, end=num)
        self._check_buffer_crc(self._buffer[0:num])

    @staticmethod
    def _crc8(buffer: bytearray) -> int:
        crc = 0xFF
        for byte in buffer:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc <<= 1
        return crc & 0xFF  # return the bottom 8 bits
